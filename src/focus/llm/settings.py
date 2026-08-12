"""FOCUS_LLM_* environment knobs for local Qwen captions via Ollama."""

from __future__ import annotations

import os

import httpx
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434/v1"
DEFAULT_OLLAMA_MODEL_HINT = "qwen2.5-coder:3b"


class LlmSettings(BaseSettings):
    """Loaded from env / ``.env``. Keys never appear in logs or HUD."""

    model_config = SettingsConfigDict(
        env_prefix="FOCUS_LLM_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    model: str | None = Field(
        default=None,
        description="Ollama model id; default qwen2.5-coder:3b when unset.",
    )
    base_url: str | None = Field(
        default=None,
        description="OpenAI-compatible Ollama base (default http://127.0.0.1:11434/v1).",
    )
    concurrency: int = Field(
        default=8,
        ge=1,
        le=16,
        description="Max parallel caption label requests (FOCUS_LLM_CONCURRENCY).",
    )


def load_llm_settings() -> LlmSettings:
    return LlmSettings()


def ollama_tags_url(base_url: str | None = None) -> str:
    """Native Ollama tags endpoint from an OpenAI-compatible ``/v1`` base."""
    base = (base_url or DEFAULT_OLLAMA_BASE_URL).rstrip("/")
    if base.endswith("/v1"):
        base = base[:-3].rstrip("/")
    return f"{base}/api/tags"


def probe_ollama(*, base_url: str | None = None, timeout: float = 1.0) -> bool:
    """True when the local Ollama daemon answers (soft check; not version-gated)."""
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(ollama_tags_url(base_url))
            return resp.status_code < 500
    except Exception:  # noqa: BLE001 — unreachable is an expected dogfood case
        return False


def gate_llm_for_runtime(use_llm: bool) -> bool:
    """Require a reachable Ollama daemon when captions should run.

    When Ollama is down, prints OS install instructions and may offer a
    Homebrew install on macOS (see ``focus.llm.ollama_setup``). Returns False
    so the audit keeps deterministic ℹ️ when setup does not succeed.

    ``FOCUS_TEST_NO_LLM=1`` (set in pytest) skips the daemon so unit tests
    stay offline.
    """
    if not use_llm:
        return False
    if os.environ.get("FOCUS_TEST_NO_LLM", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }:
        return False
    from focus.llm.ollama_setup import ensure_ollama_for_captions

    return ensure_ollama_for_captions()


def resolve_llm_captions(
    *,
    overlays: dict[str, str] | None = None,
) -> bool:
    """Whether this audit may call the caption labeler.

    Always on for CLI audit / Audit Local. Live overlays always skip
    (latency — not a user setting).
    """
    if overlays:
        return False
    return True
