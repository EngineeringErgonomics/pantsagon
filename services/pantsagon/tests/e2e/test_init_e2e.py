from typer.testing import CliRunner
import pytest
import stat
import tomllib

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
    assert (tmp_path / "shared" / "contracts" / "openapi" / "monitors.yaml").exists()


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
    assert (
        tmp_path / "services" / "governance" / "src" / "governance" / "domain"
    ).exists()
    assert (tmp_path / "shared" / "contracts" / "openapi" / "monitors.yaml").exists()
    assert (tmp_path / "shared" / "contracts" / "openapi" / "governance.yaml").exists()


@pytest.mark.parametrize(
    "lang,expected,unexpected",
    [
        (
            "typescript",
            {
                "pants.backend.experimental.javascript",
                "pants.backend.experimental.typescript",
                "pants.backend.shell",
                "pants.backend.python",
                "pants.backend.python.lint.ruff",
                "pants.backend.python.typecheck.pyright",
            },
            {"pants.backend.experimental.rust", "pants.backend.experimental.go"},
        ),
        (
            "rust",
            {
                "pants.backend.experimental.rust",
                "pants.backend.shell",
                "pants.backend.python",
                "pants.backend.python.lint.ruff",
                "pants.backend.python.typecheck.pyright",
            },
            {"pants.backend.experimental.typescript", "pants.backend.experimental.go"},
        ),
        (
            "go",
            {
                "pants.backend.experimental.go",
                "pants.backend.shell",
                "pants.backend.python",
                "pants.backend.python.lint.ruff",
                "pants.backend.python.typecheck.pyright",
            },
            {
                "pants.backend.experimental.typescript",
                "pants.backend.experimental.rust",
            },
        ),
    ],
)
def test_init_non_python_repo_pants_toml_is_clean(
    tmp_path, monkeypatch, lang, expected, unexpected
):
    monkeypatch.setenv("PANTSAGON_DETERMINISTIC", "1")
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "init",
            str(tmp_path),
            "--lang",
            lang,
            "--services",
            "monitors,governance",
            "--feature",
            "docker",
        ],
    )
    assert result.exit_code == 0
    pants_toml = tmp_path / "pants.toml"
    text = pants_toml.read_text()
    assert text.lstrip().startswith("[GLOBAL]")
    assert not text.startswith("\n")
    assert "\n\n\n" not in text
    lines = text.splitlines()
    start = lines.index("backend_packages = [")
    end = start + 1
    while end < len(lines) and not lines[end].startswith("]"):
        assert lines[end].strip() != ""
        end += 1

    data = tomllib.loads(text)
    backends = set(data["GLOBAL"]["backend_packages"])
    for backend in expected:
        assert backend in backends
    for backend in unexpected:
        assert backend not in backends

    assert "[python]" in text
    assert "[python-infer]" in text
    assert "[ruff]" in text
    assert "[pyright]" in text

    assert (tmp_path / ".ruff.toml").exists()
    assert (tmp_path / "pyrightconfig.json").exists()
    assert (tmp_path / "3rdparty" / "python").exists()

    for build_file in tmp_path.rglob("BUILD"):
        assert build_file.stat().st_mode & stat.S_IXUSR == 0
