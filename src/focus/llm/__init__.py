"""Local Qwen caption labeler via Ollama (Phase 4c).

LLM **labels** only — never invents graph nodes, edges, or risk topology.
Always attempted on CLI audit / Audit Local; never on live-buffer overlay.
"""

from focus.llm.labeler import apply_llm_captions, label_caption
from focus.llm.ollama_setup import ensure_ollama_for_captions, platform_install_instructions
from focus.llm.pack import CaptionEvidencePack, build_evidence_pack
from focus.llm.settings import (
    LlmSettings,
    gate_llm_for_runtime,
    load_llm_settings,
    resolve_llm_captions,
)
from focus.llm.weak import is_weak_caption

__all__ = [
    "CaptionEvidencePack",
    "LlmSettings",
    "apply_llm_captions",
    "build_evidence_pack",
    "ensure_ollama_for_captions",
    "gate_llm_for_runtime",
    "is_weak_caption",
    "label_caption",
    "load_llm_settings",
    "platform_install_instructions",
    "resolve_llm_captions",
]
