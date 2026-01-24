import importlib.util

import pytest
from typer.testing import CliRunner

from pantsagon.entrypoints.cli import app

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("copier") is None,
    reason="copier not installed",
)


def test_augmented_coding_creates_agents_file(tmp_path):
    runner = CliRunner()
    result = runner.invoke(
        app, ["init", str(tmp_path), "--lang", "python", "--augmented-coding", "agents"]
    )
    assert result.exit_code == 0
    agents_path = tmp_path / "AGENTS.md"
    assert agents_path.exists()
    content = agents_path.read_text(encoding="utf-8")
    assert "Hexagonal Architecture Rules" in content
    assert "Domain depends on nothing" in content
    assert "ruff" in content
    assert "pyright" in content
