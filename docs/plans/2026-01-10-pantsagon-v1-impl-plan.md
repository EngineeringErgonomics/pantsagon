# Pantsagon v1.0 Implementation Plan (Phase 1)

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Deliver M0 + M1 foundation: correct licensing/docs and real pack rendering in `init` with atomic staging.

**Architecture:** Preserve hexagonal core. Add rendering workflow in application layer using existing ports/adapters. Update README to truthfully represent state.

**Tech Stack:** Python 3.12, Typer, Copier, PyYAML, jsonschema, pytest.

---

### Task 1: Fix README license + status (M0)

**Files:**
- Modify: `README.md`
- Verify: `LICENSE`

**Step 1: Write failing test (doc assertion)**

```python
# tests/docs/test_readme_license.py
from pathlib import Path


def test_readme_mentions_apache_license():
    text = Path("README.md").read_text().lower()
    assert "apache license 2.0" in text
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/docs/test_readme_license.py -q`
Expected: FAIL (license text missing)

**Step 3: Write minimal implementation**

Update `README.md`:
- Add a “License” section that explicitly says **Apache License 2.0**.
- Ensure status section reflects current capabilities (no misleading claims).

**Step 4: Run test to verify it passes**

Run: `pytest tests/docs/test_readme_license.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add README.md tests/docs/test_readme_license.py

git commit -m "docs: fix license statement in readme"
```

---

### Task 2: `init` renders packs into staging (M1)

**Files:**
- Modify: `pantsagon/application/init_repo.py`
- Modify: `pantsagon/adapters/workspace/filesystem.py`
- Create: `pantsagon/application/rendering.py`
- Test: `tests/application/test_init_repo_renders.py`
- Test: `tests/adapters/test_workspace_atomic.py`

**Step 1: Write failing tests**

```python
# tests/application/test_init_repo_renders.py
from pathlib import Path
from pantsagon.application.init_repo import init_repo


def test_init_repo_renders_core_pack(tmp_path):
    result = init_repo(repo_path=tmp_path, languages=["python"], services=["monitors"], features=["openapi", "docker"], renderer="copier")
    assert (tmp_path / "pants.toml").exists()
    assert (tmp_path / ".pantsagon.toml").exists()
```

```python
# tests/adapters/test_workspace_atomic.py
from pathlib import Path
from pantsagon.adapters.workspace.filesystem import FilesystemWorkspace


def test_workspace_rollback_on_error(tmp_path, monkeypatch):
    ws = FilesystemWorkspace(tmp_path)
    stage = ws.begin_transaction()
    (stage / "file.txt").write_text("data")
    monkeypatch.setattr(ws, "_copy_file", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")))
    try:
        ws.commit(stage)
    except Exception:
        pass
    assert not (tmp_path / "file.txt").exists()
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/application/test_init_repo_renders.py tests/adapters/test_workspace_atomic.py -q`
Expected: FAIL

**Step 3: Write minimal implementation**

- Add `application/rendering.py` to:
  - resolve pack paths (bundled only in v1)
  - validate packs with `validate_pack`
  - call Copier renderer per pack into staging
- Update `FilesystemWorkspace`:
  - add `_copy_file` helper for test injection
  - ensure commit cleans stage and does not partially apply on error
- Update `init_repo` to:
  - use staging dir
  - render packs via new helper
  - write `.pantsagon.toml` into staging
  - commit atomically
  - remove placeholder `pants.toml` write

**Step 4: Run tests to verify they pass**

Run: `pytest tests/application/test_init_repo_renders.py tests/adapters/test_workspace_atomic.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add pantsagon/application/init_repo.py pantsagon/application/rendering.py pantsagon/adapters/workspace/filesystem.py tests/application/test_init_repo_renders.py tests/adapters/test_workspace_atomic.py

git commit -m "feat: render packs during init"
```

---

### Task 3: README update for rendered init (M1)

**Files:**
- Modify: `README.md`

**Step 1: Write failing test**

```python
# tests/docs/test_readme_init_rendering.py
from pathlib import Path


def test_readme_mentions_rendered_init():
    text = Path("README.md").read_text().lower()
    assert "renders" in text and "init" in text
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/docs/test_readme_init_rendering.py -q`
Expected: FAIL

**Step 3: Write minimal implementation**

Update README “Quick start / Status” to state that `init` renders packs into a real repo skeleton.

**Step 4: Run test to verify it passes**

Run: `pytest tests/docs/test_readme_init_rendering.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add README.md tests/docs/test_readme_init_rendering.py

git commit -m "docs: update readme for rendered init"
```

---

Plan complete and saved to `docs/plans/2026-01-10-pantsagon-v1-impl-plan.md`.

Two execution options:

1. Subagent-Driven (this session) — I dispatch a fresh subagent per task, review between tasks.
2. Parallel Session (separate) — Open a new session with executing-plans and batch execution.

Which approach would you like?
