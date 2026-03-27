# Pants Lint Fix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make `pants lint ::` pass by addressing pyright unknown-type errors, the F841 unused variable, and the GitHub Actions workflow input error without behavioral changes.

**Architecture:** Treat lint as the failing test, reproduce it, then trace unknown-type sources to parsing boundaries. Apply minimal, localized typing/casting/guards at data ingress, fix the unused variable, and correct the workflow input. Re-run lint as the acceptance gate.

**Tech Stack:** Pants, Python, Pyright, Ruff, GitHub Actions.

### Task 1: Reproduce failures and capture evidence

**Files:**
- Modify: none
- Test: none

**Step 1: Run lint (failing test)**

Run: `pants lint ::`
Expected: FAIL with pyright errors, F841 in `init_repo.py`, and a GitHub Actions input error in `.github/workflows/ci.yml`.

**Step 2: Save the failing output**

Run: `pants lint :: 2> /tmp/pants-lint.log`
Expected: `/tmp/pants-lint.log` contains all failing file paths and line numbers.

**Step 3: Identify impacted files (gates)**

Run: `hammer tldr impact`
Expected: List of impacted files aligns with the lint output.

### Task 2: Root cause investigation for pyright unknown types

**Files:**
- Modify: none
- Test: none

**Step 1: Trace data sources for unknown dicts**

Inspect parsing/IO boundaries in:
- `scripts/generate_diagnostic_codes.py`
- `scripts/generate_schema_docs.py`
- `services/pantsagon/src/pantsagon/adapters/policy/pack_validator.py`
- `services/pantsagon/src/pantsagon/application/add_service.py`
- `services/pantsagon/src/pantsagon/application/init_repo.py`
- `services/pantsagon/src/pantsagon/application/pack_index.py`
- `services/pantsagon/src/pantsagon/application/rendering.py`
- `services/pantsagon/src/pantsagon/application/repo_lock.py`
- `services/pantsagon/src/pantsagon/application/validate_repo.py`
- `services/pantsagon/src/pantsagon/domain/result.py`
- `services/pantsagon/src/pantsagon/tools/validate_packs.py`
- `tools/forbidden_imports/src/forbidden_imports/checker.py`

Record which functions return `Any`/untyped dicts so typing can be applied at the entry point.

**Step 2: Compare with working patterns**

Search for nearby or similar code that uses `Mapping[str, Any]`, `TypedDict`, or `cast()` and note differences.

**Step 3: Hypothesis**

State the root cause: “Unknown types originate from untyped JSON/YAML parsing results; adding explicit types/casts at parse boundaries resolves pyright errors without behavior changes.”

### Task 3: Fix F841 unused variable in init_repo

**Files:**
- Modify: `services/pantsagon/src/pantsagon/application/init_repo.py`
- Test: none

**Step 1: Locate the unused variable**

Find `ordered_ids` and verify it is unused.

**Step 2: Apply minimal change**

Remove the unused variable assignment.

**Step 3: Re-run lint for confirmation**

Run: `pants lint :: --changed-since=HEAD`
Expected: F841 no longer reported.

### Task 4: Apply minimal typing fixes at boundaries

**Files:**
- Modify: files listed in Task 2
- Test: none

**Step 1: Add explicit types for parsed mappings**

Example patterns (apply at parse boundaries):

```python
from typing import Any, Mapping, cast

raw = cast(Mapping[str, Any], raw)
items = cast(list[Mapping[str, Any]], raw.get("items", []))
```

**Step 2: Use `Mapping` for read-only data**

Example:

```python
def render_bundled_packs(
    answers: Mapping[str, Any],
    catalog: PackCatalogPort,
    renderer: RendererPort,
    policy_engine: PolicyEnginePort,
) -> ...:
    ...
```

**Step 3: Normalize optional values**

Example:

```python
raw = raw or {}
selection = selection or {}
```

**Step 4: Keep changes localized**

No refactors; only typing/casting/guards to satisfy pyright.

### Task 5: Fix GitHub Actions input error

**Files:**
- Modify: `.github/workflows/ci.yml`
- Test: none

**Step 1: Move `python-version` to setup-python**

Example (adjust existing steps as needed):

```yaml
- uses: actions/checkout@v6
- uses: actions/setup-python@v5
  with:
    python-version: "3.12"
```

**Step 2: Validate workflow syntax**

Run: `pants lint ::` (or the repo’s workflow linter if present)
Expected: GitHub Actions input error resolved.

### Task 6: Rerun lint and verify

**Files:**
- Modify: none
- Test: none

**Step 1: Run lint**

Run: `pants lint ::`
Expected: PASS.

**Step 2: If failures remain**

Stop and document the remaining errors with file/line details before proposing changes.
