# Pants Monorepo Conversion Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Convert the repo into a Pants-managed monorepo with strict hexagonal layering, hard dependency boundaries, and contract-first guardrails.

**Architecture:** Treat `pantsagon` as a service under `services/pantsagon/` with top-level layers (`domain`, `ports`, `application`, `adapters`, `entrypoints`), strict dependency/visibility rules, and a non-importable entrypoints layer. Keep `packs/` at repo root and move JSON schemas to `shared/contracts/schemas/`.

**Tech Stack:** Pants 2.30.x, Python 3.12, Ruff, Pyright, Pytest, PEX.

---

### Task 1: Add Pants baseline configuration + tool configs

**Files:**
- Create: `pants.toml`
- Create: `3rdparty/python/requirements.txt`
- Create: `3rdparty/python/BUILD`
- Create: `.ruff.toml`
- Create: `pyrightconfig.json`

**Step 1: Write a failing check (existence test)**

Create `services/pantsagon/tests/test_repo_layout.py` with:
```python
from pathlib import Path


def test_repo_layout_basics_exist() -> None:
    root = Path(__file__).resolve().parents[3]
    assert (root / "pants.toml").exists()
    assert (root / "3rdparty/python/requirements.txt").exists()
```
Expected: FAIL because files don’t exist yet.

**Step 2: Create Pants + tool configs**

Create `pants.toml`:
```toml
[GLOBAL]
pants_version = "2.30.0"
backend_packages = [
  "pants.backend.python",
  "pants.backend.shell",
  "pants.backend.docker",

  "pants.backend.experimental.python.lint.ruff.check",
  "pants.backend.experimental.python.lint.ruff.format",
  "pants.backend.experimental.python.typecheck.pyright",
  "pants.backend.python.test.pytest",

  "pants.backend.experimental.openapi",
  "pants.backend.experimental.openapi.codegen.python",
  "pants.backend.experimental.openapi.lint.spectral",
  "pants.backend.experimental.openapi.lint.openapi_format",

  "pants.backend.experimental.terraform",
  "pants.backend.experimental.visibility",
  "pants.backend.experimental.adhoc",
  "pants.backend.build_files.fmt.ruff",
]

[source]
root_patterns = [
  "shared/**/src",
  "services/**/src",
  "tools/**/src",
]

[python]
interpreter_constraints = ["CPython>=3.12,<3.15"]
enable_resolves = true
default_resolve = "python-default"
resolves = { python-default = "3rdparty/python/python-default.lock" }

[python-infer]
unowned_dependency_behavior = "error"

[visibility]
enforce = true
```

Create `3rdparty/python/requirements.txt`:
```text
typer>=0.12
copier>=9.0
pyyaml>=6.0
jsonschema>=4.22
tomli-w>=1.0
rich>=13.7
pytest>=8.0
pytest-cov>=5.0
```

Create `3rdparty/python/BUILD`:
```python
python_requirements(name="reqs", source="requirements.txt")
```

Create `.ruff.toml`:
```toml
line-length = 100
target-version = "py312"

[lint]
select = ["E", "F", "I"]
```

Create `pyrightconfig.json`:
```json
{
  "pythonVersion": "3.12",
  "typeCheckingMode": "strict",
  "reportMissingTypeStubs": false,
  "exclude": [".git", ".worktrees", "dist", "build"]
}
```

**Step 3: Run tests to verify Step 1 passes**
Run: `python3.12 -m pytest services/pantsagon/tests/test_repo_layout.py -v`
Expected: PASS.

**Step 4: Commit**
```bash
git add pants.toml 3rdparty/python/requirements.txt 3rdparty/python/BUILD .ruff.toml pyrightconfig.json services/pantsagon/tests/test_repo_layout.py
git commit -m "chore: add pants baseline config"
```

---

### Task 2: Move schemas to shared/contracts and add shared/foundation skeleton

**Files:**
- Move: `schemas/pack.schema.v1.json` → `shared/contracts/schemas/pack.schema.v1.json`
- Create: `shared/contracts/BUILD`
- Create: `shared/foundation/src/foundation/__init__.py`
- Create: `shared/foundation/BUILD`

**Step 1: Write a failing check**
Add to `services/pantsagon/tests/test_repo_layout.py`:
```python
    assert (root / "shared/contracts/schemas/pack.schema.v1.json").exists()
```
Expected: FAIL.

**Step 2: Move schema and add shared targets**
Run:
```bash
mkdir -p shared/contracts/schemas
mkdir -p shared/foundation/src/foundation
mkdir -p shared/foundation/tests
mv schemas/pack.schema.v1.json shared/contracts/schemas/pack.schema.v1.json
```

Create `shared/contracts/BUILD`:
```python
__dependents_rules__ = [{"type": "*"}]

resources(
  name="schemas",
  sources=["schemas/**/*.json"],
  tags=["shared:contracts"],
)
```

Create `shared/foundation/src/foundation/__init__.py`:
```python
# Foundation layer placeholder.
```

Create `shared/foundation/BUILD`:
```python
__dependents_rules__ = [{"type": "*"}]

python_sources(
  name="lib",
  tags=["shared:foundation"],
  __dependencies_rules__=[
    {"path": "shared/foundation/src/**"},
  ],
)

python_tests(
  name="tests",
  dependencies=[":lib"],
)
```

**Step 3: Run tests**
Run: `python3.12 -m pytest services/pantsagon/tests/test_repo_layout.py -v`
Expected: PASS.

**Step 4: Commit**
```bash
git add shared/contracts shared/foundation services/pantsagon/tests/test_repo_layout.py

git commit -m "chore: add shared contracts and foundation"
```

---

### Task 3: Move service code to `services/pantsagon/src/pantsagon`

**Files:**
- Move: `pantsagon/` → `services/pantsagon/src/pantsagon/`
- Ensure: `services/pantsagon/src/pantsagon/ports/` stays top-level

**Step 1: Write a failing check**
Add to `services/pantsagon/tests/test_repo_layout.py`:
```python
    assert (root / "services/pantsagon/src/pantsagon/entrypoints/cli.py").exists()
```
Expected: FAIL.

**Step 2: Move package**
Run:
```bash
mkdir -p services/pantsagon/src
mv pantsagon services/pantsagon/src/pantsagon
```

**Step 3: Run tests**
Run: `python3.12 -m pytest services/pantsagon/tests/test_repo_layout.py -v`
Expected: PASS.

**Step 4: Commit**
```bash
git add services/pantsagon/src/pantsagon services/pantsagon/tests/test_repo_layout.py

git commit -m "refactor: move pantsagon package into services layout"
```

---

### Task 4: Move tests into service and update paths

**Files:**
- Move: `tests/` → `services/pantsagon/tests/`
- Modify: `services/pantsagon/tests/packs/test_bundled_packs.py`
- Modify: `pyproject.toml`

**Step 1: Write a failing test (path)**
Update `services/pantsagon/tests/test_repo_layout.py` to assert:
```python
    assert (root / "services/pantsagon/tests/packs/test_bundled_packs.py").exists()
```
Expected: FAIL.

**Step 2: Move tests and fix path reference**
Run:
```bash
mv tests services/pantsagon/tests
```

Update `services/pantsagon/tests/packs/test_bundled_packs.py`:
```python
from pathlib import Path

from pantsagon.application.pack_validation import validate_pack


def test_all_bundled_packs_validate():
    root = Path(__file__).resolve().parents[3]
    packs_dir = root / "packs"
    for pack in ("core", "python", "openapi", "docker"):
        result = validate_pack(packs_dir / pack)
        assert result.is_ok(), result
```

Update `pyproject.toml` pytest config to include the new src path:
```toml
[tool.pytest.ini_options]
addopts = "-q"
pythonpath = ["services/pantsagon/src", "."]
```

**Step 3: Run tests**
Run: `python3.12 -m pytest services/pantsagon/tests/packs/test_bundled_packs.py -v`
Expected: PASS.

**Step 4: Commit**
```bash
git add services/pantsagon/tests pyproject.toml

git commit -m "refactor: move tests under service"
```

---

### Task 5: Add Pants BUILD files for service layers + packaging

**Files:**
- Create: `services/pantsagon/BUILD`
- Create: `services/pantsagon/src/pantsagon/domain/BUILD`
- Create: `services/pantsagon/src/pantsagon/ports/BUILD`
- Create: `services/pantsagon/src/pantsagon/application/BUILD`
- Create: `services/pantsagon/src/pantsagon/adapters/BUILD`
- Create: `services/pantsagon/src/pantsagon/entrypoints/BUILD`
- Create: `services/pantsagon/tests/BUILD`

**Step 1: Write a failing test (Pants address check)**
Add a minimal test to `services/pantsagon/tests/test_repo_layout.py` to check the BUILD file exists:
```python
    assert (root / "services/pantsagon/src/pantsagon/domain/BUILD").exists()
```
Expected: FAIL.

**Step 2: Create BUILD files**

Create `services/pantsagon/BUILD`:
```python
pex_binary(
  name="cli",
  entry_point="pantsagon.entrypoints.cli:app",
  dependencies=["//services/pantsagon/src/pantsagon/entrypoints:entrypoints"],
)
```

Create `services/pantsagon/src/pantsagon/domain/BUILD`:
```python
__dependents_rules__ = [{"tags": ["svc:pantsagon"]}]

python_sources(
  name="domain",
  tags=["svc:pantsagon", "layer:domain"],
  dependencies=["//shared/foundation:lib"],
  __dependencies_rules__=[
    {"path": "services/pantsagon/src/pantsagon/domain/**"},
    {"path": "shared/foundation/src/**"},
  ],
)
```

Create `services/pantsagon/src/pantsagon/ports/BUILD`:
```python
__dependents_rules__ = [{"tags": ["svc:pantsagon"]}]

python_sources(
  name="ports",
  tags=["svc:pantsagon", "layer:ports"],
  dependencies=[
    "//services/pantsagon/src/pantsagon/domain:domain",
    "//shared/foundation:lib",
  ],
  __dependencies_rules__=[
    {"path": "services/pantsagon/src/pantsagon/ports/**"},
    {"path": "services/pantsagon/src/pantsagon/domain/**"},
    {"path": "shared/foundation/src/**"},
  ],
)
```

Create `services/pantsagon/src/pantsagon/application/BUILD`:
```python
__dependents_rules__ = [{"tags": ["svc:pantsagon"]}]

python_sources(
  name="application",
  tags=["svc:pantsagon", "layer:application"],
  dependencies=[
    "//services/pantsagon/src/pantsagon/domain:domain",
    "//services/pantsagon/src/pantsagon/ports:ports",
    "//shared/foundation:lib",
  ],
  __dependencies_rules__=[
    {"path": "services/pantsagon/src/pantsagon/application/**"},
    {"path": "services/pantsagon/src/pantsagon/ports/**"},
    {"path": "services/pantsagon/src/pantsagon/domain/**"},
    {"path": "shared/foundation/src/**"},
  ],
)
```

Create `services/pantsagon/src/pantsagon/adapters/BUILD`:
```python
__dependents_rules__ = [{"tags": ["svc:pantsagon"]}]

python_sources(
  name="adapters",
  tags=["svc:pantsagon", "layer:adapters"],
  dependencies=[
    "//services/pantsagon/src/pantsagon/application:application",
    "//services/pantsagon/src/pantsagon/ports:ports",
    "//services/pantsagon/src/pantsagon/domain:domain",
    "//shared/foundation:lib",
  ],
  __dependencies_rules__=[
    {"path": "services/pantsagon/src/pantsagon/adapters/**"},
    {"path": "services/pantsagon/src/pantsagon/application/**"},
    {"path": "services/pantsagon/src/pantsagon/ports/**"},
    {"path": "services/pantsagon/src/pantsagon/domain/**"},
    {"path": "shared/foundation/src/**"},
    {"path": "shared/adapters/**"},
    {"path": "3rdparty/python/**"},
  ],
)
```

Create `services/pantsagon/src/pantsagon/entrypoints/BUILD`:
```python
__dependents_rules__ = [
  {"address": "services/pantsagon:cli"},
]

python_sources(
  name="entrypoints",
  tags=["svc:pantsagon", "layer:entrypoints"],
  dependencies=[
    "//services/pantsagon/src/pantsagon/adapters:adapters",
    "//services/pantsagon/src/pantsagon/application:application",
    "//services/pantsagon/src/pantsagon/ports:ports",
    "//services/pantsagon/src/pantsagon/domain:domain",
    "//shared/foundation:lib",
  ],
  __dependencies_rules__=[
    {"path": "services/pantsagon/src/pantsagon/entrypoints/**"},
    {"path": "services/pantsagon/src/pantsagon/adapters/**"},
    {"path": "services/pantsagon/src/pantsagon/application/**"},
    {"path": "services/pantsagon/src/pantsagon/ports/**"},
    {"path": "services/pantsagon/src/pantsagon/domain/**"},
    {"path": "shared/foundation/src/**"},
    {"path": "shared/adapters/**"},
    {"path": "3rdparty/python/**"},
  ],
)
```

Create `services/pantsagon/tests/BUILD`:
```python
python_tests(
  name="domain",
  sources=["domain/**/*.py"],
  dependencies=["//services/pantsagon/src/pantsagon/domain:domain"],
)

python_tests(
  name="application",
  sources=["application/**/*.py"],
  dependencies=[
    "//services/pantsagon/src/pantsagon/application:application",
    "//services/pantsagon/src/pantsagon/ports:ports",
    "//services/pantsagon/src/pantsagon/domain:domain",
  ],
)

python_tests(
  name="adapters",
  sources=["adapters/**/*.py"],
  dependencies=[
    "//services/pantsagon/src/pantsagon/adapters:adapters",
    "//services/pantsagon/src/pantsagon/application:application",
    "//services/pantsagon/src/pantsagon/ports:ports",
    "//services/pantsagon/src/pantsagon/domain:domain",
  ],
)

python_tests(
  name="entrypoints",
  sources=["entrypoints/**/*.py"],
  dependencies=[
    "//services/pantsagon/src/pantsagon/entrypoints:entrypoints",
    "//services/pantsagon/src/pantsagon/adapters:adapters",
    "//services/pantsagon/src/pantsagon/application:application",
    "//services/pantsagon/src/pantsagon/ports:ports",
    "//services/pantsagon/src/pantsagon/domain:domain",
  ],
)

python_tests(
  name="packs",
  sources=["packs/**/*.py"],
  dependencies=[
    "//services/pantsagon/src/pantsagon/application:application",
    "//services/pantsagon/src/pantsagon/domain:domain",
    "//shared/contracts:schemas",
    "//packs:bundled",
  ],
)

python_tests(
  name="e2e",
  sources=["e2e/**/*.py"],
  dependencies=[
    "//services/pantsagon/src/pantsagon/entrypoints:entrypoints",
  ],
)

python_tests(
  name="misc",
  sources=["test_imports.py"],
  dependencies=[
    "//services/pantsagon/src/pantsagon/application:application",
    "//services/pantsagon/src/pantsagon/domain:domain",
  ],
)
```

**Step 3: Run tests**
Run: `python3.12 -m pytest services/pantsagon/tests/test_repo_layout.py -v`
Expected: PASS.

**Step 4: Commit**
```bash
git add services/pantsagon/BUILD services/pantsagon/src/pantsagon/**/BUILD services/pantsagon/tests/BUILD services/pantsagon/tests/test_repo_layout.py

git commit -m "build: add pants targets for service layers"
```

---

### Task 6: Add packs/resources BUILD and wire shared contracts

**Files:**
- Create: `packs/BUILD`

**Step 1: Write a failing check**
Add to `services/pantsagon/tests/test_repo_layout.py`:
```python
    assert (root / "packs/BUILD").exists()
```
Expected: FAIL.

**Step 2: Create packs BUILD**
Create `packs/BUILD`:
```python
resources(
  name="bundled",
  sources=["**/*"],
)
```

**Step 3: Run tests**
Run: `python3.12 -m pytest services/pantsagon/tests/test_repo_layout.py -v`
Expected: PASS.

**Step 4: Commit**
```bash
git add packs/BUILD services/pantsagon/tests/test_repo_layout.py

git commit -m "build: add packs resources target"
```

---

### Task 7: Implement forbidden-imports checker with ports support (TDD)

**Files:**
- Create: `tools/forbidden_imports/forbidden_imports.yaml`
- Create: `tools/forbidden_imports/src/forbidden_imports/checker.py`
- Create: `tools/forbidden_imports/tests/test_checker.py`
- Create: `tools/forbidden_imports/tests/test_repo_scan.py`
- Create: `tools/forbidden_imports/BUILD`

**Step 1: Write failing tests**
Create `tools/forbidden_imports/tests/test_checker.py`:
```python
from pathlib import Path

from forbidden_imports.checker import load_config, scan_files


def test_ports_reject_framework_import(tmp_path: Path) -> None:
    cfg = tmp_path / "forbidden_imports.yaml"
    cfg.write_text(
        "layers:\n"
        "  ports:\n"
        "    include: ['ports/*.py']\n"
        "    deny: ['fastapi', 'requests']\n"
    )
    bad = tmp_path / "ports" / "bad.py"
    bad.parent.mkdir(parents=True)
    bad.write_text("import fastapi\n")

    config = load_config(cfg)
    violations = scan_files(config, [bad])
    assert violations, "Expected a violation for ports layer"
```

Create `tools/forbidden_imports/tests/test_repo_scan.py`:
```python
from pathlib import Path

from forbidden_imports.checker import load_config, scan_tree


def test_repo_has_no_forbidden_imports() -> None:
    root = Path(__file__).resolve().parents[3]
    config = load_config(root / "tools/forbidden_imports/forbidden_imports.yaml")
    violations = scan_tree(config, root)
    assert not violations, "\n" + "\n".join(violations)
```
Expected: FAIL (checker not implemented).

**Step 2: Implement checker + config**
Create `tools/forbidden_imports/forbidden_imports.yaml`:
```yaml
layers:
  domain:
    include:
      - "services/**/src/**/domain/**/*.py"
    deny:
      - "requests"
      - "fastapi"
      - "boto3"
  application:
    include:
      - "services/**/src/**/application/**/*.py"
    deny:
      - "requests"
      - "fastapi"
      - "boto3"
  ports:
    include:
      - "services/**/src/**/ports/**/*.py"
    deny:
      - "requests"
      - "fastapi"
      - "boto3"
```

Create `tools/forbidden_imports/src/forbidden_imports/checker.py`:
```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import ast
import fnmatch
import yaml


@dataclass(frozen=True)
class LayerRule:
    name: str
    include: list[str]
    deny: list[str]


@dataclass(frozen=True)
class Config:
    layers: list[LayerRule]


def load_config(path: Path) -> Config:
    data = yaml.safe_load(path.read_text()) or {}
    layers = []
    for name, rules in (data.get("layers") or {}).items():
        layers.append(LayerRule(name=name, include=rules.get("include", []), deny=rules.get("deny", [])))
    return Config(layers=layers)


def _matches_any(path: Path, patterns: list[str]) -> bool:
    rel = path.as_posix()
    return any(fnmatch.fnmatch(rel, pattern) for pattern in patterns)


def _deny_hit(import_name: str, deny: list[str]) -> bool:
    return any(import_name == d or import_name.startswith(d + ".") for d in deny)


def scan_files(config: Config, files: list[Path]) -> list[str]:
    violations: list[str] = []
    for file in files:
        for layer in config.layers:
            if _matches_any(file, layer.include):
                tree = ast.parse(file.read_text(), filename=str(file))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            if _deny_hit(alias.name, layer.deny):
                                violations.append(f"{file}:{node.lineno} forbidden import '{alias.name}' in layer {layer.name}")
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        if _deny_hit(node.module, layer.deny):
                            violations.append(
                                f"{file}:{node.lineno} forbidden import '{node.module}' in layer {layer.name}"
                            )
    return violations


def scan_tree(config: Config, root: Path) -> list[str]:
    files: list[Path] = [p for p in root.rglob("*.py") if p.is_file()]
    return scan_files(config, files)
```

Create `tools/forbidden_imports/BUILD`:
```python
python_sources(name="lib", sources=["src/**/*.py"])

python_tests(
  name="tests",
  sources=["tests/**/*.py"],
  dependencies=[":lib"],
)
```

**Step 3: Run tests**
Run: `python3.12 -m pytest tools/forbidden_imports/tests/test_checker.py -v`
Expected: PASS.

**Step 4: Commit**
```bash
git add tools/forbidden_imports

git commit -m "feat: add forbidden imports checker with ports support"
```

---

### Task 8: Update references to schemas path

**Files:**
- Modify: `services/pantsagon/src/pantsagon/application/pack_validation.py`
- Modify: `services/pantsagon/tests/pack/*` if path is embedded

**Step 1: Write failing test**
Add to `services/pantsagon/tests/pack/test_pack_validation.py` (or equivalent):
```python
from pathlib import Path

from pantsagon.application.pack_validation import _schema_path


def test_schema_path_points_to_shared_contracts() -> None:
    root = Path(__file__).resolve().parents[3]
    assert _schema_path(root).as_posix().endswith("shared/contracts/schemas/pack.schema.v1.json")
```
Expected: FAIL until `_schema_path` is updated.

**Step 2: Update path logic**
Update `services/pantsagon/src/pantsagon/application/pack_validation.py` to compute schema path via repo root:
```python
from pathlib import Path


def _schema_path(root: Path) -> Path:
    return root / "shared/contracts/schemas/pack.schema.v1.json"
```
(Adjust callers to pass repo root as needed.)

**Step 3: Run tests**
Run: `python3.12 -m pytest services/pantsagon/tests/pack/test_pack_validation.py -v`
Expected: PASS.

**Step 4: Commit**
```bash
git add services/pantsagon/src/pantsagon/application/pack_validation.py services/pantsagon/tests/pack/test_pack_validation.py

git commit -m "refactor: update schema path to shared/contracts"
```

---

### Task 9: Generate Pants lockfile and run repo checks

**Files:**
- Create: `3rdparty/python/python-default.lock`

**Step 1: Generate lockfiles**
Run: `pants generate-lockfiles`
Expected: lockfile generated at `3rdparty/python/python-default.lock`.

**Step 2: Run Pants hygiene + tests**
Run:
```bash
pants tailor --check ::
pants update-build-files --check ::
pants lint check test ::
```
Expected: all pass.

**Step 3: Commit**
```bash
git add 3rdparty/python/python-default.lock

git commit -m "chore: generate pants lockfile"
```

---

### Task 10: Final verification

**Files:**
- None (verification only)

**Step 1: Run full test suite**
Run: `python3.12 -m pytest -q`
Expected: PASS.

**Step 2: Run Pants targets for the service only**
Run: `pants lint check test services/pantsagon::`
Expected: PASS.

**Step 3: Commit (if needed)**
If verification steps required changes, commit them. Otherwise, no commit needed.

