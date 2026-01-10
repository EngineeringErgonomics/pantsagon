from typer.testing import CliRunner

import importlib.util
import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("copier") is None,
    reason="copier not installed",
)

from pantsagon.entrypoints.cli import app


def test_augmented_coding_creates_agents_file(tmp_path):
    runner = CliRunner()
    result = runner.invoke(app, ["init", str(tmp_path), "--lang", "python", "--augmented-coding", "agents"])
    assert result.exit_code == 0
    assert (tmp_path / "AGENTS.md").exists()
