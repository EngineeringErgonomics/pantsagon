from pathlib import Path


def test_readme_mentions_validate_command():
    text = Path("README.md").read_text().lower()
    assert "pantsagon validate" in text
