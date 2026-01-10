from pathlib import Path

import pytest


def _readme_text() -> str:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "README.md"
        if candidate.exists():
            return candidate.read_text()
    pytest.skip("README.md not available in test sandbox")
    return ""


def test_readme_mentions_rendered_init():
    text = _readme_text().lower()
    assert "renders" in text and "init" in text
