from typer.testing import CliRunner

from pantsagon.entrypoints.cli import app


def test_init_generates_core_files(tmp_path, monkeypatch):
    monkeypatch.setenv("PANTSAGON_DETERMINISTIC", "1")
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
