import importlib.util
from pathlib import Path
import os

import pytest

from pantsagon.adapters.policy import pack_validator
from pantsagon.adapters.policy.pack_validator import PackPolicyEngine
from pantsagon.adapters.renderer.copier_renderer import CopierRenderer
from pantsagon.adapters.workspace.filesystem import FilesystemWorkspace
from pantsagon.application.add_service import add_service
from pantsagon.application.repo_lock import read_lock, write_lock


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
        "tool": {"name": "pantsagon", "version": "1.0.0"},
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


def test_add_service_renders_scoped_files(tmp_path, monkeypatch):
    repo_root = _repo_root()
    monkeypatch.setenv("PANTS_BUILDROOT", str(repo_root))
    pack_validator.SCHEMA_PATH = pack_validator._schema_path(repo_root)
    write_lock(tmp_path / ".pantsagon.toml", _base_lock(tmp_path))

    result = add_service(
        repo_path=tmp_path,
        name="monitor-cost",
        lang="python",
        renderer_port=CopierRenderer(),
        policy_engine=PackPolicyEngine(),
        workspace=FilesystemWorkspace(tmp_path),
    )
    assert not [d for d in result.diagnostics if d.severity.value == "error"]

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

    assert not (tmp_path / ".github").exists()
    assert not (tmp_path / "pants.toml").exists()
    assert not (tmp_path / "tools").exists()
    assert not (tmp_path / "shared" / "foundation").exists()

    lock = read_lock(tmp_path / ".pantsagon.toml").value
    assert lock is not None
    assert lock["selection"]["services"] == ["monitor-cost"]
    assert lock["resolved"]["answers"]["service_name"] == "monitor-cost"
    assert lock["resolved"]["answers"]["service_pkg"] == "monitor_cost"
    assert lock["resolved"]["answers"]["service_packages"]["monitor-cost"] == "monitor_cost"


def test_add_service_skips_openapi_readme_if_present(tmp_path, monkeypatch):
    repo_root = _repo_root()
    monkeypatch.setenv("PANTS_BUILDROOT", str(repo_root))
    pack_validator.SCHEMA_PATH = pack_validator._schema_path(repo_root)
    write_lock(tmp_path / ".pantsagon.toml", _base_lock(tmp_path))
    readme_path = tmp_path / "shared" / "contracts" / "openapi" / "README.md"
    readme_path.parent.mkdir(parents=True, exist_ok=True)
    readme_path.write_text("keep")

    result = add_service(
        repo_path=tmp_path,
        name="monitor-cost",
        lang="python",
        renderer_port=CopierRenderer(),
        policy_engine=PackPolicyEngine(),
        workspace=FilesystemWorkspace(tmp_path),
    )
    assert not [d for d in result.diagnostics if d.severity.value == "error"]
    assert readme_path.read_text() == "keep"
