from typer.testing import CliRunner

from pantsagon.entrypoints.cli import app
import json


def test_cli_init_writes_lock(tmp_path):
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
        ],
    )
    assert result.exit_code == 0
    assert (tmp_path / ".pantsagon.toml").exists()


def test_cli_init_json_output(tmp_path):
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
            "--json",
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["command"] == "init"
    assert payload["exit_code"] == 0
