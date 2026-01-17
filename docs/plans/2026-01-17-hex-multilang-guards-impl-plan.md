# Hex Multi-Lang + Guards Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix multi-service init and ship language-aware hex repo defaults (guards, docs, tooling, and locks) across Python/TS/Rust/Go.

**Architecture:** Init renders global packs once and service-scoped packs per service (detected by `service_name`/`service_pkg` variables). Core pack owns global config/docs/tools; language packs own service skeletons; repo lock drops `[tool]` entirely. Language layouts follow Option A (per-language idioms): Python uses `services/<svc>/src/<pkg>/...`, TypeScript/Rust use `services/<svc>/src/<layer>/...`, Go uses `services/<svc>/internal/<layer>/...` plus `services/<svc>/cmd/<svc>/main.go`.

**Tech Stack:** Pants 2.30, Copier, Python, YAML/JSON, MkDocs (docs), shell guards.

---

### Task 1: Add failing test for multi-service init

**Files:**
- Modify: `services/pantsagon/tests/e2e/test_init_e2e.py`

**Step 1: Write the failing test**

```python
def test_init_generates_multiple_services(tmp_path, monkeypatch):
    monkeypatch.setenv("PANTSAGON_DETERMINISTIC", "1")
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "init",
            str(tmp_path),
            "--lang",
            "python",
            "--services",
            "monitors,governance",
            "--feature",
            "openapi",
            "--feature",
            "docker",
        ],
    )
    assert result.exit_code == 0
    assert (tmp_path / "services" / "monitors" / "src" / "monitors" / "domain").exists()
    assert (tmp_path / "services" / "governance" / "src" / "governance" / "domain").exists()
    assert (tmp_path / "shared" / "contracts" / "openapi" / "monitors.yaml").exists()
    assert (tmp_path / "shared" / "contracts" / "openapi" / "governance.yaml").exists()
```

**Step 2: Run test to verify it fails**

Run: `pytest services/pantsagon/tests/e2e/test_init_e2e.py::test_init_generates_multiple_services -v`
Expected: FAIL because only first service renders.

---

### Task 2: Implement service-scoped rendering in init

**Files:**
- Modify: `services/pantsagon/src/pantsagon/application/init_repo.py`
- Modify: `services/pantsagon/src/pantsagon/application/rendering.py`
- Modify: `services/pantsagon/src/pantsagon/application/add_service.py` (extract/shared copy helper)

**Step 1: Add shared helper for copying service-scoped files**

Create a helper in `services/pantsagon/src/pantsagon/application/rendering.py` (or new module) and use it in both init and add_service:

```python
SERVICE_PACK_VARS = {"service_name", "service_pkg"}

OPENAPI_PACK_ID = "pantsagon.openapi"

OPENAPI_SHARED_FILES = {
    Path("shared") / "contracts" / "openapi" / "README.md",
    Path("shared") / "contracts" / "openapi" / "BUILD",
}


def is_service_pack(manifest: dict[str, Any]) -> bool:
    vars_block = manifest.get("variables")
    if not isinstance(vars_block, list):
        return False
    names = {str(v.get("name")) for v in vars_block if isinstance(v, dict)}
    return bool(names & SERVICE_PACK_VARS)


def copy_service_scoped(
    temp_root: Path,
    stage_root: Path,
    repo_root: Path,
    service_name: str,
    allow_openapi: bool,
) -> None:
    spec_rel = Path("shared") / "contracts" / "openapi" / f"{service_name}.yaml"
    for path in temp_root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(temp_root)
        dest = stage_root / rel
        if len(rel.parts) >= 2 and rel.parts[0] == "services" and rel.parts[1] == service_name:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest)
            continue
        if allow_openapi and rel == spec_rel:
            if not dest.exists() and not (repo_root / rel).exists():
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, dest)
            continue
        if allow_openapi and rel in OPENAPI_SHARED_FILES:
            if not dest.exists() and not (repo_root / rel).exists():
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, dest)
```

**Step 2: Update init_repo to split global vs service packs**

In `init_repo.py`, when building `resolved_packs`, compute `service_scoped = is_service_pack(manifest)` and store it. Then:

- Build `answers_base` with `repo_name`, `service_packages`, `languages`, `features`.
- Render **global packs once** into the stage dir (direct render).
- For each service and each service pack: render into a temp dir and call `copy_service_scoped`.

Pseudo-structure (real code in file):

```python
answers_base = {
    "repo_name": repo_path.name,
    "service_packages": service_packages,
    "languages": languages,
    "features": features,
}

service_packs = [p for p in ordered_packs if p["service_scoped"]]
global_packs = [p for p in ordered_packs if not p["service_scoped"]]

# Render global packs once
render_bundled_packs(..., pack_ids=[p["id"] for p in global_packs], answers={**answers_base, "service_name": service_name, "service_pkg": service_pkg})

# Render service packs per service into temp + copy
for service in services:
    service_pkg = service_packages[service]
    answers = {**answers_base, "service_name": service, "service_pkg": service_pkg}
    for pack in service_packs:
        with tempfile.TemporaryDirectory() as tempdir:
            renderer.render(RenderRequest(..., staging_dir=Path(tempdir), answers=answers, ...))
            copy_service_scoped(Path(tempdir), stage, repo_path, service, allow_openapi=(pack["id"]==OPENAPI_PACK_ID))
```

**Step 3: Update add_service to use shared helper**

Replace its private `_copy_service_scoped` with the shared helper from `rendering.py`.

**Step 4: Run failing test**

Run: `pytest services/pantsagon/tests/e2e/test_init_e2e.py::test_init_generates_multiple_services -v`
Expected: PASS.

---

### Task 3: Remove `[tool]` from `.pantsagon.toml`

**Files:**
- Modify: `shared/contracts/schemas/repo-lock.schema.v1.json`
- Modify: `services/pantsagon/src/pantsagon/application/init_repo.py`
- Modify: `services/pantsagon/src/pantsagon/application/validate_repo.py`
- Modify: `services/pantsagon/src/pantsagon/application/repo_lock.py`
- Modify: `services/pantsagon/tests/application/test_repo_lock.py`
- Modify: `services/pantsagon/tests/application/test_add_service_rendering.py`

**Step 1: Update schema (remove required tool)**

Change `required` to `['resolved']` and remove the `tool` property entirely.

**Step 2: Update lock writing**

Remove `"tool": {...}` from `init_repo` lock object and `_fallback_dumps()` in `repo_lock.py`.

**Step 3: Update validation**

In `validate_repo.py`, remove the missing-tool diagnostic.

**Step 4: Update tests**

Update tests to omit tool section and assert new shape. For `test_repo_lock.py`, the lock dict should no longer include `tool`. Assertions should verify `resolved` contents only.

Run: `pytest services/pantsagon/tests/application/test_repo_lock.py -v`
Expected: PASS.

---

### Task 4: Expand core pack templates (pants.toml, gitignore, docs, mkdocs)

**Files:**
- Modify: `packs/core/templates/pants.toml.jinja`
- Modify: `packs/core/templates/.gitignore.jinja`
- Modify: `packs/core/templates/docs/README.md.jinja`
- Create: `packs/core/templates/docs/dev/hexagonal-dev-guide.md.jinja`
- Create: `packs/core/templates/mkdocs.yml.jinja`

**Step 1: pants.toml conditional sections**

Use Jinja to include language sections based on `languages` answer.

Example structure:

```toml
[GLOBAL]
pants_version = "2.30.0"

backend_packages = [
  "pants.backend.python",
  "pants.backend.docker",
  "pants.backend.experimental.visibility",
{% if "python" in languages %}
  "pants.backend.experimental.python.lint.ruff.check",
  "pants.backend.experimental.python.lint.ruff.format",
  "pants.backend.experimental.python.typecheck.pyright",
{% endif %}
{% if "typescript" in languages %}
  "pants.backend.experimental.javascript",
  "pants.backend.experimental.typescript",
{% endif %}
{% if "rust" in languages %}
  "pants.backend.experimental.rust",
{% endif %}
{% if "go" in languages %}
  "pants.backend.experimental.go",
{% endif %}
]

{% if "python" in languages %}
[python]
interpreter_constraints = ["CPython>=3.12,<3.15"]

[python-infer]
unowned_dependency_behavior = "error"
{% endif %}
```

**Step 2: richer .gitignore**

Add common Python/Node/Rust/Go artifacts, IDEs, `.env`, `.venv`, `.direnv`, `.pytest_cache`, `.ruff_cache`, `.mypy_cache`, `dist/`, `build/`, `target/`, `node_modules/`, `.vscode/`, `.idea/`.

**Step 3: docs guide**

Update docs README to link to new dev guide. Create `docs/dev/hexagonal-dev-guide.md` with structure:
- Repo layout & hex layers
- Dependency rules
- How to add a service
- Pants commands (lint/check/test)
- Guard scripts + forbidden imports

**Step 4: mkdocs.yml**

Minimal nav referencing `docs/README.md` and the dev guide.

---

### Task 5: Language-aware forbidden imports tool + CI wiring

**Files:**
- Modify: `tools/forbidden_imports/src/forbidden_imports/checker.py`
- Modify: `tools/forbidden_imports/forbidden_imports.yaml`
- Modify: `tools/forbidden_imports/BUILD`
- Create: `tools/forbidden_imports/src/forbidden_imports/cli.py`
- Modify: `packs/core/templates/tools/forbidden_imports/*` (mirror tool)
- Modify: `packs/core/templates/.github/workflows/ci.yml.jinja`

**Step 1: Update config format**

Use a `languages` top-level map:

```yaml
languages:
  python:
    extensions: [".py"]
    layers:
      domain:
        include:
          - "services/**/src/**/domain/**/*.py"
        deny: ["requests", "fastapi", "boto3"]
      ...
  typescript:
    extensions: [".ts", ".tsx"]
    layers:
      domain:
        include:
          - "services/**/src/**/domain/**/*.ts"
          - "services/**/src/**/domain/**/*.tsx"
        deny: ["axios", "express"]
  rust:
    extensions: [".rs"]
    layers: ...
  go:
    extensions: [".go"]
    layers:
      domain:
        include:
          - "services/**/internal/domain/**/*.go"
        deny: ["net/http", "database/sql"]
      application:
        include:
          - "services/**/internal/application/**/*.go"
        deny: ["net/http", "database/sql"]
      ports:
        include:
          - "services/**/internal/ports/**/*.go"
        deny: ["net/http", "database/sql"]
```

**Step 2: Checker logic**

- Find repo root by walking up to `.pantsagon.toml`.
- Read `selection.languages` from the lock (default `["python"]`).
- Only enforce languages present in config.
- For Python: use AST as today.
- For others: regex import extraction (patterns per language) and prefix‑match deny list.

Add CLI:

```python
def main() -> int:
    root = find_repo_root()
    config = load_config(root / "tools/forbidden_imports/forbidden_imports.yaml")
    languages = load_languages(root / ".pantsagon.toml")
    violations = scan_repo(root, config, languages)
    if violations:
        print("\n".join(violations))
        return 1
    return 0
```

**Step 3: Pants target**

Add `pex_binary(name="check", entry_point="forbidden_imports.cli:main")` and add to CI:

```yaml
- name: Forbidden imports
  run: pants run tools/forbidden_imports:check
```

**Step 4: Mirror into pack templates**

Copy tool files into `packs/core/templates/tools/forbidden_imports/`.

**Step 5: Tests**

Update existing tests or add new ones for language selection and non‑python scanning.

---

### Task 6: Guard scripts + git hooks auto-install

**Files:**
- Create: `packs/core/templates/tools/guards/*.sh` (adapted copies)
- Create: `packs/core/templates/.githooks/pre-commit.jinja`
- Create: `packs/core/templates/.githooks/pre-push.jinja`
- Modify: `services/pantsagon/src/pantsagon/application/init_repo.py`

**Step 1: Copy/adapt scripts**

Copy from `/Users/co/scroll/amami-v2/src/shell/` and adapt paths to Pantsagon repo layout. Ensure scripts are POSIX sh/bash, use repo root detection, and read `.pantsagon.toml` for language selection when needed.

**Step 2: Hooks install script**

Implement `tools/guards/install-git-hooks.sh` that sets `git config core.hooksPath .githooks` and ensures hook files are executable.

**Step 3: Init behavior**

In `init_repo` after commit:
- If `.git` missing: run `git init`.
- `chmod +x` on guard scripts + hooks.
- Execute `tools/guards/install-git-hooks.sh`.
- If any step fails, add a warning diagnostic but do not fail init.

---

### Task 7: AGENTS.md content

**Files:**
- Modify: `services/pantsagon/src/pantsagon/application/init_repo.py`

**Step 1: Replace stub**

When `--augmented-coding agents`, write a full `AGENTS.md` with hex rules, layering, and guard usage.

---

### Task 8: Add new language packs (typescript/rust/go)

**Files:**
- Create: `packs/typescript/pack.yaml`, `packs/typescript/copier.yml`, templates
- Create: `packs/rust/pack.yaml`, `packs/rust/copier.yml`, templates
- Create: `packs/go/pack.yaml`, `packs/go/copier.yml`, templates
- Modify: `packs/_index.json`

**Step 1: Pack manifests**

Each new pack requires `pantsagon.core` and declares `service_name`/`service_pkg` variables. Provide minimal hex skeletons:
- **TypeScript:** `services/{{ service_name }}/src/{domain,ports,application,adapters,entrypoints}/index.ts`
- **Rust:** `services/{{ service_name }}/Cargo.toml` with `src/lib.rs` and `src/{domain,ports,application,adapters,entrypoints}/mod.rs`
- **Go:** `services/{{ service_name }}/go.mod`, `internal/{domain,ports,application,adapters}/<layer>.go`, and `cmd/{{ service_name }}/main.go`

**Step 2: Update pack index**

Add language mappings:

```json
"languages": {
  "python": ["pantsagon.python"],
  "typescript": ["pantsagon.typescript"],
  "rust": ["pantsagon.rust"],
  "go": ["pantsagon.go"]
}
```

---

### Task 9: Verify & regressions

**Step 1: Run core tests**

Run: `pytest services/pantsagon/tests/e2e/test_init_e2e.py -v`

**Step 2: Run forbidden imports tests**

Run: `pytest tools/forbidden_imports/tests -v`

---

### Task 10: Update README/Docs if needed

If new commands/files were added (mkdocs, guard scripts), update `README.md` in this repo accordingly.

---

## Risks
- OpenAPI pack contains both service-scoped and global files; ensure BUILD/README are copied once.
- Hook install must not fail init in environments without git.
- Regex import detection for TS/Rust/Go must avoid false positives; keep rules conservative.
