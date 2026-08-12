"""Shared pytest fixtures."""

from pathlib import Path

import pytest

GLASS_BOX = Path(__file__).parent / "fixtures" / "glass_box"
GLASS_BOX_JS = Path(__file__).parent / "fixtures" / "glass_box_js"


@pytest.fixture(autouse=True)
def _focus_test_no_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    """Product default is captions-on; keep unit/integration tests offline."""
    monkeypatch.setenv("FOCUS_TEST_NO_LLM", "1")


@pytest.fixture()
def glass_box_path() -> Path:
    """Path to the committed golden Python fixture repo."""
    return GLASS_BOX


@pytest.fixture()
def glass_box_js_path() -> Path:
    """Path to the committed golden JS/TS fixture repo."""
    return GLASS_BOX_JS
