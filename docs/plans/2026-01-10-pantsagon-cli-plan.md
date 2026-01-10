# Pantsagon CLI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement Pantsagon v1 as a hexagonal, pack‑based scaffolding CLI (Typer + Copier) that generates enforced Pants hexagonal monorepos with OpenAPI + Docker packs.

**Architecture:** Hexagonal core (domain/application) with ports/adapters. Packs are tool‑agnostic via `pack.yaml` validated by schema. Copier renders templates. `.pantsagon.toml` is the single source of truth for repo state. CLI is a thin adapter.

**Tech Stack:** Python 3.12, Typer, Copier, PyYAML, jsonschema, pytest.

---

### Task 1: Project skeleton + tooling bootstrap

**Files:**
- Create: `pyproject.toml`
- Create: `pantsagon/__init__.py`
- Create: `pantsagon/domain/__init__.py`
- Create: `pantsagon/application/__init__.py`
- Create: `pantsagon/ports/__init__.py`
- Create: `pantsagon/adapters/__init__.py`
- Create: `pantsagon/entrypoints/__init__.py`
- Create: `tests/__init__.py`

**Step 1: Write failing test (package import smoke)**

```python
# tests/test_imports.py

def test_imports():
    import pantsagon
    assert pantsagon.__package__ == "pantsagon"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_imports.py -q`
Expected: FAIL (module not found)

**Step 3: Write minimal implementation**

```python
# pantsagon/__init__.py
__all__ = ["__version__"]
__version__ = "0.1.0"
```

```toml
# pyproject.toml
[build-system]
requires = ["hatchling>=1.21.0"]
build-backend = "hatchling.build"

[project]
name = "pantsagon"
version = "0.1.0"
description = "Hexagonal monorepos, generated with enforcement."
requires-python = ">=3.12"
dependencies = [
  "typer>=0.12",
  "copier>=9.0",
  "pyyaml>=6.0",
  "jsonschema>=4.22",
  "tomli-w>=1.0",
  "rich>=13.7",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-cov>=5.0"]

[project.scripts]
pantsagon = "pantsagon.entrypoints.cli:app"

[tool.pytest.ini_options]
addopts = "-q"
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_imports.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add pyproject.toml pantsagon/__init__.py tests/test_imports.py

git commit -m "chore: bootstrap python package"
```

---

### Task 2: Domain primitives (Diagnostic, Result, Location, PackRef)

**Files:**
- Create: `pantsagon/domain/diagnostics.py`
- Create: `pantsagon/domain/result.py`
- Create: `pantsagon/domain/pack.py`
- Test: `tests/domain/test_diagnostics.py`
- Test: `tests/domain/test_result.py`
- Test: `tests/domain/test_packref.py`

**Step 1: Write failing tests**

```python
# tests/domain/test_diagnostics.py
from pantsagon.domain.diagnostics import Diagnostic, Severity, FileLocation

def test_diagnostic_id_is_deterministic():
    d1 = Diagnostic(code="X", rule="r", severity=Severity.ERROR, message="m", location=FileLocation("a.txt", 1, 2))
    d2 = Diagnostic(code="X", rule="r", severity=Severity.ERROR, message="m", location=FileLocation("a.txt", 1, 2))
    assert d1.id == d2.id
```

```python
# tests/domain/test_result.py
from pantsagon.domain.result import Result
from pantsagon.domain.diagnostics import Diagnostic, Severity

def test_exit_code_precedence_exec_over_validation():
    r = Result(diagnostics=[
        Diagnostic(code="VAL", rule="r", severity=Severity.ERROR, message="v"),
        Diagnostic(code="EXEC", rule="r", severity=Severity.ERROR, message="e", is_execution=True),
    ])
    assert r.exit_code == 3
```

```python
# tests/domain/test_packref.py
from pantsagon.domain.pack import PackRef

def test_packref_supports_future_fields():
    ref = PackRef(id="pantsagon.core", version="1.0.0", source="bundled", location=None, git_ref=None, commit=None, digest=None, subdir=None)
    assert ref.source == "bundled"
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/domain/test_diagnostics.py tests/domain/test_result.py tests/domain/test_packref.py -q`
Expected: FAIL (imports missing)

**Step 3: Write minimal implementation**

```python
# pantsagon/domain/diagnostics.py
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
import hashlib
from typing import Any

class Severity(str, Enum):
    ERROR = "error"
    WARN = "warn"
    INFO = "info"

@dataclass(frozen=True)
class Location:
    kind: str

@dataclass(frozen=True)
class FileLocation(Location):
    path: str
    line: int | None = None
    col: int | None = None
    def __init__(self, path: str, line: int | None = None, col: int | None = None):
        object.__setattr__(self, "kind", "file")
        object.__setattr__(self, "path", path)
        object.__setattr__(self, "line", line)
        object.__setattr__(self, "col", col)

@dataclass(frozen=True)
class Diagnostic:
    code: str
    rule: str
    severity: Severity
    message: str
    location: Location | None = None
    hint: str | None = None
    details: dict[str, Any] | None = None
    is_execution: bool = False
    id: str = field(init=False)

    def __post_init__(self) -> None:
        raw = f"{self.code}|{self.rule}|{self.severity}|{self.message}|{self.location}"
        object.__setattr__(self, "id", hashlib.sha256(raw.encode()).hexdigest()[:12])
```

```python
# pantsagon/domain/result.py
from dataclasses import dataclass, field
from typing import Generic, TypeVar
from pantsagon.domain.diagnostics import Diagnostic, Severity

T = TypeVar("T")

@dataclass
class Result(Generic[T]):
    value: T | None = None
    diagnostics: list[Diagnostic] = field(default_factory=list)
    artifacts: list[dict] = field(default_factory=list)

    @property
    def exit_code(self) -> int:
        has_exec = any(d.is_execution and d.severity == Severity.ERROR for d in self.diagnostics)
        has_val = any((not d.is_execution) and d.severity == Severity.ERROR for d in self.diagnostics)
        if has_exec:
            return 3
        if has_val:
            return 2
        return 0
```

```python
# pantsagon/domain/pack.py
from dataclasses import dataclass
from typing import Literal

PackSource = Literal["bundled", "local", "git", "registry"]

@dataclass(frozen=True)
class PackRef:
    id: str
    version: str
    source: PackSource
    location: str | None = None
    git_ref: str | None = None
    commit: str | None = None
    digest: str | None = None
    subdir: str | None = None
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/domain/test_diagnostics.py tests/domain/test_result.py tests/domain/test_packref.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add pantsagon/domain tests/domain
git commit -m "feat: add domain primitives"
```

---

### Task 3: Pack schema + manifest parsing + Copier cross-check

**Files:**
- Create: `schemas/pack.schema.v1.json`
- Create: `pantsagon/application/pack_validation.py`
- Create: `pantsagon/adapters/policy/pack_validator.py`
- Test: `tests/pack/test_pack_schema.py`
- Test: `tests/pack/test_copier_crosscheck.py`
- Fixture: `tests/fixtures/packs/minimal/pack.yaml`
- Fixture: `tests/fixtures/packs/minimal/copier.yml`

**Step 1: Write failing tests**

```python
# tests/pack/test_pack_schema.py
from pantsagon.application.pack_validation import validate_pack


def test_manifest_schema_validation(tmp_path):
    pack = tmp_path / "pack"
    pack.mkdir()
    (pack / "pack.yaml").write_text("id: x\nversion: 1.0.0\n")
    (pack / "copier.yml").write_text("_min_copier_version: '9.0'\n")
    result = validate_pack(pack)
    assert any(d.code == "PACK_SCHEMA_INVALID" for d in result.diagnostics)
```

```python
# tests/pack/test_copier_crosscheck.py
from pantsagon.application.pack_validation import validate_pack


def test_copier_crosscheck_detects_undeclared_var(tmp_path):
    pack = tmp_path / "pack"
    pack.mkdir()
    (pack / "pack.yaml").write_text("id: x\nversion: 1.0.0\nvariables: [{name: service_name, type: string}]\n")
    (pack / "copier.yml").write_text("service_name: {type: str}\nextra_var: {type: str}\n")
    result = validate_pack(pack)
    assert any(d.code == "PACK_COPIER_UNDECLARED_VAR" for d in result.diagnostics)
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/pack/test_pack_schema.py tests/pack/test_copier_crosscheck.py -q`
Expected: FAIL (missing validator)

**Step 3: Write minimal implementation**

```json
// schemas/pack.schema.v1.json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["id", "version"],
  "properties": {
    "id": {"type": "string"},
    "version": {"type": "string"},
    "description": {"type": "string"},
    "variables": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["name", "type"],
        "properties": {
          "name": {"type": "string"},
          "type": {"type": "string"},
          "default": {}
        }
      }
    }
  }
}
```

```python
# pantsagon/adapters/policy/pack_validator.py
from __future__ import annotations
import json
from pathlib import Path
import yaml
import jsonschema
from pantsagon.domain.diagnostics import Diagnostic, Severity

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "pack.schema.v1.json"


def load_manifest(pack_dir: Path) -> dict:
    return yaml.safe_load((pack_dir / "pack.yaml").read_text()) or {}


def load_copier_vars(pack_dir: Path) -> set[str]:
    data = yaml.safe_load((pack_dir / "copier.yml").read_text()) or {}
    return {k for k in data.keys() if not k.startswith("_")}


def validate_manifest_schema(manifest: dict) -> list[Diagnostic]:
    schema = json.loads(SCHEMA_PATH.read_text())
    try:
        jsonschema.validate(manifest, schema)
        return []
    except jsonschema.ValidationError as e:
        return [Diagnostic(code="PACK_SCHEMA_INVALID", rule="pack.schema", severity=Severity.ERROR, message=str(e))]


def crosscheck_variables(manifest: dict, copier_vars: set[str]) -> list[Diagnostic]:
    declared = {v["name"] for v in manifest.get("variables", [])}
    diagnostics: list[Diagnostic] = []
    undeclared = copier_vars - declared
    for var in sorted(undeclared):
        diagnostics.append(Diagnostic(code="PACK_COPIER_UNDECLARED_VAR", rule="pack.copier", severity=Severity.ERROR, message=f"Undeclared variable: {var}"))
    return diagnostics
```

```python
# pantsagon/application/pack_validation.py
from pathlib import Path
from pantsagon.domain.result import Result
from pantsagon.adapters.policy.pack_validator import load_manifest, load_copier_vars, validate_manifest_schema, crosscheck_variables


def validate_pack(pack_path: Path) -> Result[dict]:
    manifest = load_manifest(pack_path)
    copier_vars = load_copier_vars(pack_path)
    diags = []
    diags.extend(validate_manifest_schema(manifest))
    diags.extend(crosscheck_variables(manifest, copier_vars))
    return Result(value=manifest, diagnostics=diags)
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/pack/test_pack_schema.py tests/pack/test_copier_crosscheck.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add schemas pantsagon/application/pack_validation.py pantsagon/adapters/policy/pack_validator.py tests/pack
git commit -m "feat: add pack schema validation"
```

---

### Task 4: Ports + AdapterError taxonomy

**Files:**
- Create: `pantsagon/ports/pack_catalog.py`
- Create: `pantsagon/ports/renderer.py`
- Create: `pantsagon/ports/workspace.py`
- Create: `pantsagon/ports/policy_engine.py`
- Create: `pantsagon/ports/command_runner.py`
- Create: `pantsagon/adapters/errors.py`
- Test: `tests/adapters/test_adapter_errors.py`

**Step 1: Write failing test**

```python
# tests/adapters/test_adapter_errors.py
from pantsagon.adapters.errors import RendererExecutionError

def test_adapter_error_has_message_and_details():
    err = RendererExecutionError("boom", details={"x": 1})
    assert "boom" in str(err)
    assert err.details["x"] == 1
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/adapters/test_adapter_errors.py -q`
Expected: FAIL (missing class)

**Step 3: Write minimal implementation**

```python
# pantsagon/adapters/errors.py
from dataclasses import dataclass
from typing import Any

@dataclass
class AdapterError(Exception):
    message: str
    details: dict[str, Any] | None = None
    hint: str | None = None
    cause: Exception | None = None

    def __str__(self) -> str:
        return self.message

class PackFetchError(AdapterError):
    pass

class PackReadError(AdapterError):
    pass

class PackParseError(AdapterError):
    pass

class RendererTemplateError(AdapterError):
    pass

class RendererExecutionError(AdapterError):
    pass

class WorkspaceTransactionError(AdapterError):
    pass

class WorkspaceCommitError(AdapterError):
    pass

class CommandNotFound(AdapterError):
    pass

class CommandFailed(AdapterError):
    pass

class CommandTimeout(AdapterError):
    pass
```

```python
# pantsagon/ports/renderer.py
from typing import Protocol
from dataclasses import dataclass
from pathlib import Path
from pantsagon.domain.pack import PackRef

@dataclass
class RenderRequest:
    pack: PackRef
    pack_path: Path
    staging_dir: Path
    answers: dict
    allow_hooks: bool

@dataclass
class RenderOutcome:
    rendered_paths: list[Path]
    warnings: list[str]

class RendererPort(Protocol):
    def render(self, request: RenderRequest) -> RenderOutcome: ...
```

(Implement similar Protocols for pack_catalog, workspace, policy_engine, command_runner.)

**Step 4: Run tests to verify they pass**

Run: `pytest tests/adapters/test_adapter_errors.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add pantsagon/ports pantsagon/adapters/errors.py tests/adapters/test_adapter_errors.py

git commit -m "feat: add ports and adapter error taxonomy"
```

---

### Task 5: Pack catalog adapters (bundled + local)

**Files:**
- Create: `pantsagon/adapters/pack_catalog/bundled.py`
- Create: `pantsagon/adapters/pack_catalog/local.py`
- Test: `tests/adapters/test_pack_catalog.py`
- Fixture: `tests/fixtures/packs/minimal/pack.yaml`
- Fixture: `tests/fixtures/packs/minimal/copier.yml`

**Step 1: Write failing test**

```python
# tests/adapters/test_pack_catalog.py
from pathlib import Path
from pantsagon.adapters.pack_catalog.local import LocalPackCatalog


def test_local_pack_catalog_loads_manifest(tmp_path):
    pack = tmp_path / "pack"
    pack.mkdir()
    (pack / "pack.yaml").write_text("id: x\nversion: 1.0.0\n")
    (pack / "copier.yml").write_text("_min_copier_version: '9.0'\n")
    catalog = LocalPackCatalog()
    manifest = catalog.load_manifest(pack)
    assert manifest["id"] == "x"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/adapters/test_pack_catalog.py -q`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# pantsagon/adapters/pack_catalog/local.py
from pathlib import Path
import yaml

class LocalPackCatalog:
    def load_manifest(self, pack_dir: Path) -> dict:
        return yaml.safe_load((pack_dir / "pack.yaml").read_text()) or {}
```

```python
# pantsagon/adapters/pack_catalog/bundled.py
from pathlib import Path

class BundledPackCatalog:
    def __init__(self, root: Path) -> None:
        self.root = root

    def get_pack_path(self, pack_id: str) -> Path:
        return self.root / pack_id.split(".")[-1]
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/adapters/test_pack_catalog.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add pantsagon/adapters/pack_catalog tests/adapters/test_pack_catalog.py

git commit -m "feat: add pack catalog adapters"
```

---

### Task 6: Renderer adapter (Copier)

**Files:**
- Create: `pantsagon/adapters/renderer/copier_renderer.py`
- Test: `tests/adapters/test_renderer_copier.py`
- Fixture: `tests/fixtures/packs/minimal/templates/README.md.jinja`

**Step 1: Write failing test**

```python
# tests/adapters/test_renderer_copier.py
from pathlib import Path
from pantsagon.adapters.renderer.copier_renderer import CopierRenderer
from pantsagon.domain.pack import PackRef
from pantsagon.ports.renderer import RenderRequest


def test_copier_renders_template(tmp_path):
    pack = tmp_path / "pack"
    (pack / "templates").mkdir(parents=True)
    (pack / "pack.yaml").write_text("id: x\nversion: 1.0.0\nvariables: [{name: name, type: string}]\n")
    (pack / "copier.yml").write_text("name: {type: str}\n_templates_suffix: '.jinja'\n_subdirectory: 'templates'\n")
    (pack / "templates" / "README.md.jinja").write_text("Hello {{ name }}")
    out = tmp_path / "out"
    out.mkdir()
    req = RenderRequest(pack=PackRef(id="x", version="1.0.0", source="local"), pack_path=pack, staging_dir=out, answers={"name": "World"}, allow_hooks=False)
    result = CopierRenderer().render(req)
    assert (out / "README.md").read_text() == "Hello World"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/adapters/test_renderer_copier.py -q`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# pantsagon/adapters/renderer/copier_renderer.py
from copier import run_copy
from pantsagon.adapters.errors import RendererExecutionError
from pantsagon.ports.renderer import RenderRequest, RenderOutcome

class CopierRenderer:
    def render(self, request: RenderRequest) -> RenderOutcome:
        try:
            run_copy(
                str(request.pack_path),
                str(request.staging_dir),
                data=request.answers,
                unsafe=request.allow_hooks,
            )
        except Exception as e:  # Copier raises various exceptions
            raise RendererExecutionError("Copier failed", details={"pack": request.pack.id}, cause=e)
        return RenderOutcome(rendered_paths=[request.staging_dir], warnings=[])
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/adapters/test_renderer_copier.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add pantsagon/adapters/renderer tests/adapters/test_renderer_copier.py

git commit -m "feat: add copier renderer adapter"
```

---

### Task 7: Workspace adapter with staging + atomic commit (init + add service)

**Files:**
- Create: `pantsagon/adapters/workspace/filesystem.py`
- Test: `tests/adapters/test_workspace.py`

**Step 1: Write failing test**

```python
# tests/adapters/test_workspace.py
from pathlib import Path
from pantsagon.adapters.workspace.filesystem import FilesystemWorkspace


def test_workspace_commit_writes_files(tmp_path):
    ws = FilesystemWorkspace(tmp_path)
    stage = ws.begin_transaction()
    (stage / "hello.txt").write_text("hi")
    ws.commit(stage)
    assert (tmp_path / "hello.txt").read_text() == "hi"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/adapters/test_workspace.py -q`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# pantsagon/adapters/workspace/filesystem.py
from pathlib import Path
import shutil
import tempfile
from pantsagon.adapters.errors import WorkspaceCommitError

class FilesystemWorkspace:
    def __init__(self, root: Path) -> None:
        self.root = root

    def begin_transaction(self) -> Path:
        return Path(tempfile.mkdtemp(prefix="pantsagon-stage-", dir=self.root.parent))

    def commit(self, stage: Path) -> None:
        try:
            for path in stage.rglob("*"):
                rel = path.relative_to(stage)
                dest = self.root / rel
                if path.is_dir():
                    dest.mkdir(parents=True, exist_ok=True)
                else:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(path, dest)
        except Exception as e:
            raise WorkspaceCommitError("Workspace commit failed", cause=e)
        finally:
            shutil.rmtree(stage, ignore_errors=True)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/adapters/test_workspace.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add pantsagon/adapters/workspace tests/adapters/test_workspace.py

git commit -m "feat: add filesystem workspace adapter"
```

---

### Task 8: Application use-cases (init / add service / validate)

**Files:**
- Create: `pantsagon/application/init_repo.py`
- Create: `pantsagon/application/add_service.py`
- Create: `pantsagon/application/validate_repo.py`
- Test: `tests/application/test_init_repo.py`
- Test: `tests/application/test_add_service.py`

**Step 1: Write failing tests**

```python
# tests/application/test_init_repo.py
from pathlib import Path
from pantsagon.application.init_repo import init_repo


def test_init_repo_writes_lock(tmp_path, monkeypatch):
    result = init_repo(repo_path=tmp_path, languages=["python"], services=["monitors"], features=["openapi"], renderer="copier")
    assert (tmp_path / ".pantsagon.toml").exists()
```

```python
# tests/application/test_add_service.py
from pathlib import Path
from pantsagon.application.add_service import add_service


def test_add_service_fails_on_existing(tmp_path):
    (tmp_path / ".pantsagon.toml").write_text("[tool]\nname='pantsagon'\nversion='0.1.0'\n")
    svc_dir = tmp_path / "services" / "foo"
    svc_dir.mkdir(parents=True)
    result = add_service(repo_path=tmp_path, name="foo", lang="python")
    assert any(d.code == "SERVICE_EXISTS" for d in result.diagnostics)
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/application/test_init_repo.py tests/application/test_add_service.py -q`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# pantsagon/application/init_repo.py
from pathlib import Path
from pantsagon.domain.result import Result
from pantsagon.domain.diagnostics import Diagnostic, Severity
import tomli_w


def init_repo(repo_path: Path, languages: list[str], services: list[str], features: list[str], renderer: str) -> Result[None]:
    lock = {
        "tool": {"name": "pantsagon", "version": "0.1.0"},
        "settings": {"renderer": renderer, "strict": False, "strict_manifest": True, "allow_hooks": False},
        "selection": {"languages": languages, "features": features, "services": services, "augmented_coding": "none"},
        "resolved": {"packs": [], "answers": {}},
    }
    (repo_path / ".pantsagon.toml").write_text(tomli_w.dumps(lock))
    return Result()
```

```python
# pantsagon/application/add_service.py
from pathlib import Path
from pantsagon.domain.result import Result
from pantsagon.domain.diagnostics import Diagnostic, Severity


def add_service(repo_path: Path, name: str, lang: str) -> Result[None]:
    svc_dir = repo_path / "services" / name
    if svc_dir.exists():
        return Result(diagnostics=[Diagnostic(code="SERVICE_EXISTS", rule="service.name", severity=Severity.ERROR, message="Service already exists")])
    return Result()
```

```python
# pantsagon/application/validate_repo.py
from pathlib import Path
from pantsagon.domain.result import Result


def validate_repo(repo_path: Path) -> Result[None]:
    return Result()
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/application/test_init_repo.py tests/application/test_add_service.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add pantsagon/application tests/application

git commit -m "feat: add minimal use-case scaffolds"
```

---

### Task 9: CLI entrypoint with Typer + JSON output

**Files:**
- Create: `pantsagon/entrypoints/cli.py`
- Test: `tests/entrypoints/test_cli_init.py`

**Step 1: Write failing test**

```python
# tests/entrypoints/test_cli_init.py
from typer.testing import CliRunner
from pantsagon.entrypoints.cli import app


def test_cli_init_writes_lock(tmp_path):
    runner = CliRunner()
    result = runner.invoke(app, ["init", str(tmp_path), "--lang", "python", "--services", "monitors", "--feature", "openapi"])
    assert result.exit_code == 0
    assert (tmp_path / ".pantsagon.toml").exists()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/entrypoints/test_cli_init.py -q`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# pantsagon/entrypoints/cli.py
import typer
from pathlib import Path
from pantsagon.application.init_repo import init_repo

app = typer.Typer(add_completion=False)

@app.command()
def init(repo: Path, lang: str = typer.Option(...), services: str = "", feature: list[str] = typer.Option(None)):
    features = feature or []
    svc_list = [s for s in services.split(",") if s]
    init_repo(repo, [lang], svc_list, features, renderer="copier")
    raise typer.Exit(0)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/entrypoints/test_cli_init.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add pantsagon/entrypoints tests/entrypoints

git commit -m "feat: add minimal typer cli"
```

---

### Task 10: Bundled packs (core/python/openapi/docker) + pack tests

**Files:**
- Create: `packs/core/pack.yaml`, `packs/core/copier.yml`, `packs/core/templates/...`
- Create: `packs/python/pack.yaml`, `packs/python/copier.yml`, `packs/python/templates/...`
- Create: `packs/openapi/pack.yaml`, `packs/openapi/copier.yml`, `packs/openapi/templates/...`
- Create: `packs/docker/pack.yaml`, `packs/docker/copier.yml`, `packs/docker/templates/...`
- Test: `tests/packs/test_bundled_packs.py`

**Step 1: Write failing test**

```python
# tests/packs/test_bundled_packs.py
from pathlib import Path
from pantsagon.application.pack_validation import validate_pack


def test_all_bundled_packs_validate():
    packs_dir = Path(__file__).resolve().parents[2] / "packs"
    for pack in ["core", "python", "openapi", "docker"]:
        result = validate_pack(packs_dir / pack)
        assert not [d for d in result.diagnostics if d.severity.value == "error"]
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/packs/test_bundled_packs.py -q`
Expected: FAIL (missing packs)

**Step 3: Write minimal templates**

Create minimal `pack.yaml` + `copier.yml` and core skeleton templates for each pack. Example for core:

```yaml
# packs/core/pack.yaml
id: pantsagon.core
version: 1.0.0
description: Core monorepo skeleton
variables:
  - name: repo_name
    type: string
```

```yaml
# packs/core/copier.yml
_min_copier_version: "9.0.0"
_subdirectory: "templates"
_templates_suffix: ".jinja"
repo_name:
  type: str
  default: "repo"
```

```text
# packs/core/templates/pants.toml.jinja
[GLOBAL]
pants_version = "2.30.0"
```

Repeat for python/openapi/docker with minimal placeholders.

**Step 4: Run tests to verify they pass**

Run: `pytest tests/packs/test_bundled_packs.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add packs tests/packs/test_bundled_packs.py

git commit -m "feat: add bundled packs and pack tests"
```

---

### Task 11: E2E init test (deterministic mode)

**Files:**
- Test: `tests/e2e/test_init_e2e.py`

**Step 1: Write failing test**

```python
# tests/e2e/test_init_e2e.py
from pathlib import Path
from pantsagon.entrypoints.cli import app
from typer.testing import CliRunner


def test_init_generates_core_files(tmp_path, monkeypatch):
    monkeypatch.setenv("PANTSAGON_DETERMINISTIC", "1")
    runner = CliRunner()
    result = runner.invoke(app, ["init", str(tmp_path), "--lang", "python", "--services", "monitors", "--feature", "openapi", "--feature", "docker"])
    assert result.exit_code == 0
    assert (tmp_path / "pants.toml").exists()
    assert (tmp_path / ".pantsagon.toml").exists()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/e2e/test_init_e2e.py -q`
Expected: FAIL

**Step 3: Implement deterministic mode hook**

Add a global helper in `pantsagon/domain/determinism.py` to fix timestamps or skip them, and ensure CLI honors `PANTSAGON_DETERMINISTIC=1` by passing a deterministic flag into render/use-cases (even if no timestamps are emitted in v1).

**Step 4: Run test to verify it passes**

Run: `pytest tests/e2e/test_init_e2e.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/e2e/test_init_e2e.py pantsagon/domain/determinism.py

git commit -m "test: add deterministic e2e init"
```

---

### Task 12: Polish CLI flags + augmented-coding option

**Files:**
- Modify: `pantsagon/entrypoints/cli.py`
- Modify: `pantsagon/application/init_repo.py`
- Test: `tests/entrypoints/test_cli_augmented.py`

**Step 1: Write failing test**

```python
# tests/entrypoints/test_cli_augmented.py
from typer.testing import CliRunner
from pantsagon.entrypoints.cli import app


def test_augmented_coding_creates_agents_file(tmp_path):
    runner = CliRunner()
    result = runner.invoke(app, ["init", str(tmp_path), "--lang", "python", "--augmented-coding", "agents"])
    assert result.exit_code == 0
    assert (tmp_path / "AGENTS.md").exists()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/entrypoints/test_cli_augmented.py -q`
Expected: FAIL

**Step 3: Write minimal implementation**

Update `init_repo` to create AGENTS/CLAUDE/GEMINI file based on selection, and persist `selection.augmented_coding` in `.pantsagon.toml`.

```python
# pantsagon/application/init_repo.py (snippet)
augmented = augmented_coding or "none"
lock["selection"]["augmented_coding"] = augmented
if augmented == "agents":
    (repo_path / "AGENTS.md").write_text("# AGENTS\n")
elif augmented == "claude":
    (repo_path / "CLAUDE.md").write_text("# CLAUDE\n")
elif augmented == "gemini":
    (repo_path / "GEMINI.md").write_text("# GEMINI\n")
```

Update CLI options:

```python
# pantsagon/entrypoints/cli.py (snippet)
augmented_coding: str = typer.Option("none", "--augmented-coding")
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/entrypoints/test_cli_augmented.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add pantsagon/application/init_repo.py pantsagon/entrypoints/cli.py tests/entrypoints/test_cli_augmented.py

git commit -m "feat: add augmented coding file option"
```

---

Plan complete and saved to `docs/plans/2026-01-10-pantsagon-cli-plan.md`.

Two execution options:

1. Subagent-Driven (this session) — I dispatch a fresh subagent per task, review between tasks.
2. Parallel Session (separate) — Open a new session with executing-plans and batch execution.

Which approach would you like?
