import importlib.util
import shutil

import pytest

from pantsagon.application.init_repo import init_repo
from pantsagon.adapters.pack_catalog.bundled import BundledPackCatalog
from pantsagon.adapters.policy.pack_validator import PackPolicyEngine
from pantsagon.adapters.renderer.copier_renderer import CopierRenderer
from pantsagon.adapters.workspace.filesystem import FilesystemWorkspace
from pathlib import Path

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("copier") is None,
    reason="copier not installed",
)


def test_init_repo_writes_lock(tmp_path):
    init_repo(
        repo_path=tmp_path,
        languages=["python"],
        services=["monitors"],
        features=["openapi"],
        renderer="copier",
    )
    assert (tmp_path / ".pantsagon.toml").exists()


def test_init_repo_records_service_package(tmp_path):
    init_repo(
        repo_path=tmp_path,
        languages=["python"],
        services=["monitor-cost"],
        features=["openapi"],
        renderer="copier",
    )
    import tomllib

    data = tomllib.loads((tmp_path / ".pantsagon.toml").read_text())
    assert data["resolved"]["answers"]["service_packages"]["monitor-cost"] == "monitor_cost"


def test_init_repo_installs_git_hooks(tmp_path):
    if shutil.which("git") is None:
        pytest.skip("git not available")
    packs_root = Path("packs")
    catalog = BundledPackCatalog(packs_root)
    renderer_port = CopierRenderer()
    policy_engine = PackPolicyEngine()
    workspace = FilesystemWorkspace(tmp_path)
    init_repo(
        repo_path=tmp_path,
        languages=["python"],
        services=["monitors"],
        features=[],
        renderer="copier",
        renderer_port=renderer_port,
        pack_catalog=catalog,
        policy_engine=policy_engine,
        workspace=workspace,
    )
    git_dir = tmp_path / ".git"
    assert git_dir.is_dir()
    config_text = (git_dir / "config").read_text()
    assert "hooksPath" in config_text
    assert ".githooks" in config_text
