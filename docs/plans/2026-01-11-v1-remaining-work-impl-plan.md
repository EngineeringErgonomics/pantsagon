# V1 Remaining Work Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Complete the remaining v1 gaps: transactional workspace commit, service‑scoped add‑service rendering + lock updates, JSON outputs, CI pack validation, stronger init E2E checks, and v1.0.0 version/docs updates.

**Architecture:** Extend the add‑service use‑case to render pinned packs into a temp dir, then selectively copy only service‑scoped artifacts into a staging workspace. Keep resolved packs unchanged and update lock answers/selection. Improve workspace commit rollback to restore overwritten files. Wire JSON output flags in CLI and update CI to run pack validation.

**Tech Stack:** Python 3.12, Typer, Copier, pytest, GitHub Actions

---

### Task 1: Make workspace commit rollback truly safe

**Files:**
- Modify: `services/pantsagon/src/pantsagon/adapters/workspace/filesystem.py`
- Modify: `services/pantsagon/tests/adapters/test_workspace_atomic.py`

**Step 1: Write the failing test**

```python
# in services/pantsagon/tests/adapters/test_workspace_atomic.py

def test_workspace_restores_overwritten_file(tmp_path, monkeypatch):
    ws = FilesystemWorkspace(tmp_path)
    target = tmp_path / "file.txt"
    target.write_text("old")
    stage = ws.begin_transaction()
    (stage / "file.txt").write_text("new")
    # force failure after overwrite attempt
    monkeypatch.setattr(ws, "_copy_file", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")))
    try:
        ws.commit(stage)
    except Exception:
        pass
    assert target.read_text() == "old"
```

**Step 2: Run test to verify it fails**

Run: `pytest services/pantsagon/tests/adapters/test_workspace_atomic.py::test_workspace_restores_overwritten_file -v`
Expected: FAIL (file content not restored)

**Step 3: Write minimal implementation**

```python
# in FilesystemWorkspace.commit
# - back up existing files before overwriting
# - use temp file + os.replace for atomic file swaps
# - restore backups on failure
```

**Step 4: Run test to verify it passes**

Run: `pytest services/pantsagon/tests/adapters/test_workspace_atomic.py::test_workspace_restores_overwritten_file -v`
Expected: PASS

**Step 5: Commit**

```bash
git add services/pantsagon/src/pantsagon/adapters/workspace/filesystem.py \
  services/pantsagon/tests/adapters/test_workspace_atomic.py
git commit -m "feat: make workspace commit rollback safe"
```

---

### Task 2: Implement service‑scoped add‑service rendering + lock updates

**Files:**
- Modify: `services/pantsagon/src/pantsagon/application/add_service.py`
- Modify: `services/pantsagon/src/pantsagon/entrypoints/cli.py`
- Modify: `services/pantsagon/src/pantsagon/diagnostics/codes.yaml`
- Add: `services/pantsagon/tests/application/test_add_service_rendering.py`
- Add: `services/pantsagon/tests/entrypoints/test_cli_add_service.py`

**Step 1: Write the failing tests**

```python
# services/pantsagon/tests/application/test_add_service_rendering.py

def test_add_service_renders_scoped_files(tmp_path, monkeypatch):
    # create minimal lock with bundled packs and openapi
    # call add_service with real adapters (bundled packs)
    # assert:
    # - services/<svc>/... exists
    # - shared/contracts/openapi/<svc>.yaml exists
    # - shared/contracts/openapi/README.md only copied if missing
    # - no other top-level files created
```

```python
# services/pantsagon/tests/entrypoints/test_cli_add_service.py

def test_cli_add_service_renders_scoped_files(tmp_path, monkeypatch):
    # init repo via CLI, then add-service
    # assert service dir + docker/openapi artifacts exist
```

**Step 2: Run tests to verify they fail**

Run: `pytest services/pantsagon/tests/application/test_add_service_rendering.py -v`
Expected: FAIL (add_service doesn’t render)

**Step 3: Implement add‑service rendering**

```python
# In add_service:
# - read lock + validate
# - ensure service not already in lock or on disk
# - build render answers (repo_name, service_name, service_pkg, service_packages)
# - for each resolved pack, render into temp dir
# - copy only allowed paths into staging dir
# - update lock selection.services + resolved.answers
# - keep resolved.packs unchanged
```

**Step 4: Update diagnostics codes**

```yaml
# services/pantsagon/src/pantsagon/diagnostics/codes.yaml
- code: SERVICE_EXISTS
  severity: error
  rule: service.name
  message: Service already exists.
  hint: Choose a new service name or remove the existing service.
```

**Step 5: Run tests to verify they pass**

Run: `pytest services/pantsagon/tests/application/test_add_service_rendering.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add services/pantsagon/src/pantsagon/application/add_service.py \
  services/pantsagon/src/pantsagon/entrypoints/cli.py \
  services/pantsagon/src/pantsagon/diagnostics/codes.yaml \
  services/pantsagon/tests/application/test_add_service_rendering.py \
  services/pantsagon/tests/entrypoints/test_cli_add_service.py
git commit -m "feat: add scoped add-service rendering"
```

---

### Task 3: Add JSON output for init/add‑service + align CLI naming in docs

**Files:**
- Modify: `services/pantsagon/src/pantsagon/entrypoints/cli.py`
- Modify: `README.md`
- Modify: `services/pantsagon/tests/entrypoints/test_cli_init.py`
- Add: `services/pantsagon/tests/entrypoints/test_cli_add_service_json.py`

**Step 1: Write failing tests**

```python
# test init --json prints Result payload with exit_code
# test add-service --json prints Result payload
```

**Step 2: Run tests to verify they fail**

Run: `pytest services/pantsagon/tests/entrypoints/test_cli_add_service_json.py -v`
Expected: FAIL (no --json flag)

**Step 3: Implement --json flags and serialization**

```python
# add --json to init/add_service
# serialize_result(result, command=..., args=...)
# echo JSON before exiting
```

**Step 4: Update README CLI usage to use add-service + --json**

**Step 5: Run tests to verify they pass**

Run: `pytest services/pantsagon/tests/entrypoints/test_cli_add_service_json.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add services/pantsagon/src/pantsagon/entrypoints/cli.py \
  README.md \
  services/pantsagon/tests/entrypoints/test_cli_init.py \
  services/pantsagon/tests/entrypoints/test_cli_add_service_json.py
git commit -m "feat: add json output for init/add-service"
```

---

### Task 4: Strengthen init E2E validation

**Files:**
- Modify: `services/pantsagon/tests/e2e/test_init_e2e.py`

**Step 1: Write failing assertions**

```python
# assert service skeleton, openapi spec, dockerfile exist
```

**Step 2: Run test to verify it fails**

Run: `pytest services/pantsagon/tests/e2e/test_init_e2e.py::test_init_generates_core_files -v`
Expected: FAIL (missing new asserts)

**Step 3: Adjust code if needed**

```python
# No code changes expected; ensure init already renders packs
```

**Step 4: Run test to verify it passes**

Run: `pytest services/pantsagon/tests/e2e/test_init_e2e.py::test_init_generates_core_files -v`
Expected: PASS

**Step 5: Commit**

```bash
git add services/pantsagon/tests/e2e/test_init_e2e.py
git commit -m "test: strengthen init e2e skeleton checks"
```

---

### Task 5: Add pack validation step to CI

**Files:**
- Modify: `.github/workflows/ci.yml`

**Step 1: Add CI step after tests**

```yaml
- name: Install pack validation deps
  run: python -m pip install -r 3rdparty/python/requirements.txt
- name: Validate bundled packs
  run: |
    PANTSAGON_DETERMINISTIC=1 PYTHONPATH=services/pantsagon/src \
      python -m pantsagon.tools.validate_packs --bundled --quiet
```

**Step 2: Verify YAML locally**

Run: `python -m pantsagon.tools.validate_packs --bundled --quiet`
Expected: PASS

**Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add bundled pack validation step"
```

---

### Task 6: Bump to v1.0.0 + docs updates

**Files:**
- Modify: `pyproject.toml`
- Modify: `services/pantsagon/src/pantsagon/__init__.py`
- Modify: `services/pantsagon/src/pantsagon/application/init_repo.py`
- Modify: `README.md`
- Modify: `services/pantsagon/tests/application/test_repo_lock.py`
- Modify: `services/pantsagon/tests/application/test_add_service.py`
- Modify: `services/pantsagon/tests/application/test_add_service_naming.py`

**Step 1: Update version constants**

```python
# set version = "1.0.0" in pyproject + __init__ + init_repo lock writer
```

**Step 2: Update README status + examples**

```markdown
# update status to v1.0
# update "What you get" header
# update example lock version
# remove roadmap item for add-service rendering
```

**Step 3: Update tests for new version**

**Step 4: Run tests**

Run: `pytest services/pantsagon/tests/application/test_repo_lock.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add pyproject.toml \
  services/pantsagon/src/pantsagon/__init__.py \
  services/pantsagon/src/pantsagon/application/init_repo.py \
  README.md \
  services/pantsagon/tests/application/test_repo_lock.py \
  services/pantsagon/tests/application/test_add_service.py \
  services/pantsagon/tests/application/test_add_service_naming.py
git commit -m "release: bump pantsagon to v1.0.0"
```

