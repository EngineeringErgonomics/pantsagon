from pathlib import Path


def test_readme_mentions_apache_license():
    text = Path("README.md").read_text().lower()
    assert "apache license 2.0" in text
