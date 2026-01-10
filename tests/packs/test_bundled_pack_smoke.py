import importlib.util
from pathlib import Path

import pytest

from pantsagon.adapters.renderer.copier_renderer import CopierRenderer
from pantsagon.domain.pack import PackRef
from pantsagon.ports.renderer import RenderRequest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("copier") is None,
    reason="copier not installed",
)


def _render(pack_dir: Path, out: Path, answers: dict) -> None:
    req = RenderRequest(
        pack=PackRef(id="x", version="1.0.0", source="bundled"),
        pack_path=pack_dir,
        staging_dir=out,
        answers=answers,
        allow_hooks=False,
    )
    CopierRenderer().render(req)


def test_core_pack_renders_minimum_skeleton(tmp_path):
    pack = Path("packs/core")
    out = tmp_path / "core"
    out.mkdir()
    _render(pack, out, {"repo_name": "acme"})
    assert (out / "pants.toml").exists()
    assert (out / ".github" / "workflows" / "ci.yml").exists()
    assert (out / "shared" / "foundation" / "README.md").exists()
    assert (out / "docs" / "README.md").exists()


def test_python_pack_renders_hex_layers_with_snake_pkg(tmp_path):
    pack = Path("packs/python")
    out = tmp_path / "python"
    out.mkdir()
    _render(pack, out, {"service_name": "monitor-cost", "service_pkg": "monitor_cost"})
    base = out / "services" / "monitor-cost" / "src" / "monitor_cost"
    assert (base / "domain" / "__init__.py").exists()
    assert (base / "entrypoints" / "BUILD").exists()


def test_openapi_pack_renders_contracts(tmp_path):
    pack = Path("packs/openapi")
    out = tmp_path / "openapi"
    out.mkdir()
    _render(pack, out, {"service_name": "monitor-cost"})
    assert (out / "shared" / "contracts" / "openapi" / "monitor-cost.yaml").exists()
    assert (out / "shared" / "contracts" / "openapi" / "BUILD").exists()


def test_docker_pack_renders_dockerfile_and_pex(tmp_path):
    pack = Path("packs/docker")
    out = tmp_path / "docker"
    out.mkdir()
    _render(pack, out, {"service_name": "monitor-cost", "service_pkg": "monitor_cost"})
    assert (out / "services" / "monitor-cost" / "Dockerfile").exists()
    assert (out / "services" / "monitor-cost" / "BUILD").exists()
