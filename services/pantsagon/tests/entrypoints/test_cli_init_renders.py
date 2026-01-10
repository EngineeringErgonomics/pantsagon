import importlib.util

import pytest
from typer.testing import CliRunner

from pantsagon.entrypoints.cli import app

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("copier") is None,
    reason="copier not installed",
)


def test_cli_init_renders_core_pack(tmp_path):
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "init",
            str(tmp_path),
            "--lang",
            "python",
            "--services",
            "monitors",
            "--feature",
            "openapi",
            "--feature",
            "docker",
        ],
    )
    assert result.exit_code == 0
    assert (tmp_path / "pants.toml").exists()
    assert (tmp_path / ".pantsagon.toml").exists()
    readme = (tmp_path / "README.md").read_text()
    assert "Pantsagon Generated Repo" in readme
