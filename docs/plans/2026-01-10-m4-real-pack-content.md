# M4 Real Pack Content Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement real bundled pack content (core/python/openapi/docker), add pack smoke tests, and update README with an example tree.

**Architecture:** Keep packs tool-agnostic and minimal while aligning with the hexagonal monorepo design. Core provides repo skeleton and CI, python provides service hex layers and BUILD rules, openapi provides contract scaffolding, docker provides runnable packaging and Dockerfile. Tests verify schema, copier cross-check, and render smoke.

**Tech Stack:** Python, Copier templates, Pants build metadata, Pytest.

### Task 1: Add bundled pack render smoke tests (RED)

**Files:**
- Create: `tests/packs/test_bundled_pack_smoke.py`

**Step 1: Write the failing test**

```python
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/packs/test_bundled_pack_smoke.py -q`
Expected: FAIL (missing templates/content)

### Task 2: Fix pack manifests (schema + cross-check)

**Files:**
- Modify: `packs/core/pack.yaml`
- Modify: `packs/python/pack.yaml`
- Modify: `packs/openapi/pack.yaml`
- Modify: `packs/docker/pack.yaml`
- Modify: `packs/python/copier.yml`
- Modify: `packs/docker/copier.yml`

**Step 1: Confirm failing validation**

Run: `pytest tests/packs/test_bundled_packs.py -q`
Expected: FAIL (missing compatibility)

**Step 2: Update manifests to satisfy schema**

Example (core):
```yaml
schema_version: 1
id: pantsagon.core
version: 1.0.0
description: Core monorepo skeleton
compatibility:
  pants: ">=2.30.0,<2.31"
variables:
  - name: repo_name
    type: string
```

Update other packs similarly with `compatibility.pants`, and add:
- `requires.packs` for python/openapi/docker
- `provides.features` for openapi/docker
- `variables` for `service_name` (and `service_pkg` for python/docker)

**Step 3: Run validation test**

Run: `pytest tests/packs/test_bundled_packs.py -q`
Expected: PASS

### Task 3: Core pack templates (repo skeleton + CI)

**Files:**
- Modify: `packs/core/templates/README.md.jinja`
- Modify: `packs/core/templates/pants.toml.jinja`
- Create: `packs/core/templates/.gitignore.jinja`
- Create: `packs/core/templates/.github/workflows/ci.yml.jinja`
- Create: `packs/core/templates/docs/README.md.jinja`
- Create: `packs/core/templates/shared/foundation/README.md.jinja`
- Create: `packs/core/templates/shared/adapters/README.md.jinja`
- Create: `packs/core/templates/shared/contracts/README.md.jinja`
- Create: `packs/core/templates/tools/forbidden_imports/README.md.jinja`
- Create: `packs/core/templates/3rdparty/python/requirements.txt.jinja`
- Create: `packs/core/templates/3rdparty/python/BUILD.jinja`

**Step 1: Implement minimal, deterministic repo skeleton**

- `pants.toml`: include `pants_version` and minimal `backend_packages` (python, resources, docker)
- `README.md`: mention `.pantsagon.toml` as source of truth and show top-level layout
- `ci.yml`: install Pants only and run `pants lint ::`, `pants check ::`, `pants test ::`
- `.gitignore`: include `.pants.d/`, caches, `dist/`, `.env`

**Step 2: Run smoke tests**

Run: `pytest tests/packs/test_bundled_pack_smoke.py::test_core_pack_renders_minimum_skeleton -q`
Expected: PASS

### Task 4: Python pack templates (hex layers + BUILD rules)

**Files:**
- Modify: `packs/python/templates/README.md.jinja`
- Create: `packs/python/templates/services/{{ service_name }}/README.md.jinja`
- Create: `packs/python/templates/services/{{ service_name }}/src/{{ service_pkg }}/domain/__init__.py.jinja`
- Create: `packs/python/templates/services/{{ service_name }}/src/{{ service_pkg }}/ports/__init__.py.jinja`
- Create: `packs/python/templates/services/{{ service_name }}/src/{{ service_pkg }}/application/__init__.py.jinja`
- Create: `packs/python/templates/services/{{ service_name }}/src/{{ service_pkg }}/adapters/__init__.py.jinja`
- Create: `packs/python/templates/services/{{ service_name }}/src/{{ service_pkg }}/entrypoints/__init__.py.jinja`
- Create: `packs/python/templates/services/{{ service_name }}/src/{{ service_pkg }}/domain/BUILD.jinja`
- Create: `packs/python/templates/services/{{ service_name }}/src/{{ service_pkg }}/ports/BUILD.jinja`
- Create: `packs/python/templates/services/{{ service_name }}/src/{{ service_pkg }}/application/BUILD.jinja`
- Create: `packs/python/templates/services/{{ service_name }}/src/{{ service_pkg }}/adapters/BUILD.jinja`
- Create: `packs/python/templates/services/{{ service_name }}/src/{{ service_pkg }}/entrypoints/BUILD.jinja`

**Step 1: Implement hex layer packages and BUILD rules**

- Use `service_name` for directory and `service_pkg` (snake_case) for package path
- Add `__dependents_rules__` restricting dependents to `svc:{{ service_name }}`
- Entry points target restricts dependents to tag `entrypoint-consumer`
- Dependencies follow hex direction (domain -> foundation; ports -> domain; etc.)

**Step 2: Run smoke test**

Run: `pytest tests/packs/test_bundled_pack_smoke.py::test_python_pack_renders_hex_layers_with_snake_pkg -q`
Expected: PASS

### Task 5: OpenAPI pack templates (contracts + resources target)

**Files:**
- Modify: `packs/openapi/templates/README.md.jinja`
- Create: `packs/openapi/templates/shared/contracts/openapi/README.md.jinja`
- Create: `packs/openapi/templates/shared/contracts/openapi/{{ service_name }}.yaml.jinja`
- Create: `packs/openapi/templates/shared/contracts/openapi/BUILD.jinja`

**Step 1: Implement contract scaffolding**

- `/health` placeholder in spec with note it is disposable
- `resources(name="openapi_specs", sources=["*.yaml"])`
- README notes multiple specs per service and future backend upgrade

**Step 2: Run smoke test**

Run: `pytest tests/packs/test_bundled_pack_smoke.py::test_openapi_pack_renders_contracts -q`
Expected: PASS

### Task 6: Docker pack templates (Dockerfile + docker_image target)

**Files:**
- Modify: `packs/docker/templates/README.md.jinja`
- Create: `packs/docker/templates/services/{{ service_name }}/entrypoints/main.py.jinja`
- Create: `packs/docker/templates/services/{{ service_name }}/Dockerfile.jinja`
- Create: `packs/docker/templates/services/{{ service_name }}/BUILD.jinja`

**Step 1: Implement runnable packaging**

- `entrypoints/main.py` placeholder with clear comment
- `pex_binary(name="app", entry_point="{{ service_pkg }}.entrypoints.main:main", output_path="dist/app.pex", tags=["entrypoint-consumer", "svc:{{ service_name }}"])`
- `docker_image(name="image", image_tags=[], dependencies=[":app"], dockerfile="Dockerfile")`
- Dockerfile uses `WORKDIR /app`, copies `dist/app.pex`, chmod +x, and `ENTRYPOINT ["/app/app.pex"]`

**Step 2: Run smoke test**

Run: `pytest tests/packs/test_bundled_pack_smoke.py::test_docker_pack_renders_dockerfile_and_pex -q`
Expected: PASS

### Task 7: Persist service package mapping in .pantsagon.toml

**Files:**
- Modify: `pantsagon/application/init_repo.py`
- Modify: `pantsagon/application/rendering.py`
- Modify: `tests/application/test_init_repo.py`

**Step 1: Write failing test**

```python
import tomllib


def test_init_repo_records_service_package(tmp_path):
    result = init_repo(repo_path=tmp_path, languages=["python"], services=["monitor-cost"], features=["openapi"], renderer="copier")
    data = tomllib.loads((tmp_path / ".pantsagon.toml").read_text())
    assert data["resolved"]["answers"]["service_packages"]["monitor-cost"] == "monitor_cost"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/application/test_init_repo.py::test_init_repo_records_service_package -q`
Expected: FAIL (missing mapping)

**Step 3: Implement mapping and pass through render answers**

- Compute `service_packages = {name: name.replace('-', '_') for name in services}` in `init_repo`
- Store under `lock["resolved"]["answers"]["service_packages"]`
- Pass `service_pkg` (first service) into `render_bundled_packs` answers for template use

**Step 4: Run test to verify it passes**

Run: `pytest tests/application/test_init_repo.py::test_init_repo_records_service_package -q`
Expected: PASS

### Task 8: Update root README with example tree

**Files:**
- Modify: `README.md`

**Step 1: Add example tree section**

- Include a compact tree showing `services/<svc>/src/<pkg>/...`, `shared/`, `docs/`, and `tools/`

**Step 2: Run docs test**

Run: `pytest tests/docs/test_readme_init_rendering.py -q`
Expected: PASS

### Task 9: Full verification

**Step 1: Run pack tests**

Run: `pytest tests/packs/test_bundled_packs.py tests/packs/test_bundled_pack_smoke.py -q`
Expected: PASS (skips smoke if copier missing)

**Step 2: Run full suite**

Run: `pytest -q`
Expected: PASS
