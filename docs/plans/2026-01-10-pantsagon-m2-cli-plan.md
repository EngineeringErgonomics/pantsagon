# Pantsagon M2 CLI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Complete the v1 M2 CLI surface: add `add service`, `validate`, JSON output, and exit-code precedence, with README updates.

**Architecture:** Extend the application layer with add/validate use-cases and validation helpers, wire into Typer CLI, and serialize Result objects for `--json`. Keep logic in application/domain, CLI thin.

**Tech Stack:** Python 3.12, Typer, pytest.

---

### Task 1: Result serialization for JSON output

**Files:**
- Create: `pantsagon/application/result_serialization.py`
- Modify: `pantsagon/domain/diagnostics.py`
- Test: `tests/application/test_result_serialization.py`

**Step 1: Write failing test**

```python
# tests/application/test_result_serialization.py
from pantsagon.domain.diagnostics import Diagnostic, Severity, FileLocation
from pantsagon.domain.result import Result
from pantsagon.application.result_serialization import serialize_result


def test_result_serializes_with_schema_version():
    result = Result(diagnostics=[
        Diagnostic(code="X", rule="r", severity=Severity.ERROR, message="m", location=FileLocation("x.py", 1, 2))
    ])
    data = serialize_result(result, command="init", args=["."])
    assert data["result_schema_version"] == 1
    assert data["exit_code"] == result.exit_code
    assert data["diagnostics"][0]["location"]["path"] == "x.py"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/application/test_result_serialization.py -q`
Expected: FAIL (module missing)

**Step 3: Write minimal implementation**

```python
# pantsagon/application/result_serialization.py
from datetime import datetime, timezone
from pantsagon.domain.result import Result
from pantsagon.domain.diagnostics import Diagnostic, FileLocation


def _serialize_location(loc):
    if loc is None:
        return None
    data = {"kind": loc.kind}
    if isinstance(loc, FileLocation):
        data.update({"path": loc.path, "line": loc.line, "col": loc.col})
    return data


def serialize_result(result: Result, command: str, args: list[str]) -> dict:
    return {
        "result_schema_version": 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "command": command,
        "args": args,
        "exit_code": result.exit_code,
        "diagnostics": [
            {
                "id": d.id,
                "code": d.code,
                "rule": d.rule,
                "severity": d.severity.value,
                "message": d.message,
                "location": _serialize_location(d.location),
                "hint": d.hint,
                "details": d.details,
                "is_execution": d.is_execution,
            }
            for d in result.diagnostics
        ],
        "artifacts": result.artifacts,
    }
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/application/test_result_serialization.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add pantsagon/application/result_serialization.py tests/application/test_result_serialization.py

git commit -m "feat: serialize results to json"
```

---

### Task 2: `add service` use-case (naming + idempotency)

**Files:**
- Modify: `pantsagon/application/add_service.py`
- Test: `tests/application/test_add_service_naming.py`

**Step 1: Write failing test**

```python
# tests/application/test_add_service_naming.py
from pantsagon.application.add_service import add_service


def test_add_service_rejects_bad_name(tmp_path):
    (tmp_path / ".pantsagon.toml").write_text("[tool]\nname='pantsagon'\nversion='0.1.0'\n")
    result = add_service(repo_path=tmp_path, name="BadName", lang="python")
    assert any(d.code == "SERVICE_NAME_INVALID" for d in result.diagnostics)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/application/test_add_service_naming.py -q`
Expected: FAIL

**Step 3: Write minimal implementation**

Implement kebab-case validation and reserved-name checks in `add_service`. Return diagnostics with code `SERVICE_NAME_INVALID`.

**Step 4: Run test to verify it passes**

Run: `pytest tests/application/test_add_service_naming.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add pantsagon/application/add_service.py tests/application/test_add_service_naming.py

git commit -m "feat: validate service naming"
```

---

### Task 3: `validate` use-case (lock drift + pack checks)

**Files:**
- Modify: `pantsagon/application/validate_repo.py`
- Test: `tests/application/test_validate_repo.py`

**Step 1: Write failing test**

```python
# tests/application/test_validate_repo.py
from pantsagon.application.validate_repo import validate_repo


def test_validate_repo_missing_lock(tmp_path):
    result = validate_repo(repo_path=tmp_path)
    assert any(d.code == "LOCK_MISSING" for d in result.diagnostics)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/application/test_validate_repo.py -q`
Expected: FAIL

**Step 3: Write minimal implementation**

Add checks for `.pantsagon.toml`, produce diagnostics with `LOCK_MISSING`, and stub pack validation.

**Step 4: Run test to verify it passes**

Run: `pytest tests/application/test_validate_repo.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add pantsagon/application/validate_repo.py tests/application/test_validate_repo.py

git commit -m "feat: add validate use-case scaffold"
```

---

### Task 4: CLI wiring for `add service` and `validate` + JSON flag

**Files:**
- Modify: `pantsagon/entrypoints/cli.py`
- Test: `tests/entrypoints/test_cli_validate.py`

**Step 1: Write failing test**

```python
# tests/entrypoints/test_cli_validate.py
from typer.testing import CliRunner
from pantsagon.entrypoints.cli import app


def test_cli_validate_exits_nonzero_when_lock_missing(tmp_path):
    runner = CliRunner()
    result = runner.invoke(app, ["validate", "--json"])
    assert result.exit_code != 0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/entrypoints/test_cli_validate.py -q`
Expected: FAIL

**Step 3: Write minimal implementation**

Wire `validate` to return JSON via `serialize_result` when `--json` is set.

**Step 4: Run test to verify it passes**

Run: `pytest tests/entrypoints/test_cli_validate.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add pantsagon/entrypoints/cli.py tests/entrypoints/test_cli_validate.py

git commit -m "feat: wire validate cli"
```

---

### Task 5: README update for CLI surface

**Files:**
- Modify: `README.md`

**Step 1: Write failing test**

```python
# tests/docs/test_readme_cli_m2.py
from pathlib import Path


def test_readme_mentions_validate_command():
    text = Path("README.md").read_text().lower()
    assert "pantsagon validate" in text
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/docs/test_readme_cli_m2.py -q`
Expected: FAIL

**Step 3: Write minimal implementation**

Update README CLI section with `add service` and `validate` usage and `--json` flag.

**Step 4: Run test to verify it passes**

Run: `pytest tests/docs/test_readme_cli_m2.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add README.md tests/docs/test_readme_cli_m2.py

git commit -m "docs: update readme for m2 cli"
```

---

Plan complete and saved to `docs/plans/2026-01-10-pantsagon-m2-cli-plan.md`.

Two execution options:

1. Subagent-Driven (this session) — I dispatch a fresh subagent per task, review between tasks, fast iteration
2. Parallel Session (separate) — Open new session with executing-plans and batch execution with checkpoints

Which approach?
