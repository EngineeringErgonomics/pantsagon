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
    ci_path = out / ".github" / "workflows" / "ci.yml"
    assert ci_path.exists()
    ci_text = ci_path.read_text()
    assert "pantsbuild/actions/init-pants" in ci_text
    assert (out / "shared" / "foundation" / "README.md").exists()
    assert (out / "docs" / "README.md").exists()
    assert (out / "docs" / "dev" / "hexagonal-dev-guide.md").exists()
    assert (out / "mkdocs.yml").exists()
    assert (out / ".ruff.toml").exists()
    assert (out / "pyrightconfig.json").exists()


def test_core_pack_renders_guard_scripts_and_hooks(tmp_path):
    pack = Path("packs/core")
    out = tmp_path / "core"
    out.mkdir()
    _render(pack, out, {"repo_name": "acme"})
    guard_files = [
        "tools/guards/security-scan.sh",
        "tools/guards/pre-commit.sh",
        "tools/guards/install-git-hooks.sh",
        "tools/guards/pre-push.sh",
        "tools/guards/find_python_package_clashes.sh",
        "tools/guards/enforce_py_size_limit",
        "tools/guards/fp_sheriff",
        "tools/guards/hex_enforce",
        "tools/guards/monkey_guard",
        "tools/guards/private_alias_guard",
        "tools/guards/test_speed_enforce",
        "tools/guards/third_party_sheriff",
        "tools/guards/unique_enforce",
    ]
    for rel in guard_files:
        assert (out / rel).exists()
    assert (out / ".githooks" / "pre-commit").exists()
    assert (out / ".githooks" / "pre-push").exists()


def test_python_pack_renders_hex_layers_with_snake_pkg(tmp_path):
    pack = Path("packs/python")
    out = tmp_path / "python"
    out.mkdir()
    _render(pack, out, {"service_name": "monitor-cost", "service_pkg": "monitor_cost"})
    base = out / "services" / "monitor-cost" / "src" / "monitor_cost"
    assert (base / "domain" / "__init__.py").exists()
    assert (base / "entrypoints" / "BUILD").exists()


def test_typescript_pack_renders_hex_layers(tmp_path):
    pack = Path("packs/typescript")
    out = tmp_path / "typescript"
    out.mkdir()
    _render(pack, out, {"service_name": "monitor-cost", "service_pkg": "monitor_cost"})
    base = out / "services" / "monitor-cost" / "src"
    assert (base / "domain" / "index.ts").exists()
    assert (base / "entrypoints" / "index.ts").exists()


def test_rust_pack_renders_hex_layers(tmp_path):
    pack = Path("packs/rust")
    out = tmp_path / "rust"
    out.mkdir()
    _render(pack, out, {"service_name": "monitor-cost", "service_pkg": "monitor_cost"})
    svc = out / "services" / "monitor-cost"
    base = svc / "src"
    assert (svc / "Cargo.toml").exists()
    assert (base / "lib.rs").exists()
    assert (base / "domain" / "mod.rs").exists()
    assert (base / "entrypoints" / "mod.rs").exists()


def test_go_pack_renders_hex_layers(tmp_path):
    pack = Path("packs/go")
    out = tmp_path / "go"
    out.mkdir()
    _render(pack, out, {"service_name": "monitor-cost", "service_pkg": "monitor_cost"})
    svc = out / "services" / "monitor-cost"
    assert (svc / "go.mod").exists()
    assert (svc / "internal" / "domain" / "domain.go").exists()
    assert (svc / "cmd" / "monitor-cost" / "main.go").exists()


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
