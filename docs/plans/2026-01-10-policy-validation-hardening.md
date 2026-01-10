# Policy + Validation Hardening Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement M5 naming rules, strictness tiers, diagnostic codes/locations, and documentation updates with deterministic validation behavior.

**Architecture:** Add a small domain validation module (pure, side‑effect free) for naming and strictness, then wire it into application orchestration (init/add/validate) with explicit phase ordering and strictness precedence. Schemas remain defensive guardrails; semantics live in domain validators.

**Tech Stack:** Python 3.12, pytest, jsonschema, typer, copier.

### Task 1: Add strictness upgradeable support in diagnostics

**Files:**
- Modify: `pantsagon/domain/diagnostics.py`
- Create: `pantsagon/domain/strictness.py`
- Test: `tests/domain/test_strictness.py`

**Step 1: Write the failing test** (@superpowers:test-driven-development)

```python
# tests/domain/test_strictness.py
from pantsagon.domain.diagnostics import Diagnostic, Severity
from pantsagon.domain.strictness import apply_strictness

def test_strictness_only_upgrades_upgradeable_warnings():
    diags = [
        Diagnostic(code="W_UP", rule="r", severity=Severity.WARN, message="warn", upgradeable=True),
        Diagnostic(code="W_NO", rule="r", severity=Severity.WARN, message="warn", upgradeable=False),
        Diagnostic(code="E", rule="r", severity=Severity.ERROR, message="err"),
    ]
    strict = apply_strictness(diags, strict=True)
    assert [d.severity.value for d in strict] == ["error", "warn", "error"]

    non_strict = apply_strictness(diags, strict=False)
    assert [d.severity.value for d in non_strict] == ["warn", "warn", "error"]
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/domain/test_strictness.py -q`
Expected: FAIL with `ImportError` or `AttributeError` because `upgradeable` / `apply_strictness` do not exist yet.

**Step 3: Write minimal implementation**

```python
# pantsagon/domain/diagnostics.py
@dataclass(frozen=True)
class Diagnostic:
    ...
    upgradeable: bool = False
```

```python
# pantsagon/domain/strictness.py
from __future__ import annotations
from pantsagon.domain.diagnostics import Diagnostic, Severity

def apply_strictness(diagnostics: list[Diagnostic], strict: bool) -> list[Diagnostic]:
    if not strict:
        return diagnostics
    upgraded: list[Diagnostic] = []
    for d in diagnostics:
        if d.severity == Severity.WARN and d.upgradeable:
            upgraded.append(d.__class__(**{**d.__dict__, "severity": Severity.ERROR}))
        else:
            upgraded.append(d)
    return upgraded
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/domain/test_strictness.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add pantsagon/domain/diagnostics.py pantsagon/domain/strictness.py tests/domain/test_strictness.py
git commit -m "feat: add upgradeable strictness handling"
```

### Task 2: Add naming validators + reserved name policy

**Files:**
- Create: `pantsagon/domain/naming.py`
- Modify: `pantsagon/domain/diagnostics.py`
- Test: `tests/domain/test_naming.py`

**Step 1: Write the failing test**

```python
# tests/domain/test_naming.py
from pantsagon.domain.naming import (
    validate_service_name,
    validate_pack_id,
    validate_feature_name,
    BUILTIN_RESERVED_SERVICES,
)

def test_service_name_rules():
    assert validate_service_name("my-service", BUILTIN_RESERVED_SERVICES, set()) == []
    assert validate_service_name("MyService", BUILTIN_RESERVED_SERVICES, set())
    assert validate_service_name("bad--name", BUILTIN_RESERVED_SERVICES, set())
    assert validate_service_name("trailing-", BUILTIN_RESERVED_SERVICES, set())
    assert validate_service_name("services", BUILTIN_RESERVED_SERVICES, set())


def test_pack_id_rules():
    assert validate_pack_id("pantsagon.core") == []
    assert validate_pack_id("Pantsagon.Core")
    assert validate_pack_id("nope")


def test_feature_name_rules():
    assert validate_feature_name("openapi") == []
    assert validate_feature_name("snake_case") == []
    assert validate_feature_name("bad.name")
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/domain/test_naming.py -q`
Expected: FAIL with `ImportError` because naming validators do not exist.

**Step 3: Write minimal implementation**

```python
# pantsagon/domain/naming.py
import re
import keyword
from pantsagon.domain.diagnostics import Diagnostic, Severity
from pantsagon.domain.diagnostics import Location

SERVICE_PATTERN = re.compile(r"^[a-z](?:[a-z0-9]*(-[a-z0-9]+)*)$")
PACK_ID_PATTERN = re.compile(r"^[a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*)+$")
FEATURE_PATTERN = re.compile(r"^[a-z][a-z0-9_-]*$")

BUILTIN_RESERVED_SERVICES = {
    "services", "shared", "tools", "docs", "packs", "schemas", "infra", "tests",
    "domain", "ports", "application", "adapters", "entrypoints",
    "pantsagon", "core", "foundation",
    *keyword.kwlist,
}

class ValueLocation(Location):
    value: str
    field: str
    def __init__(self, field: str, value: str):
        object.__setattr__(self, "kind", "value")
        object.__setattr__(self, "field", field)
        object.__setattr__(self, "value", value)


def validate_service_name(name: str, builtins: set[str], project: set[str]) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    if not SERVICE_PATTERN.match(name):
        diags.append(Diagnostic(code="SERVICE_NAME_INVALID", rule="naming.service.format", severity=Severity.ERROR,
            message=f"Invalid service name: {name}", location=ValueLocation("service", name)))
        return diags
    if name in builtins:
        diags.append(Diagnostic(code="SERVICE_NAME_RESERVED", rule="naming.service.reserved", severity=Severity.ERROR,
            message=f"Service name is reserved: {name}", location=ValueLocation("service", name), details={"scope":"builtin"}))
    if name in project:
        diags.append(Diagnostic(code="SERVICE_NAME_RESERVED", rule="naming.service.reserved", severity=Severity.ERROR,
            message=f"Service name is reserved: {name}", location=ValueLocation("service", name), details={"scope":"project"}))
    return diags


def validate_pack_id(pack_id: str) -> list[Diagnostic]:
    if PACK_ID_PATTERN.match(pack_id):
        return []
    return [Diagnostic(code="PACK_ID_INVALID", rule="naming.pack.id", severity=Severity.ERROR,
        message=f"Invalid pack id: {pack_id}", location=ValueLocation("pack.id", pack_id))]


def validate_feature_name(feature: str) -> list[Diagnostic]:
    if FEATURE_PATTERN.match(feature) and "." not in feature:
        return []
    return [Diagnostic(code="FEATURE_NAME_INVALID", rule="naming.feature.format", severity=Severity.ERROR,
        message=f"Invalid feature name: {feature}", location=ValueLocation("feature", feature))]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/domain/test_naming.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add pantsagon/domain/naming.py pantsagon/domain/diagnostics.py tests/domain/test_naming.py
git commit -m "feat: add naming validators"
```

### Task 3: Add new diagnostic codes + regenerate reference docs

**Files:**
- Modify: `pantsagon/diagnostics/codes.yaml`
- Modify (generated): `docs/reference/diagnostic-codes.md`

**Step 1: Add codes to YAML**

Add entries for:
- `SERVICE_NAME_INVALID` (error)
- `SERVICE_NAME_RESERVED` (error)
- `PACK_ID_INVALID` (error)
- `FEATURE_NAME_INVALID` (error)
- `FEATURE_NAME_SHADOWS_PACK` (warn, upgradeable)
- `LOCK_INVALID` (error)

**Step 2: Regenerate docs**

Run: `python scripts/generate_diagnostic_codes.py`
Expected: `Generated docs/reference/diagnostic-codes.md`

**Step 3: Commit**

```bash
git add pantsagon/diagnostics/codes.yaml docs/reference/diagnostic-codes.md
git commit -m "docs: add naming diagnostics"
```

### Task 4: Load repo lock + strictness precedence + validate_repo phases

**Files:**
- Create: `pantsagon/application/repo_lock.py`
- Modify: `pantsagon/application/validate_repo.py`
- Modify: `tests/application/test_validate_repo.py`

**Step 1: Write failing tests**

```python
# tests/application/test_validate_repo.py
from pantsagon.application.validate_repo import validate_repo

def test_validate_repo_missing_lock(tmp_path):
    result = validate_repo(repo_path=tmp_path)
    assert any(d.code == "LOCK_MISSING" for d in result.diagnostics)

def test_validate_repo_invalid_lock(tmp_path):
    (tmp_path / ".pantsagon.toml").write_text("not=toml:::")
    result = validate_repo(repo_path=tmp_path)
    assert any(d.code == "LOCK_INVALID" for d in result.diagnostics)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/application/test_validate_repo.py -q`
Expected: FAIL with missing `LOCK_INVALID` behavior.

**Step 3: Minimal implementation**

```python
# pantsagon/application/repo_lock.py
import tomllib
from pathlib import Path
from pantsagon.domain.diagnostics import Diagnostic, Severity, FileLocation


def load_repo_lock(repo_path: Path) -> tuple[dict | None, list[Diagnostic]]:
    lock_path = repo_path / ".pantsagon.toml"
    if not lock_path.exists():
        return None, [Diagnostic(code="LOCK_MISSING", rule="repo.lock.missing", severity=Severity.ERROR,
            message="Missing .pantsagon.toml", location=FileLocation(str(lock_path)))]
    try:
        return tomllib.loads(lock_path.read_text()), []
    except Exception as e:
        return None, [Diagnostic(code="LOCK_INVALID", rule="repo.lock.invalid", severity=Severity.ERROR,
            message=f"Invalid .pantsagon.toml: {e}", location=FileLocation(str(lock_path)))]


def effective_strict(cli_strict: bool | None, lock: dict | None) -> bool:
    if cli_strict is not None:
        return cli_strict
    if lock is None:
        return False
    return bool(lock.get("settings", {}).get("strict", False))


def project_reserved_services(lock: dict | None) -> set[str]:
    if not lock:
        return set()
    return set(lock.get("settings", {}).get("naming", {}).get("reserved_services", []) or [])
```

Update `validate_repo` to:
- call `load_repo_lock`
- if lock invalid/missing, return diagnostics immediately (skip later phases)
- otherwise run phase 1/2/3 and apply `apply_strictness` at the end

**Step 4: Run tests**

Run: `pytest tests/application/test_validate_repo.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add pantsagon/application/repo_lock.py pantsagon/application/validate_repo.py tests/application/test_validate_repo.py
git commit -m "feat: load repo lock and validate phases"
```

### Task 5: Pack validation naming + default mismatch warnings

**Files:**
- Modify: `pantsagon/adapters/policy/pack_validator.py`
- Modify: `pantsagon/application/pack_validation.py`
- Test: `tests/pack/test_pack_schema.py`
- Create: `tests/pack/test_pack_naming.py`
- Create: `tests/pack/test_copier_defaults.py`

**Step 1: Write failing tests**

```python
# tests/pack/test_pack_naming.py
from pantsagon.application.pack_validation import validate_pack

def test_pack_id_must_be_namespaced(tmp_path):
    pack = tmp_path / "pack"
    pack.mkdir()
    (pack / "pack.yaml").write_text("id: bad\nversion: 1.0.0\ncompatibility: {pants: '>=2.0.0'}")
    (pack / "copier.yml").write_text("_min_copier_version: '9.0'\n")
    result = validate_pack(pack)
    assert any(d.code == "PACK_ID_INVALID" for d in result.diagnostics)
```

```python
# tests/pack/test_copier_defaults.py
from pantsagon.application.pack_validation import validate_pack

def test_default_mismatch_warns(tmp_path):
    pack = tmp_path / "pack"
    pack.mkdir()
    (pack / "pack.yaml").write_text(
        "id: pantsagon.core\nversion: 1.0.0\ncompatibility: {pants: '>=2.0.0'}\nvariables: [{name: repo_name, type: string, default: repo}]\n"
    )
    (pack / "copier.yml").write_text("repo_name: {type: str, default: other}\n")
    result = validate_pack(pack)
    assert any(d.code == "COPIER_DEFAULT_MISMATCH" for d in result.diagnostics)
```

**Step 2: Run tests to verify failure**

Run: `pytest tests/pack/test_pack_naming.py tests/pack/test_copier_defaults.py -q`
Expected: FAIL with missing diagnostics.

**Step 3: Minimal implementation**

- In `pack_validator.py`, after schema validation, call `validate_pack_id`, `validate_feature_name` for each `provides.features`, and `validate_variable_name` for each variable.
- Add default mismatch detection: when both pack variable default and copier default exist and differ, emit `COPIER_DEFAULT_MISMATCH` with `Severity.WARN` and `upgradeable=True` and a `FileLocation` on `pack.yaml`.
- Keep diagnostics in deterministic order; sort inputs as needed.

**Step 4: Run tests**

Run: `pytest tests/pack/test_pack_naming.py tests/pack/test_copier_defaults.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add pantsagon/adapters/policy/pack_validator.py pantsagon/application/pack_validation.py tests/pack/test_pack_naming.py tests/pack/test_copier_defaults.py

git commit -m "feat: validate pack ids and default mismatches"
```

### Task 6: Service/init validation + strict CLI flags

**Files:**
- Modify: `pantsagon/application/add_service.py`
- Modify: `pantsagon/application/init_repo.py`
- Modify: `pantsagon/application/rendering.py`
- Modify: `pantsagon/entrypoints/cli.py`
- Test: `tests/application/test_add_service.py`
- Create: `tests/application/test_init_validation.py`

**Step 1: Write failing tests**

```python
# tests/application/test_add_service.py
from pantsagon.application.add_service import add_service

def test_add_service_rejects_reserved(tmp_path):
    (tmp_path / ".pantsagon.toml").write_text("[settings.naming]\nreserved_services=['api']\n")
    result = add_service(repo_path=tmp_path, name="api", lang="python")
    assert any(d.code == "SERVICE_NAME_RESERVED" for d in result.diagnostics)
```

```python
# tests/application/test_init_validation.py
from pantsagon.application.init_repo import init_repo

def test_init_rejects_invalid_service_name(tmp_path):
    result = init_repo(repo_path=tmp_path, languages=["python"], services=["bad--name"], features=[], renderer="copier")
    assert any(d.code == "SERVICE_NAME_INVALID" for d in result.diagnostics)
```

**Step 2: Run tests to verify failure**

Run: `pytest tests/application/test_add_service.py tests/application/test_init_validation.py -q`
Expected: FAIL with missing diagnostics.

**Step 3: Minimal implementation**

- In `add_service`, load repo lock, compute project reserved list, validate service name with built-ins + project names before filesystem checks.
- In `init_repo`, validate services list early (built-ins only) and return diagnostics if invalid.
- Thread `strict` flag through CLI (`--strict`) and into `init_repo` / `add_service` / `validate_repo` with precedence rules.
- Apply `apply_strictness` to diagnostics before returning from application functions.

**Step 4: Run tests**

Run: `pytest tests/application/test_add_service.py tests/application/test_init_validation.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add pantsagon/application/add_service.py pantsagon/application/init_repo.py pantsagon/application/rendering.py pantsagon/entrypoints/cli.py tests/application/test_add_service.py tests/application/test_init_validation.py

git commit -m "feat: enforce service naming and strict flags"
```

### Task 7: Update schemas + regenerate schema docs

**Files:**
- Modify: `schemas/pack.schema.v1.json`
- Modify: `schemas/repo-lock.schema.v1.json`
- Modify (generated): `docs/reference/pack.schema.v1.md`, `docs/reference/repo-lock.schema.v1.md`

**Step 1: Update schemas**

- `pack.schema.v1.json`: tighten `id` and `requires.packs` patterns to dot‑namespaced IDs.
- `pack.schema.v1.json`: add `provides.features` items pattern `^[a-z][a-z0-9_-]*$`.
- `repo-lock.schema.v1.json`: add `settings.naming.reserved_services` array of strings.
- `repo-lock.schema.v1.json`: update `selection.services` pattern to `^[a-z](?:[a-z0-9]*(-[a-z0-9]+)*)$`.

**Step 2: Regenerate docs**

Run: `python scripts/generate_schema_docs.py`
Expected: `Generated schema docs into docs/reference`

**Step 3: Commit**

```bash
git add schemas/pack.schema.v1.json schemas/repo-lock.schema.v1.json docs/reference/pack.schema.v1.md docs/reference/repo-lock.schema.v1.md

git commit -m "docs: tighten schemas for naming rules"
```

### Task 8: Update README + full test run

**Files:**
- Modify: `README.md`

**Step 1: Update README**

Add a short “Validation & Strictness” section documenting:
- strict naming for services + reserved names
- pack id namespace rules
- `--strict` upgrades warnings to errors
- `.pantsagon.toml` additive reserved service names

**Step 2: Run full tests**

Run: `pytest -q`
Expected: PASS (note pytest-asyncio warning is acceptable per README).

**Step 3: Commit**

```bash
git add README.md
git commit -m "docs: describe validation behavior"
```

---

Plan complete and saved to `docs/plans/2026-01-10-policy-validation-hardening.md`. Two execution options:

1. Subagent-Driven (this session) — I dispatch fresh subagent per task, review between tasks, fast iteration
2. Parallel Session (separate) — Open new session with executing-plans, batch execution with checkpoints

Which approach?
