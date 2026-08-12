"""HTTP client for local Ollama caption labeling (OpenAI-compatible /v1)."""

from __future__ import annotations

import json
import logging
from typing import Any, Protocol

import httpx

from focus.llm.settings import DEFAULT_OLLAMA_BASE_URL, LlmSettings

log = logging.getLogger("focus.llm")

SYSTEM_PROMPT = (
    "Write one ℹ️ caption for a code reviewer. Hard limits: ≤320 chars; "
    "at most two short sentences — no preamble, no bullet lists, no markdown. "
    "Sweet spot: what changed AND why it matters (so that / for whom) using "
    "measured slots, edit_lines, implication_*, and deterministic_caption — "
    "not a thin slogan like 'Updates X here', not chatty filler "
    "('This change…', 'The function now…'), and not jargon without consequence. "
    "Grounding: only name identifiers listed in allowed_tokens or "
    "grounding.allowed_identifiers; never invent callers, files, modules, or behavior "
    "absent from the pack. If you cannot add a clear so-that from the pack, "
    "return deterministic_caption verbatim. "
    'JSON only: {"detail": "..."}'
)

# Module-constant orphans (Phase 4d): the pack carries readers + reader_doc,
# so the model must explain consequence for the reader — not re-dump the value.
ORPHAN_SYSTEM_PROMPT = (
    "Write one ℹ️ caption for a code reviewer. Hard limits: ≤320 chars; "
    "at most two short sentences — no preamble or markdown. "
    "symbol_name is a module constant; readers/importers and reader_doc are "
    "measured facts in the pack. Sweet spot: what changing this constant means "
    "for reader behavior (so that / who breaks) — not quoting the value, not "
    "repeating deterministic_caption, not 'Updates X here'. "
    "Only name identifiers from allowed_tokens, readers, or importers; never "
    "invent callers, files, or downstream behavior. "
    'JSON only: {"detail": "..."}'
)

DEFAULT_OLLAMA_MODEL = "qwen2.5-coder:3b"


def _prompt_for(pack_json: dict[str, Any]) -> str:
    if pack_json.get("symbol_kind") == "constant" and (
        pack_json.get("readers") or pack_json.get("importers")
    ):
        return ORPHAN_SYSTEM_PROMPT
    return SYSTEM_PROMPT


class LabelClient(Protocol):
    def label(self, pack_json: dict[str, Any]) -> str | None: ...


def build_client(settings: LlmSettings) -> LabelClient:
    """Always return a local Ollama chat-completions client."""
    base = (settings.base_url or DEFAULT_OLLAMA_BASE_URL).rstrip("/")
    return OllamaClient(
        model=settings.model or DEFAULT_OLLAMA_MODEL,
        base_url=base,
    )


class OllamaClient:
    """Ollama's OpenAI-compatible ``/v1/chat/completions`` endpoint."""

    def __init__(self, *, model: str, base_url: str = DEFAULT_OLLAMA_BASE_URL) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")

    def label(self, pack_json: dict[str, Any]) -> str | None:
        body = {
            "model": self.model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": _prompt_for(pack_json)},
                {"role": "user", "content": json.dumps(pack_json)},
            ],
        }
        try:
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": "Bearer ollama",
                        "Content-Type": "application/json",
                    },
                    json=body,
                )
                resp.raise_for_status()
                data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return _detail_from_content(content)
        except Exception as exc:  # noqa: BLE001 — never block audit
            log.debug("Ollama caption label failed: %s", type(exc).__name__)
            return None


def _detail_from_content(content: str) -> str | None:
    if not content or not content.strip():
        return None
    text = content.strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        # Model sometimes wraps JSON in fences.
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            parsed = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None
    if not isinstance(parsed, dict):
        return None
    detail = parsed.get("detail")
    return detail if isinstance(detail, str) else None
