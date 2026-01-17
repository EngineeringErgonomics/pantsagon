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
    service_root = tmp_path / "services" / "monitors"
    assert (service_root / "src" / "monitors" / "domain" / "__init__.py").exists()
    assert (service_root / "Dockerfile").exists()
    assert (
        tmp_path
        / "shared"
        / "contracts"
        / "openapi"
        / "monitors.yaml"
    ).exists()


def test_init_generates_multiple_services(tmp_path, monkeypatch):
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
            "monitors,governance",
            "--feature",
            "openapi",
            "--feature",
            "docker",
        ],
    )
    assert result.exit_code == 0
    assert (tmp_path / "services" / "monitors" / "src" / "monitors" / "domain").exists()
    assert (tmp_path / "services" / "governance" / "src" / "governance" / "domain").exists()
    assert (tmp_path / "shared" / "contracts" / "openapi" / "monitors.yaml").exists()
    assert (tmp_path / "shared" / "contracts" / "openapi" / "governance.yaml").exists()
