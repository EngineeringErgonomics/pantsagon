from pathlib import Path

import importlib.util
import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("copier") is None,
    reason="copier not installed",
)

from pantsagon.application.init_repo import init_repo


def test_init_repo_writes_lock(tmp_path):
    result = init_repo(repo_path=tmp_path, languages=["python"], services=["monitors"], features=["openapi"], renderer="copier")
    assert (tmp_path / ".pantsagon.toml").exists()

def test_init_repo_records_service_package(tmp_path):
    result = init_repo(repo_path=tmp_path, languages=["python"], services=["monitor-cost"], features=["openapi"], renderer="copier")
    import tomllib

    data = tomllib.loads((tmp_path / ".pantsagon.toml").read_text())
    assert data["resolved"]["answers"]["service_packages"]["monitor-cost"] == "monitor_cost"
