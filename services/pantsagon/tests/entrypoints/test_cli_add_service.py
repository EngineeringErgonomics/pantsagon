import importlib.util
from pathlib import Path

import pytest
from typer.testing import CliRunner

from pantsagon.application.repo_lock import write_lock
from pantsagon.entrypoints.cli import app


pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("copier") is None,
    reason="copier not installed",
)


def _repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "packs").is_dir():
            return parent
    raise RuntimeError("Could not locate repo root")


def _base_lock(repo_path: Path) -> dict:
    return {
        "tool": {"name": "pantsagon", "version": "0.1.0"},
        "settings": {
            "renderer": "copier",
            "strict": False,
            "strict_manifest": True,
            "allow_hooks": False,
        },
        "selection": {
            "languages": ["python"],
            "features": ["openapi", "docker"],
            "services": [],
            "augmented_coding": "none",
        },
        "resolved": {
            "packs": [
                {"id": "pantsagon.core", "version": "1.0.0", "source": "bundled"},
                {"id": "pantsagon.python", "version": "1.0.0", "source": "bundled"},
                {"id": "pantsagon.openapi", "version": "1.0.0", "source": "bundled"},
                {"id": "pantsagon.docker", "version": "1.0.0", "source": "bundled"},
            ],
            "answers": {"repo_name": repo_path.name},
        },
    }


def test_cli_add_service_renders_scoped_files(tmp_path, monkeypatch):
    write_lock(tmp_path / ".pantsagon.toml", _base_lock(tmp_path))
    monkeypatch.chdir(tmp_path)
    repo_root = _repo_root()

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["add-service", "monitor-cost", "--lang", "python"],
        env={"PANTS_BUILDROOT": str(repo_root)},
    )
    assert result.exit_code == 0

    service_root = tmp_path / "services" / "monitor-cost"
    assert (service_root / "src" / "monitor_cost" / "domain").exists()
    assert (service_root / "Dockerfile").exists()
    assert (
        tmp_path
        / "shared"
        / "contracts"
        / "openapi"
        / "monitor-cost.yaml"
    ).exists()
