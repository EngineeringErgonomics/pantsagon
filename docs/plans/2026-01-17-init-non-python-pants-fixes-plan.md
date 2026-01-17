# Init Non-Python Pants Fixes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make non-Python init repos include Python tooling/backends, fix pants.toml whitespace, use Pants GitHub Action in CI, and prevent executable BUILD files.

**Architecture:** Adjust core templates (pants.toml + CI) and init post-processing to align with desired output; update tests first to lock behavior.

**Tech Stack:** Python 3.12, Pants templates (Jinja), pytest.

### Task 1: Update non-Python init test expectations

**Files:**
- Modify: `services/pantsagon/tests/e2e/test_init_e2e.py`

**Step 1: Write the failing test**

Update `test_init_non_python_repo_pants_toml_is_clean` to expect python/ruff/pyright backends and to expect `.ruff.toml`, `pyrightconfig.json`, and `3rdparty/python` to exist for TS/Rust/Go. Also assert `[python]`, `[python-infer]`, `[ruff]`, `[pyright]` sections are present in `pants.toml`. Strengthen formatting assertions: no leading blank lines and no blank lines inside `backend_packages`. Add a repo-wide invariant: no file named `BUILD` is executable.

```python
for backend in {
    "pants.backend.python",
    "pants.backend.python.lint.ruff",
    "pants.backend.python.typecheck.pyright",
}:
    assert backend in backends

assert "[python]" in text
assert "[python-infer]" in text
assert "[ruff]" in text
assert "[pyright]" in text

assert (tmp_path / ".ruff.toml").exists()
assert (tmp_path / "pyrightconfig.json").exists()
assert (tmp_path / "3rdparty" / "python").exists()

for build_file in tmp_path.rglob("BUILD"):
    assert build_file.stat().st_mode & stat.S_IXUSR == 0
```

**Step 2: Run test to verify it fails**

Run: `pytest services/pantsagon/tests/e2e/test_init_e2e.py::test_init_non_python_repo_pants_toml_is_clean -q`
Expected: FAIL because current template omits python sections/backends for non-Python languages.

**Step 3: Commit**

```bash
git add services/pantsagon/tests/e2e/test_init_e2e.py
git commit -m "test: expect python tooling in non-python init"
```

### Task 2: Fix pants.toml template formatting and backends

**Files:**
- Modify: `packs/core/templates/pants.toml.jinja`

**Step 1: Write the failing test**

Test already exists (Task 1) and should still be failing.

**Step 2: Write minimal implementation**

Rewrite template to build `backend_packages` and `root_patterns` lists with Jinja variables and render via loops. Always include python/ruff/pyright backends and python sections. Use whitespace control (`{%-` / `-%}`) to prevent blank lines at file start and between list items.

```jinja
{%- set langs = languages | default([]) -%}
{%- set feats = features | default([]) -%}
{%- set backend_packages = [
  "pants.backend.shell",
  "pants.backend.experimental.visibility",
  "pants.backend.python",
  "pants.backend.python.lint.ruff",
  "pants.backend.python.typecheck.pyright",
] -%}
{%- if "typescript" in langs -%}
{%- set backend_packages = backend_packages + [
  "pants.backend.experimental.javascript",
  "pants.backend.experimental.typescript",
] -%}
{%- endif -%}
{%- if "rust" in langs -%}
{%- set backend_packages = backend_packages + ["pants.backend.experimental.rust"] -%}
{%- endif -%}
{%- if "go" in langs -%}
{%- set backend_packages = backend_packages + ["pants.backend.experimental.go"] -%}
{%- endif -%}
{%- if "docker" in feats -%}
{%- set backend_packages = backend_packages + ["pants.backend.docker"] -%}
{%- endif -%}
```

Then render:

```jinja
backend_packages = [
{%- for backend in backend_packages %}
  "{{ backend }}",
{%- endfor %}
]
```

Add `[python]`, `[python-infer]`, `[ruff]`, `[pyright]` sections unconditionally.

**Step 3: Run test to verify it passes**

Run: `pytest services/pantsagon/tests/e2e/test_init_e2e.py::test_init_non_python_repo_pants_toml_is_clean -q`
Expected: PASS

**Step 4: Commit**

```bash
git add packs/core/templates/pants.toml.jinja
git commit -m "fix: clean pants.toml template and always include python tooling"
```

### Task 3: Update CI to use Pants GitHub Action

**Files:**
- Modify: `packs/core/templates/.github/workflows/ci.yml.jinja`

**Step 1: Write the failing test**

Test already exists: `services/pantsagon/tests/packs/test_bundled_pack_smoke.py::test_core_pack_renders_minimum_skeleton`.

**Step 2: Write minimal implementation**

Replace the pip install step with Pants action:

```yaml
      - uses: pantsbuild/actions/init-pants@v10
        with:
          pants-version: "2.30.0"
```

Remove the pip install step.

**Step 3: Run test to verify it passes**

Run: `pytest services/pantsagon/tests/packs/test_bundled_pack_smoke.py::test_core_pack_renders_minimum_skeleton -q`
Expected: PASS

**Step 4: Commit**

```bash
git add packs/core/templates/.github/workflows/ci.yml.jinja
git commit -m "fix: use pants init action in CI"
```

### Task 4: Prevent executable BUILD files

**Files:**
- Modify: `services/pantsagon/src/pantsagon/application/init_repo.py`

**Step 1: Write the failing test**

Already covered in `test_init_non_python_repo_pants_toml_is_clean` via `hex_enforce/BUILD` executable bit assertion.

**Step 2: Write minimal implementation**

Only chmod files that start with a shebang:

```python
def _has_shebang(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            return handle.read(2) == b"#!"
    except OSError:
        return False

# In _make_executable_tree:
if path.is_file():
    if _has_shebang(path):
        path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return
...
if _has_shebang(file):
    file.chmod(...)
```

**Step 3: Run test to verify it passes**

Run: `pytest services/pantsagon/tests/e2e/test_init_e2e.py::test_init_non_python_repo_pants_toml_is_clean -q`
Expected: PASS

**Step 4: Commit**

```bash
git add services/pantsagon/src/pantsagon/application/init_repo.py
git commit -m "fix: only chmod scripts with shebang"
```

### Task 5: Final verification

**Files:**
- Tests: `services/pantsagon/tests/e2e/test_init_e2e.py`, `services/pantsagon/tests/packs/test_bundled_pack_smoke.py`

**Step 1: Run focused tests**

Run: `pytest services/pantsagon/tests/e2e/test_init_e2e.py::test_init_non_python_repo_pants_toml_is_clean -q`
Expected: PASS

Run: `pytest services/pantsagon/tests/packs/test_bundled_pack_smoke.py::test_core_pack_renders_minimum_skeleton -q`
Expected: PASS

**Step 2: Commit**

```bash
git add services/pantsagon/tests/e2e/test_init_e2e.py services/pantsagon/tests/packs/test_bundled_pack_smoke.py
# Only if test changes beyond Task 1
```
