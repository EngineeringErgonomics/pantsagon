# M6 CI + Release Readiness Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a deterministic pack-validation command, wire CI to run pytest + pack validation, and publish a v1.0.0 release checklist with a final README pass.

**Architecture:** Implement `pantsagon.tools.validate_packs` as a standalone `python -m` module that uses existing pack validation + Copier rendering, aggregates diagnostics into Result-shaped JSON, and supports render-control flags. CI runs pytest and the new pack-validation command in deterministic mode. Release readiness is captured in a doc and reflected in README.

**Tech Stack:** Python 3.12, argparse, Copier renderer, GitHub Actions, mkdocs.

### Task 1: Pack validation tool module

**Files:**
- Create: `services/pantsagon/src/pantsagon/tools/__init__.py`
- Create: `services/pantsagon/src/pantsagon/tools/validate_packs.py`
- Modify: `pantsagon/diagnostics/codes.yaml`
- Modify: `docs/reference/diagnostic-codes.md`

**Step 1: Implement the module (TDD skipped per instruction)**

Create `services/pantsagon/src/pantsagon/tools/validate_packs.py` with:

```python
from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any

from pantsagon.adapters.errors import RendererExecutionError
from pantsagon.adapters.policy import pack_validator
from pantsagon.adapters.policy.pack_validator import PackPolicyEngine
from pantsagon.adapters.renderer.copier_renderer import CopierRenderer
from pantsagon.application.pack_validation import validate_pack
from pantsagon.domain.determinism import is_deterministic
from pantsagon.domain.diagnostics import Diagnostic, FileLocation, Severity
from pantsagon.domain.pack import PackRef
from pantsagon.domain.result import Result
from pantsagon.ports.renderer import RenderRequest

DEFAULTS_BY_NAME = {
    "service_name": "example-service",
    "service_name_kebab": "example-service",
    "repo_name": "example-repo",
    "service_pkg": "example_service",
    "service_pkg_snake": "example_service",
}


def _repo_root() -> Path:
    for candidate in [Path.cwd(), *Path.cwd().parents]:
        if (candidate / "pyproject.toml").exists():
            return candidate
    return Path.cwd()


def _relative_path(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _serialize_location(location: object | None) -> dict[str, Any] | None:
    if location is None:
        return None
    if isinstance(location, FileLocation):
        return {
            "kind": "file",
            "path": location.path,
            "line": location.line,
            "col": location.col,
        }
    return asdict(location) if hasattr(location, "__dict__") else {"kind": "unknown"}


def _serialize_diagnostic(diagnostic: Diagnostic) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": diagnostic.id,
        "code": diagnostic.code,
        "rule": diagnostic.rule,
        "severity": diagnostic.severity.value,
        "message": diagnostic.message,
    }
    if diagnostic.location is not None:
        payload["location"] = _serialize_location(diagnostic.location)
    if diagnostic.hint is not None:
        payload["hint"] = diagnostic.hint
    if diagnostic.details is not None:
        payload["details"] = diagnostic.details
    return payload


def _placeholder_for(var: dict[str, Any]) -> Any:
    name = str(var.get("name", ""))
    if name in DEFAULTS_BY_NAME:
        return DEFAULTS_BY_NAME[name]
    if "default" in var:
        return var.get("default")
    vtype = var.get("type")
    if vtype == "int":
        return 1
    if vtype == "bool":
        return False
    if vtype == "enum":
        enum_values = var.get("enum")
        if isinstance(enum_values, list) and enum_values:
            return enum_values[0]
    return "example"


def _build_answers(manifest: dict[str, Any]) -> dict[str, Any]:
    answers: dict[str, Any] = {}
    raw_variables = manifest.get("variables", [])
    if isinstance(raw_variables, list):
        for entry in raw_variables:
            if not isinstance(entry, dict):
                continue
            name = entry.get("name")
            if name is None:
                continue
            answers[str(name)] = _placeholder_for(entry)
    return answers


def _pack_dirs(packs_root: Path) -> list[Path]:
    if not packs_root.exists():
        return []
    dirs = [path for path in packs_root.iterdir() if path.is_dir()]
    return sorted(dirs, key=lambda p: p.name)


def _missing_file_diagnostic(path: Path, root: Path, filename: str) -> Diagnostic:
    return Diagnostic(
        code="PACK_FILE_MISSING",
        rule="pack.files",
        severity=Severity.ERROR,
        message=f"Missing required pack file: {filename}",
        location=FileLocation(_relative_path(path / filename, root)),
    )


def _render_failed_diagnostic(pack_dir: Path, root: Path, pack_id: str, error: Exception) -> Diagnostic:
    return Diagnostic(
        code="PACK_RENDER_FAILED",
        rule="pack.render",
        severity=Severity.ERROR,
        message=str(error),
        location=FileLocation(_relative_path(pack_dir, root)),
        details={"pack": pack_id},
        is_execution=True,
    )


def validate_bundled_packs(
    packs_root: Path,
    *,
    render_on_validation_error: bool,
    render_enabled: bool,
) -> Result[dict[str, Any]]:
    root = _repo_root()
    pack_validator.SCHEMA_PATH = pack_validator._schema_path(root)
    engine = PackPolicyEngine()
    renderer = CopierRenderer()
    diagnostics: list[Diagnostic] = []
    artifacts: list[dict[str, Any]] = []

    for pack_dir in _pack_dirs(packs_root):
        pack_diags: list[Diagnostic] = []
        missing = []
        if not (pack_dir / "pack.yaml").exists():
            missing.append("pack.yaml")
        if not (pack_dir / "copier.yml").exists():
            missing.append("copier.yml")
        for filename in missing:
            diag = _missing_file_diagnostic(pack_dir, root, filename)
            pack_diags.append(diag)
            diagnostics.append(diag)

        manifest: dict[str, Any] = {}
        pack_id = pack_dir.name
        pack_version = "unknown"
        if not missing:
            result = validate_pack(pack_dir, engine)
            manifest = result.value or {}
            pack_diags.extend(result.diagnostics)
            diagnostics.extend(result.diagnostics)
            pack_id = str(manifest.get("id", pack_dir.name))
            pack_version = str(manifest.get("version", "unknown"))

        has_validation_errors = any(d.severity == Severity.ERROR for d in pack_diags if not d.is_execution)
        render_skipped = False
        status = "passed"

        if not render_enabled:
            render_skipped = True
        elif has_validation_errors and not render_on_validation_error:
            render_skipped = True

        if has_validation_errors:
            status = "failed"

        if not render_skipped and not missing:
            answers = _build_answers(manifest)
            request = RenderRequest(
                pack=PackRef(id=pack_id, version=pack_version, source="bundled"),
                pack_path=pack_dir,
                staging_dir=Path(tempfile.mkdtemp()),
                answers=answers,
                allow_hooks=False,
            )
            try:
                renderer.render(request)
            except RendererExecutionError as exc:
                diag = _render_failed_diagnostic(pack_dir, root, pack_id, exc)
                diagnostics.append(diag)
                pack_diags.append(diag)
                status = "failed"

        artifacts.append(
            {
                "pack_id": pack_id,
                "pack_version": pack_version,
                "source": "bundled",
                "status": status,
                "render_skipped": render_skipped,
                "diagnostics": [_serialize_diagnostic(d) for d in pack_diags],
            }
        )

    result = Result(value=None, diagnostics=diagnostics, artifacts=artifacts)
    return result


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate bundled Pantsagon packs")
    parser.add_argument("--bundled", action="store_true", help="Validate bundled packs under ./packs")
    parser.add_argument("--json", action="store_true", help="Emit Result JSON")
    parser.add_argument("--render-on-validation-error", action="store_true")
    parser.add_argument("--no-render", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not args.bundled:
        parser.error("--bundled is required in v1")

    if args.no_render and args.render_on_validation_error:
        args.render_on_validation_error = False

    result = validate_bundled_packs(
        packs_root=_repo_root() / "packs",
        render_on_validation_error=args.render_on_validation_error,
        render_enabled=not args.no_render,
    )

    if args.json:
        payload = {
            "result_schema_version": 1,
            "exit_code": result.exit_code,
            "diagnostics": [_serialize_diagnostic(d) for d in result.diagnostics],
            "artifacts": result.artifacts,
        }
        print(json.dumps(payload, sort_keys=is_deterministic()))
    else:
        failed = [a for a in result.artifacts if a.get("status") != "passed"]
        print(f"Validated {len(result.artifacts)} bundled packs")
        for artifact in result.artifacts:
            print(f"- {artifact['pack_id']}: {artifact['status']}")
        if failed:
            print(f"Failures: {len(failed)}")

    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
```

Adjust minor details during implementation:
- Import `tempfile` for staging dirs.
- Ensure `_serialize_location` handles `FileLocation` correctly.
- Use `_repo_root()` for relative paths and schema path.
- Keep `pack` validation per pack (continue even after failure).

**Step 2: Add diagnostic codes**

Update `pantsagon/diagnostics/codes.yaml` with new codes:

```yaml
  - code: PACK_FILE_MISSING
    severity: error
    rule: pack.files
    message: Pack is missing a required file.
    hint: Ensure pack.yaml and copier.yml exist in the pack directory.

  - code: PACK_RENDER_FAILED
    severity: error
    rule: pack.render
    message: Pack render failed.
    hint: Check Copier templates and inputs.
```

Run doc generation and verify output:

```bash
python scripts/generate_diagnostic_codes.py
```

Expected: `docs/reference/diagnostic-codes.md` updated with the two new codes.

**Step 3: Run manual validation for the new command**

```bash
PANTSAGON_DETERMINISTIC=1 PYTHONPATH=services/pantsagon/src python -m pantsagon.tools.validate_packs --bundled
```

Expected: human summary, exit code 0 if packs validate.

**Step 4: Commit**

```bash
git add services/pantsagon/src/pantsagon/tools/validate_packs.py \
  services/pantsagon/src/pantsagon/tools/__init__.py \
  pantsagon/diagnostics/codes.yaml \
  docs/reference/diagnostic-codes.md
git commit -m "feat: add bundled pack validation tool"
```

### Task 2: CI workflow for pytest + pack validation

**Files:**
- Create: `.github/workflows/ci.yml`

**Step 1: Create workflow (TDD skipped per instruction)**

```yaml
name: CI

on:
  push:
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    env:
      PANTSAGON_DETERMINISTIC: "1"
      PYTHONPATH: services/pantsagon/src
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install deps
        run: |
          python -m pip install --upgrade pip
          python -m pip install -e ".[dev]"
      - name: Pytest
        run: pytest -q
      - name: Pack validation
        run: python -m pantsagon.tools.validate_packs --bundled
```

**Step 2: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: run pytest and pack validation"
```

### Task 3: Release checklist for v1.0.0

**Files:**
- Create: `docs/contributing/release-checklist-v1.0.0.md`
- Modify: `mkdocs.yml`

**Step 1: Add the checklist doc (TDD skipped per instruction)**

```markdown
# v1.0.0 Release Checklist

This checklist defines the minimum release readiness steps for Pantsagon v1.0.0.

## Pre-release verification

- [ ] CI green: pytest + pack validation (deterministic mode)
- [ ] `python -m pantsagon.tools.validate_packs --bundled` passes locally
- [ ] Docs generators ran with clean git diff
- [ ] README reflects current CLI behavior and status

## Packaging and versioning

- [ ] Update `pyproject.toml` version to `1.0.0`
- [ ] Tag the release `v1.0.0`
- [ ] Publish release notes

## Documentation

- [ ] Update CLI docs if flags changed
- [ ] Update schema docs if schemas changed
- [ ] Update diagnostic codes if codes changed
- [ ] Update pack docs if packs changed
- [ ] Publish docs for `v1.0.0` and update `latest`
```

Add to mkdocs nav under Contributing:

```yaml
  - Contributing:
      - Docs: contributing/docs.md
      - Release checklist v1.0.0: contributing/release-checklist-v1.0.0.md
```

**Step 2: Commit**

```bash
git add docs/contributing/release-checklist-v1.0.0.md mkdocs.yml
git commit -m "docs: add v1.0.0 release checklist"
```

### Task 4: README final pass

**Files:**
- Modify: `README.md`

**Step 1: Update README (TDD skipped per instruction)**

Recommended edits:
- Add `python -m pantsagon.tools.validate_packs --bundled` to Development or Packs sections.
- Note deterministic mode used in CI: `PANTSAGON_DETERMINISTIC=1`.
- Clarify pack validation guarantees (schema + copier cross-check + smoke render).

Example snippet:

```markdown
## Development

Run tests:

```bash
pytest -q
```

Pack validation:

```bash
PANTSAGON_DETERMINISTIC=1 PYTHONPATH=services/pantsagon/src \
  python -m pantsagon.tools.validate_packs --bundled
```
```

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: update README for pack validation"
```

### Task 5: Update M6 checklist

**Files:**
- Modify: `docs/plans/2026-01-10-pantsagon-v1-checklist.md`

**Step 1: Check off M6 items (TDD skipped per instruction)**

Mark the four M6 items as complete once Tasks 1–4 are done.

**Step 2: Commit**

```bash
git add docs/plans/2026-01-10-pantsagon-v1-checklist.md
git commit -m "docs: mark M6 checklist complete"
```
