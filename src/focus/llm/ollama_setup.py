"""Optional local Ollama install helper for caption dogfood (not bundled).

macOS + Homebrew: interactive confirm, then ``brew install`` / start / pull.
Windows / Linux: print official install instructions only (no silent download).
Focus never vendors the Ollama binary and never auto-upgrades without the user.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import time
from collections.abc import Callable
from typing import TextIO

from focus.llm.settings import (
    DEFAULT_OLLAMA_MODEL_HINT,
    load_llm_settings,
    probe_ollama,
)

ConfirmFn = Callable[[str], bool]
RunFn = Callable[[list[str]], int]


def platform_install_instructions(model: str = DEFAULT_OLLAMA_MODEL_HINT) -> str:
    """Human-readable install steps for the current OS (always safe to print)."""
    system = platform.system()
    if system == "Darwin":
        return (
            "macOS — install or update Ollama, then pull the caption model:\n"
            "  brew install ollama\n"
            "  brew services start ollama\n"
            f"  ollama pull {model}\n"
            "Or download the app: https://ollama.com/download\n"
            "Keep Ollama updated yourself (Focus does not pin or auto-upgrade it)."
        )
    if system == "Linux":
        return (
            "Linux — install Ollama, then pull the caption model:\n"
            "  curl -fsSL https://ollama.com/install.sh | sh\n"
            f"  ollama pull {model}\n"
            "See https://ollama.com/download for distro notes.\n"
            "Keep Ollama updated yourself (Focus does not pin or auto-upgrade it)."
        )
    if system == "Windows":
        return (
            "Windows — install Ollama, then pull the caption model:\n"
            "  winget install Ollama.Ollama\n"
            "  (or download from https://ollama.com/download)\n"
            f"  ollama pull {model}\n"
            "Keep Ollama updated yourself (Focus does not pin or auto-upgrade it)."
        )
    return (
        f"Install Ollama from https://ollama.com/download, then:\n"
        f"  ollama pull {model}\n"
        "Keep Ollama updated yourself (Focus does not pin or auto-upgrade it)."
    )


def _default_confirm(prompt: str) -> bool:
    if not sys.stdin.isatty() or not sys.stderr.isatty():
        return False
    if os.environ.get("FOCUS_LLM_SKIP_OLLAMA_INSTALL", "").strip() in {
        "1",
        "true",
        "yes",
    }:
        return False
    try:
        answer = input(prompt).strip().lower()
    except EOFError:
        return False
    return answer in {"y", "yes"}


def _default_run(cmd: list[str]) -> int:
    completed = subprocess.run(cmd, check=False)
    return int(completed.returncode)


def _brew_available() -> bool:
    return shutil.which("brew") is not None


def _ollama_cli() -> str | None:
    return shutil.which("ollama")


def install_ollama_via_brew(
    *,
    model: str = DEFAULT_OLLAMA_MODEL_HINT,
    run: RunFn = _default_run,
    sleep: Callable[[float], None] = time.sleep,
    probe: Callable[..., bool] = probe_ollama,
    base_url: str | None = None,
) -> bool:
    """Install/start Ollama with Homebrew and pull the default caption model."""
    if not _brew_available():
        return False
    steps: list[list[str]] = [
        ["brew", "install", "ollama"],
        ["brew", "services", "start", "ollama"],
    ]
    for cmd in steps:
        if run(cmd) != 0:
            # ``brew services start`` can fail if already running; keep going to pull/probe.
            if cmd[:3] != ["brew", "services", "start"]:
                return False
    # Daemon may need a moment after first install.
    for _ in range(10):
        if probe(base_url=base_url, timeout=1.0):
            break
        sleep(0.5)
    cli = _ollama_cli()
    if cli is None:
        return probe(base_url=base_url, timeout=1.0)
    if run([cli, "pull", model]) != 0:
        # Install may still be usable if the model was already present.
        return probe(base_url=base_url, timeout=1.0)
    return probe(base_url=base_url, timeout=1.0)


def ensure_ollama_for_captions(
    *,
    err: TextIO[str] | None = None,
    confirm: ConfirmFn = _default_confirm,
    run: RunFn = _default_run,
    sleep: Callable[[float], None] = time.sleep,
    probe: Callable[..., bool] = probe_ollama,
) -> bool:
    """Return True when Ollama is ready for caption labeling.

    If the daemon is down: print OS instructions; on macOS + Homebrew + TTY,
    offer to run ``brew install ollama`` / start / pull. Never auto-installs
    on Windows/Linux (instructions only).
    """
    out = err if err is not None else sys.stderr
    settings = load_llm_settings()
    base_url = settings.base_url
    model = (settings.model or DEFAULT_OLLAMA_MODEL_HINT).strip() or DEFAULT_OLLAMA_MODEL_HINT
    if probe(base_url=base_url, timeout=1.0):
        return True

    print(
        "Focus: Ollama is not reachable (Qwen captions need a local Ollama "
        "daemon — the evidence-only HUD still works without it).",
        file=out,
    )
    print(platform_install_instructions(model), file=out)

    if platform.system() == "Darwin" and _brew_available():
        prompt = (
            "Focus: Install/start Ollama via Homebrew and "
            f"pull `{model}` now? [y/N] "
        )
        if confirm(prompt):
            print("Focus: Running Homebrew Ollama setup…", file=out)
            if install_ollama_via_brew(
                model=model,
                run=run,
                sleep=sleep,
                probe=probe,
                base_url=base_url,
            ):
                print("Focus: Ollama is ready for caption labeling.", file=out)
                return True
            print(
                "Focus: Homebrew Ollama setup did not become reachable. "
                "Using deterministic ℹ️ captions.",
                file=out,
            )
            return False

    print("Focus: Using deterministic ℹ️ captions.", file=out)
    return False
