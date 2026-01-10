import importlib.util
import pytest

from pantsagon.application.init_repo import init_repo

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("copier") is None,
    reason="copier not installed",
)


def test_init_repo_renders_core_pack(tmp_path):
    result = init_repo(repo_path=tmp_path, languages=["python"], services=["monitors"], features=["openapi", "docker"], renderer="copier")
    assert (tmp_path / "pants.toml").exists()
    assert (tmp_path / ".pantsagon.toml").exists()
    readme = (tmp_path / "README.md").read_text()
    assert "Pantsagon Generated Repo" in readme
