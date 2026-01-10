from pathlib import Path


def test_readme_mentions_rendered_init():
    text = Path("README.md").read_text().lower()
    assert "renders" in text and "init" in text
