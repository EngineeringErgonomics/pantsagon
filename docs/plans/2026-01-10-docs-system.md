# Docs System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement a docs-as-code system with MkDocs + Material + mike, versioned publishing, reference-doc generators, and CI enforcement.

**Architecture:** Documentation lives under `docs/` with a structured nav. Generated reference docs are produced by scripts from canonical sources (`schemas/` and `pantsagon/diagnostics/codes.yaml`) and CI fails if outputs drift. GitHub Actions publishes versioned docs to `gh-pages` using mike.

**Tech Stack:** MkDocs + Material, mike, GitHub Actions, Python 3.12, PyYAML, JSON Schema.

---

### Task 1: Add MkDocs config + docs dependency pins + Python pin

**Files:**
- Create: `mkdocs.yml`
- Create: `docs/requirements.txt`
- Create: `.python-version`

**Step 1: Create `mkdocs.yml`**

```yaml
site_name: Pantsagon
site_description: Hexagonal monorepos in Pants - generated with enforced boundaries.
site_url: https://engineeringergonomics.github.io/pantsagon/
repo_url: https://github.com/EngineeringErgonomics/pantsagon
repo_name: EngineeringErgonomics/pantsagon
edit_uri: edit/main/docs/

theme:
  name: material
  language: en
  features:
    - navigation.instant
    - navigation.instant.progress
    - navigation.tracking
    - navigation.sections
    - navigation.expand
    - navigation.path
    - toc.follow
    - content.action.edit
    - content.code.copy
    - content.tabs.link
    - search.suggest
    - search.highlight
  icon:
    repo: fontawesome/brands/github
  palette:
    - scheme: default
      primary: indigo
      accent: indigo

plugins:
  - search

markdown_extensions:
  - admonition
  - attr_list
  - def_list
  - footnotes
  - pymdownx.details
  - pymdownx.superfences
  - pymdownx.inlinehilite
  - pymdownx.highlight:
      anchor_linenums: true
  - pymdownx.tabbed:
      alternate_style: true
  - toc:
      permalink: true

extra:
  version:
    provider: mike

nav:
  - Home: index.md

  - Getting started:
      - Quickstart: getting-started/quickstart.md
      - Generated repo tour: getting-started/generated-repo-tour.md
      - FAQ: getting-started/faq.md

  - Concepts:
      - Architecture: concepts/architecture.md
      - Documentation contract: concepts/documentation-contract.md
      - Hexagonal layering: concepts/hexagonal-architecture.md
      - Packs: concepts/packs.md
      - Repo lock: concepts/repo-lock.md
      - Diagnostics: concepts/diagnostics.md
      - Trust model: concepts/trust-and-security.md

  - CLI:
      - Overview: cli/index.md
      - init: cli/init.md
      - add service: cli/add-service.md
      - validate: cli/validate.md
      - Exit codes: cli/exit-codes.md

  - Pack authoring:
      - Overview: pack-authoring/index.md
      - Pack format: pack-authoring/pack-format.md
      - Variables: pack-authoring/variables.md
      - Validation: pack-authoring/validation.md
      - Publishing: pack-authoring/publishing.md

  - Plugin authoring:
      - Overview: plugin-authoring/index.md
      - Ports: plugin-authoring/ports.md
      - Adapters: plugin-authoring/adapters.md
      - Discovery: plugin-authoring/discovery.md

  - Reference:
      - Schemas:
          - pack.schema.v1: reference/pack.schema.v1.md
          - repo lock schema: reference/repo-lock.schema.v1.md
          - result schema: reference/result.schema.v1.md
      - Diagnostic codes: reference/diagnostic-codes.md

  - Contributing:
      - Docs: contributing/docs.md
```

**Step 2: Create `docs/requirements.txt`**

```txt
mkdocs-material==9.5.36
mike==2.1.2
```

**Step 3: Create `.python-version`**

```txt
3.12.0
```

**Step 4: Commit**

```bash
git add mkdocs.yml docs/requirements.txt .python-version
git commit -m "docs: add mkdocs config and pinned deps"
```

---

### Task 2: Create docs tree + starter content + contract + contributing page

**Files:**
- Create: `docs/index.md`
- Create: `docs/getting-started/quickstart.md`
- Create: `docs/getting-started/generated-repo-tour.md`
- Create: `docs/getting-started/faq.md`
- Create: `docs/concepts/architecture.md`
- Create: `docs/concepts/documentation-contract.md`
- Create: `docs/concepts/hexagonal-architecture.md`
- Create: `docs/concepts/packs.md`
- Create: `docs/concepts/repo-lock.md`
- Create: `docs/concepts/diagnostics.md`
- Create: `docs/concepts/trust-and-security.md`
- Create: `docs/cli/index.md`
- Create: `docs/cli/init.md`
- Create: `docs/cli/add-service.md`
- Create: `docs/cli/validate.md`
- Create: `docs/cli/exit-codes.md`
- Create: `docs/pack-authoring/index.md`
- Create: `docs/pack-authoring/pack-format.md`
- Create: `docs/pack-authoring/variables.md`
- Create: `docs/pack-authoring/validation.md`
- Create: `docs/pack-authoring/publishing.md`
- Create: `docs/plugin-authoring/index.md`
- Create: `docs/plugin-authoring/ports.md`
- Create: `docs/plugin-authoring/adapters.md`
- Create: `docs/plugin-authoring/discovery.md`
- Create: `docs/contributing/docs.md`

**Step 1: Create `docs/index.md`**

```md
# Pantsagon

Pantsagon bootstraps **hexagonal monorepos** managed by **Pants**, with enforcement from day one.

You use Pantsagon to generate a repository where:

- each service is structured as `domain/`, `application/`, `adapters/`, `entrypoints/`
- shared code is split into **foundation** (pure) and **shared adapters** (allowlisted integrations)
- dependency boundaries hard-fail locally and in CI
- optional packs add contract-first OpenAPI and Docker packaging

## What you can do in v1

- `pantsagon init` - create a new monorepo
- `pantsagon add service` - add a new service skeleton
- `pantsagon validate` - validate invariants and optionally run Pants checks

## Key concepts

- **Packs**: versioned templates (`pack.yaml` + `copier.yml` + `templates/`)
- **Repo lock**: `.pantsagon.toml` is the single source of truth for pack pins and answers
- **Diagnostics**: structured errors/warnings emitted by all frontends

Start with **Getting started → Quickstart**.

Looking to contribute? See **Contributing → Docs**.
```

**Step 2: Create Getting started pages**

```md
# Quickstart

## Install Pantsagon

Recommended (isolated):
- `pipx install pantsagon`

## Create a repo

```bash
pantsagon init my-repo \
  --lang python \
  --services monitors,governance \
  --feature openapi \
  --feature docker
```

## Add a service

```bash
cd my-repo
pantsagon add service billing --lang python --feature docker
```

## Validate

```bash
pantsagon validate
pantsagon validate --exec
```

* `validate` checks structure and manifests
* `validate --exec` runs Pants goals (lint/check/test as configured)

See **CLI → init** for full flags and semantics.
```

```md
# Generated repo tour

A generated repo has these top-level areas:

- `services/` - independently-deployable services
- `shared/foundation/` - pure primitives, globally allowed
- `shared/adapters/` - reusable integrations (allowlisted)
- `tools/` - repo-owned checks (e.g., forbidden imports)
- `.pantsagon.toml` - pack pins and answers (source of truth)

Each service follows:

- `domain/`: pure business rules
- `application/`: use-cases
- `adapters/`: IO implementations
- `entrypoints/`: CLI/HTTP/worker wiring

The repo is designed so layering is enforced by Pants dependency rules.
```

```md
# FAQ

## Does Pantsagon support languages other than Python?

Not in v1. The architecture supports multi-language packs later.

## Do I have to use Docker?

No. Docker is a feature pack.

## Why is layering enforced?

Because “directory structure” alone does not stop coupling. Enforcement makes the architecture real.

## Does Pantsagon run Pants during generation?

Only if you ask for it (e.g., `validate --exec`), to keep init fast and predictable.
```

**Step 3: Create Concepts pages (including documentation contract)**

```md
# Architecture

Pantsagon itself is hexagonal:

- **Domain** models `Blueprint → PackSelection → RenderPlan → RepoLock → Diagnostics`
- **Application** orchestrates `init`, `add service`, and `validate`
- **Ports** define pack discovery, rendering, workspace IO, policy checks, and command execution
- **Adapters** implement those ports (Copier renderer, filesystem workspace, bundled/local packs)

This lets Pantsagon support multiple frontends and third-party extensions without forking.
```

```md
# Documentation contract

This page defines the documentation requirements and rules for Pantsagon releases.

## Release requirements

Every release must include:

- updated CLI docs if flags changed
- updated schema docs if schemas changed
- updated diagnostic codes if codes changed
- updated pack docs if pack format or bundled packs changed

## Versioning rules

Documentation is published per tool version:

- `dev` - tracks `main`
- `latest` - alias for the newest release
- `vX.Y.Z` - tagged releases
- `pr-<num>` - PR previews

## Local docs workflow

```bash
pip install -r docs/requirements.txt
pip install pyyaml
python scripts/generate_schema_docs.py
python scripts/generate_diagnostic_codes.py
mkdocs serve
```

## Generated reference docs

Reference docs are generated and must not be edited by hand.

- generator scripts run in CI
- CI fails if `git diff` is non-empty after generation
- contributors must run generators locally before committing

If you need to change reference docs, update the source files and re-run the generators.
```

```md
# Hexagonal architecture (generated repos)

Generated repos follow a strict layering model:

- `domain`: pure rules and types (no IO)
- `application`: use-cases (no concrete integrations)
- `adapters`: integrations and IO (SDKs, HTTP, DB, etc.)
- `entrypoints`: wiring (CLI/HTTP/workers)

The critical property is **dependency direction**:
- domain depends only on itself (+ foundation)
- application depends on domain (+ foundation)
- adapters depend on application/domain (+ allowlisted shared adapters)
- entrypoints depend on adapters/application/domain
```

```md
# Packs

A pack is a versioned directory containing:

- `pack.yaml` - tool-agnostic manifest (authoritative)
- `copier.yml` - Copier rendering config
- `templates/` - template files

Pantsagon validates:
- `pack.yaml` against a JSON Schema
- `pack.yaml.variables` ↔ `copier.yml` variables consistency

Packs can be bundled with Pantsagon or loaded from a local directory in v1.
```

```md
# Repo lock: .pantsagon.toml

`.pantsagon.toml` is the single source of truth for:

- tool version
- selected packs (id/version/source)
- selected features and services
- resolved answers passed to the renderer
- strictness settings

In v1:
- pack versions are pinned and never auto-upgraded
- `add service` updates the lock deterministically
```

```md
# Diagnostics

All frontends emit structured diagnostics:

- code (stable identifier)
- rule (stable rule id / namespace)
- severity (error|warn|info)
- message
- optional location/hint/details

Commands return a `Result`:
- diagnostics
- artifacts (written paths, applied packs, executed commands)
- exit_code

Use `--json` to emit a machine-readable Result (for CI / GH Actions).
```

```md
# Trust and security

Packs are treated as untrusted content by default.

- Hook execution is disabled unless explicitly allowed (or pack is trusted).
- v1 supports only bundled and local packs (no network fetching).

Future:
- trust allowlist (local file)
- signed pack metadata
- registry-based distribution
```

**Step 4: Create CLI pages**

```md
# CLI overview

v1 commands:

- `pantsagon init`
- `pantsagon add service`
- `pantsagon validate`

All commands support structured diagnostics and stable exit codes.
```

```md
# pantsagon init

Create a new monorepo.

```bash
pantsagon init <repo>
```

Common flags:

* `--lang python` (required in v1)
* `--services a,b`
* `--feature openapi` (repeatable)
* `--feature docker` (repeatable)
* `--strict`
* `--renderer copier`
* `--non-interactive`
```

```md
# pantsagon add service

Add a new service skeleton into an existing Pantsagon repo.

```bash
pantsagon add service <name> --lang python
```

Optional:

* `--feature openapi`
* `--feature docker`
* `--strict`
```

```md
# pantsagon validate

Validate `.pantsagon.toml`, packs, and repo invariants.

```bash
pantsagon validate
```

Flags:

* `--exec` runs configured Pants goals (lint/check/test etc.)
* `--strict` upgrades warnings to errors
* `--json` outputs machine-readable Result
```

```md
# Exit codes

Stable exit codes:

- `0` success
- `2` validation failure (schema/invariants/compatibility)
- `3` execution failure (IO/renderer/subprocess)
- `4` internal error (unexpected exception)
```

**Step 5: Create Pack authoring pages**

```md
# Pack authoring

Packs are the primary extension mechanism.

A pack contains:
- `pack.yaml` (authoritative manifest)
- `copier.yml` (renderer config)
- `templates/`

Pantsagon enforces:
- schema validation
- manifest ↔ copier variable cross-check
- render smoke-test (for bundled packs)
```

```md
# Pack format

Minimum pack structure:

```text
<pack>/
  pack.yaml
  copier.yml
  templates/
```

`pack.yaml` declares:

* id + version
* compatibility
* requires/provides
* variables
```

```md
# Variables

Variables are declared in `pack.yaml` and mirrored in `copier.yml`.

Policy:
- every manifest variable must exist in copier questions
- undeclared copier variables are errors (default)
- default mismatches are warnings (strict mode => errors)
```

```md
# Validation

Bundled packs must pass:
1) `pack.yaml` schema validation
2) manifest ↔ copier variable cross-check
3) render smoke-test with minimal inputs
```

```md
# Publishing

v1 supports:
- bundled packs (shipped with Pantsagon)
- local directory packs (user-provided paths)

Future:
- git packs
- registry packs
```

**Step 6: Create Plugin authoring pages**

```md
# Plugin authoring

Plugins provide adapter implementations for ports (future scope).

In v1, plugins are not loaded, but the port contracts are designed for it.
```

```md
# Ports

Core ports:
- PackCatalogPort
- RendererPort
- WorkspacePort
- PolicyEnginePort
- CommandPort

Ports accept and return domain objects and must not leak implementation details.
```

```md
# Adapters

Adapters implement ports.
They should:
- raise typed AdapterError on IO/exec failures
- return Result/Diagnostics for expected validation outcomes
```

```md
# Discovery (future)

Future plugins will be discovered via Python entry points, grouped by port:

- pantsagon.pack_catalog
- pantsagon.renderer
- pantsagon.workspace
- pantsagon.policy_engine
- pantsagon.command_runner
```

**Step 7: Create Contributing docs page**

```md
# Contributing to docs

Docs are part of the Pantsagon API surface. Keep them versioned and reproducible.

## Where to edit

- User docs live in `docs/`
- Reference docs are generated from `schemas/` and `pantsagon/diagnostics/codes.yaml`

## Edit links

Each page has an “Edit this page” link in the header.
If you’re a pack author or plugin author, start in **Pack authoring** or **Plugin authoring**.

## Local workflow

```bash
pip install -r docs/requirements.txt
pip install pyyaml
python scripts/generate_schema_docs.py
python scripts/generate_diagnostic_codes.py
mkdocs serve
```

## Generated files

Generated reference docs must not be edited by hand.
Run the scripts above to update them.

## Backlog

- Docs: remove PR preview versions from mike on PR close
```

**Step 8: Commit**

```bash
git add docs/index.md \
  docs/getting-started/quickstart.md \
  docs/getting-started/generated-repo-tour.md \
  docs/getting-started/faq.md \
  docs/concepts/architecture.md \
  docs/concepts/documentation-contract.md \
  docs/concepts/hexagonal-architecture.md \
  docs/concepts/packs.md \
  docs/concepts/repo-lock.md \
  docs/concepts/diagnostics.md \
  docs/concepts/trust-and-security.md \
  docs/cli/index.md \
  docs/cli/init.md \
  docs/cli/add-service.md \
  docs/cli/validate.md \
  docs/cli/exit-codes.md \
  docs/pack-authoring/index.md \
  docs/pack-authoring/pack-format.md \
  docs/pack-authoring/variables.md \
  docs/pack-authoring/validation.md \
  docs/pack-authoring/publishing.md \
  docs/plugin-authoring/index.md \
  docs/plugin-authoring/ports.md \
  docs/plugin-authoring/adapters.md \
  docs/plugin-authoring/discovery.md \
  docs/contributing/docs.md
git commit -m "docs: add starter content and contributor guidance"
```

---

### Task 3: Add failing tests for schema-doc generator (TDD)

**Files:**
- Create: `tests/test_generate_schema_docs.py`
- Create: `scripts/__init__.py`

**Step 1: Create `scripts/__init__.py`**

```python
# Intentionally empty to allow imports in tests.
```

**Step 2: Write the failing test `tests/test_generate_schema_docs.py`**

```python
import json
import tempfile
import unittest
from pathlib import Path

from scripts import generate_schema_docs


class GenerateSchemaDocsTest(unittest.TestCase):
    def test_generates_markdown_from_schemas(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            schemas_dir = repo_root / "schemas"
            schemas_dir.mkdir(parents=True)
            (repo_root / "docs" / "reference").mkdir(parents=True)

            def write_schema(name: str, title: str) -> None:
                (schemas_dir / name).write_text(
                    json.dumps(
                        {
                            "$schema": "https://json-schema.org/draft/2020-12/schema",
                            "$id": f"https://example.test/{name}",
                            "title": title,
                            "description": f"{title} description",
                            "type": "object",
                            "properties": {"alpha": {"type": "string"}},
                            "required": ["alpha"],
                        }
                    ),
                    encoding="utf-8",
                )

            write_schema("pack.schema.v1.json", "Pack Schema")
            write_schema("repo-lock.schema.v1.json", "Repo Lock Schema")
            write_schema("result.schema.v1.json", "Result Schema")

            generate_schema_docs.generate(repo_root)

            out = (repo_root / "docs" / "reference" / "pack.schema.v1.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("Generated file. Do not edit directly.", out)
            self.assertIn("# Pack Schema", out)
            self.assertIn("alpha", out)


if __name__ == "__main__":
    unittest.main()
```

**Step 3: Run the test to verify it fails**

Run: `python -m unittest tests/test_generate_schema_docs.py -v`

Expected: FAIL with `AttributeError` or `ImportError` because `generate_schema_docs.generate` does not exist yet.

**Step 4: Commit**

```bash
git add scripts/__init__.py tests/test_generate_schema_docs.py
git commit -m "test: add schema docs generator test"
```

---

### Task 4: Implement schema-doc generator to pass tests

**Files:**
- Create: `scripts/generate_schema_docs.py`

**Step 1: Write minimal implementation `scripts/generate_schema_docs.py`**

```python
#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]

SCHEMA_MAP = {
    "pack.schema.v1.json": "pack.schema.v1.md",
    "repo-lock.schema.v1.json": "repo-lock.schema.v1.md",
    "result.schema.v1.json": "result.schema.v1.md",
}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _md_escape(s: str) -> str:
    return s.replace("<", "&lt;").replace(">", "&gt;")


def _render_generated_notice(command: str) -> str:
    return "\n".join(
        [
            "> **Generated file. Do not edit directly.**",
            f"> Run: `{command}`",
        ]
    )


def _render_schema_overview(schema: dict[str, Any]) -> str:
    title = schema.get("title") or "Schema"
    desc = schema.get("description") or ""
    schema_id = schema.get("$id") or ""
    schema_version = schema.get("$schema") or ""

    lines: list[str] = []
    lines.append(f"# {_md_escape(title)}")
    if desc:
        lines.append("")
        lines.append(desc.strip())
    if schema_id or schema_version:
        lines.append("")
        if schema_id:
            lines.append(f"- **$id**: `{schema_id}`")
        if schema_version:
            lines.append(f"- **$schema**: `{schema_version}`")
    return "\n".join(lines)


def _render_properties(schema: dict[str, Any]) -> str:
    props: dict[str, Any] = schema.get("properties") or {}
    required: set[str] = set(schema.get("required") or [])

    if not props:
        return "## Properties\n\n(No top-level properties declared.)"

    lines: list[str] = []
    lines.append("## Properties")
    lines.append("")
    lines.append("| Name | Type | Required | Description |")
    lines.append("|---|---|---:|---|")

    for name in sorted(props.keys()):
        p = props[name] or {}
        p_type = p.get("type")
        if isinstance(p_type, list):
            type_str = " | ".join(str(t) for t in p_type)
        else:
            type_str = str(p_type) if p_type is not None else "(unspecified)"
        desc = (p.get("description") or "").strip().replace("\n", " ")
        lines.append(
            f"| `{name}` | `{type_str}` | {'yes' if name in required else 'no'} | {desc} |"
        )

    return "\n".join(lines)


def _render_raw(schema: dict[str, Any]) -> str:
    pretty = json.dumps(schema, indent=2, sort_keys=True)
    return "## Raw JSON\n\n```json\n" + pretty + "\n```\n"


def generate(repo_root: Path = REPO_ROOT) -> None:
    schemas_dir = repo_root / "schemas"
    out_dir = repo_root / "docs" / "reference"
    out_dir.mkdir(parents=True, exist_ok=True)

    for in_name, out_name in SCHEMA_MAP.items():
        in_path = schemas_dir / in_name
        if not in_path.exists():
            raise SystemExit(f"Schema file not found: {in_path}")

        schema = _load_json(in_path)
        md = "\n\n".join(
            [
                _render_generated_notice("python scripts/generate_schema_docs.py"),
                _render_schema_overview(schema),
                _render_properties(schema),
                _render_raw(schema),
            ]
        )
        out_path = out_dir / out_name
        out_path.write_text(md + "\n", encoding="utf-8")

    print(f"Generated schema docs into {out_dir}")


if __name__ == "__main__":
    generate()
```

**Step 2: Run tests to verify pass**

Run: `python -m unittest tests/test_generate_schema_docs.py -v`

Expected: PASS

**Step 3: Commit**

```bash
git add scripts/generate_schema_docs.py
git commit -m "feat: add schema docs generator"
```

---

### Task 5: Add failing tests for diagnostic-codes generator (TDD)

**Files:**
- Create: `tests/test_generate_diagnostic_codes.py`

**Step 1: Write the failing test `tests/test_generate_diagnostic_codes.py`**

```python
import tempfile
import unittest
from pathlib import Path

from scripts import generate_diagnostic_codes


class GenerateDiagnosticCodesTest(unittest.TestCase):
    def test_generates_markdown_from_codes_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            src = repo_root / "pantsagon" / "diagnostics"
            src.mkdir(parents=True)
            (repo_root / "docs" / "reference").mkdir(parents=True)

            (src / "codes.yaml").write_text(
                """
version: 1
codes:
  - code: EXAMPLE_CODE
    severity: error
    rule: example.rule
    message: Example message
    hint: Example hint
""".lstrip(),
                encoding="utf-8",
            )

            generate_diagnostic_codes.generate(repo_root)

            out = (repo_root / "docs" / "reference" / "diagnostic-codes.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("Generated file. Do not edit directly.", out)
            self.assertIn("EXAMPLE_CODE", out)


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run the test to verify it fails**

Run: `python -m unittest tests/test_generate_diagnostic_codes.py -v`

Expected: FAIL with `AttributeError` or `ImportError` because `generate_diagnostic_codes.generate` does not exist yet.

**Step 3: Commit**

```bash
git add tests/test_generate_diagnostic_codes.py
git commit -m "test: add diagnostic codes generator test"
```

---

### Task 6: Implement diagnostic-codes generator to pass tests

**Files:**
- Create: `scripts/generate_diagnostic_codes.py`

**Step 1: Write minimal implementation `scripts/generate_diagnostic_codes.py`**

```python
#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _render_generated_notice(command: str) -> str:
    return "\n".join(
        [
            "> **Generated file. Do not edit directly.**",
            f"> Run: `{command}`",
        ]
    )


def generate(repo_root: Path = REPO_ROOT) -> None:
    src = repo_root / "pantsagon" / "diagnostics" / "codes.yaml"
    out = repo_root / "docs" / "reference" / "diagnostic-codes.md"

    if not src.exists():
        raise SystemExit(f"Diagnostics source not found: {src}")

    data = _load_yaml(src)
    if data.get("version") != 1:
        raise SystemExit(f"Unsupported diagnostics version: {data.get('version')}")

    codes = data.get("codes")
    if not isinstance(codes, list):
        raise SystemExit("Invalid codes.yaml: expected top-level 'codes' list")

    lines: list[str] = []
    lines.append(_render_generated_notice("python scripts/generate_diagnostic_codes.py"))
    lines.append("")
    lines.append("# Diagnostic codes")
    lines.append("")
    lines.append("This page is generated from `pantsagon/diagnostics/codes.yaml`.")
    lines.append("")
    lines.append("| Code | Severity | Rule | Message | Hint |")
    lines.append("|---|---|---|---|---|")

    for item in sorted(codes, key=lambda x: (x.get("code") or "")):
        code = (item.get("code") or "").strip()
        sev = (item.get("severity") or "").strip()
        rule = (item.get("rule") or "").strip()
        msg = (item.get("message") or "").strip().replace("\n", " ")
        hint = (item.get("hint") or "").strip().replace("\n", " ")

        if not code or not sev or not rule:
            raise SystemExit(f"Invalid diagnostic entry (missing required fields): {item}")

        lines.append(f"| `{code}` | `{sev}` | `{rule}` | {msg} | {hint} |")

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Generated {out}")


if __name__ == "__main__":
    generate()
```

**Step 2: Run tests to verify pass**

Run: `python -m unittest tests/test_generate_diagnostic_codes.py -v`

Expected: PASS

**Step 3: Commit**

```bash
git add scripts/generate_diagnostic_codes.py
git commit -m "feat: add diagnostic codes generator"
```

---

### Task 7: Add schemas + diagnostics codes source

**Files:**
- Create: `schemas/pack.schema.v1.json`
- Create: `schemas/repo-lock.schema.v1.json`
- Create: `schemas/result.schema.v1.json`
- Create: `pantsagon/diagnostics/codes.yaml`

**Step 1: Create `schemas/pack.schema.v1.json`**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://pantsagon.dev/schemas/pack.schema.v1.json",
  "title": "Pantsagon Pack Manifest (v1)",
  "description": "Tool-agnostic manifest describing a Pantsagon pack: identity, compatibility, features, and variables.",
  "type": "object",
  "required": ["id", "version", "compatibility"],
  "additionalProperties": false,
  "properties": {
    "schema_version": {
      "type": "integer",
      "const": 1,
      "description": "Schema version for this manifest."
    },
    "id": {
      "type": "string",
      "pattern": "^[a-z0-9_.-]+$",
      "description": "Globally unique pack identifier (e.g. pantsagon.python)."
    },
    "version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+$",
      "description": "SemVer version of the pack."
    },
    "description": {
      "type": "string",
      "description": "Human-readable description of the pack."
    },
    "compatibility": {
      "type": "object",
      "required": ["pants"],
      "additionalProperties": false,
      "properties": {
        "pants": {
          "type": "string",
          "description": "Supported Pants version range (PEP 440 / semver-style range)."
        },
        "languages": {
          "type": "object",
          "additionalProperties": {
            "type": "string",
            "description": "Supported version range for a language (e.g. python: \">=3.12,<3.15\")."
          }
        }
      }
    },
    "requires": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "packs": {
          "type": "array",
          "items": {
            "type": "string",
            "pattern": "^[a-z0-9_.-]+$"
          },
          "description": "Other packs that must be present for this pack to be applied."
        }
      }
    },
    "provides": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "features": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Feature flags provided by this pack (e.g. openapi, docker)."
        },
        "service_templates": {
          "type": "array",
          "description": "Service template capabilities exposed by this pack.",
          "items": {
            "type": "object",
            "required": ["kind", "language"],
            "additionalProperties": false,
            "properties": {
              "kind": {
                "type": "string",
                "enum": ["service"],
                "description": "Template kind."
              },
              "language": {
                "type": "string",
                "description": "Language supported by this template."
              },
              "layout": {
                "type": "string",
                "description": "Declared layout (e.g. hexagonal)."
              }
            }
          }
        }
      }
    },
    "variables": {
      "type": "array",
      "description": "Variables required or accepted by this pack.",
      "items": {
        "type": "object",
        "required": ["name", "type"],
        "additionalProperties": false,
        "properties": {
          "name": {
            "type": "string",
            "pattern": "^[a-zA-Z_][a-zA-Z0-9_]*$",
            "description": "Variable name."
          },
          "type": {
            "type": "string",
            "enum": ["string", "int", "bool", "enum"],
            "description": "Variable type."
          },
          "default": {
            "description": "Default value if not provided."
          },
          "required": {
            "type": "boolean",
            "default": false,
            "description": "Whether the variable is required."
          },
          "enum": {
            "type": "array",
            "items": { "type": "string" },
            "description": "Allowed values when type is enum."
          }
        }
      }
    }
  }
}
```

**Step 2: Create `schemas/repo-lock.schema.v1.json`**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://pantsagon.dev/schemas/repo-lock.schema.v1.json",
  "title": "Pantsagon Repo Lock (.pantsagon.toml) (v1)",
  "description": "Single source of truth for a Pantsagon-generated repository.",
  "type": "object",
  "required": ["tool", "resolved"],
  "additionalProperties": false,
  "properties": {
    "tool": {
      "type": "object",
      "required": ["name", "version"],
      "additionalProperties": false,
      "properties": {
        "name": {
          "type": "string",
          "const": "pantsagon"
        },
        "version": {
          "type": "string",
          "description": "Pantsagon tool version used to generate or update this repo."
        }
      }
    },
    "settings": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "renderer": {
          "type": "string",
          "default": "copier",
          "description": "Renderer adapter to use."
        },
        "strict": {
          "type": "boolean",
          "default": false,
          "description": "Whether strict mode is enabled."
        },
        "strict_manifest": {
          "type": "boolean",
          "default": true,
          "description": "Whether manifest/Copier mismatches are fatal."
        },
        "allow_hooks": {
          "type": "boolean",
          "default": false,
          "description": "Whether pack hooks are allowed to execute."
        }
      }
    },
    "selection": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "languages": {
          "type": "array",
          "items": { "type": "string" }
        },
        "features": {
          "type": "array",
          "items": { "type": "string" }
        },
        "services": {
          "type": "array",
          "items": {
            "type": "string",
            "pattern": "^[a-z][a-z0-9-]*$"
          }
        }
      }
    },
    "resolved": {
      "type": "object",
      "required": ["packs"],
      "additionalProperties": false,
      "properties": {
        "packs": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["id", "version", "source"],
            "additionalProperties": false,
            "properties": {
              "id": {
                "type": "string"
              },
              "version": {
                "type": "string"
              },
              "source": {
                "type": "string",
                "enum": ["bundled", "local", "git", "registry"]
              },
              "location": {
                "type": "string",
                "description": "Filesystem path or URL, depending on source."
              },
              "ref": {
                "type": "string",
                "description": "Git ref, commit, or registry digest."
              }
            }
          }
        },
        "answers": {
          "type": "object",
          "additionalProperties": true,
          "description": "Resolved variable answers passed to the renderer."
        }
      }
    }
  }
}
```

**Step 3: Create `schemas/result.schema.v1.json`**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://pantsagon.dev/schemas/result.schema.v1.json",
  "title": "Pantsagon Result (v1)",
  "description": "Structured output returned by Pantsagon commands for humans and machines.",
  "type": "object",
  "required": ["result_schema_version", "exit_code", "diagnostics"],
  "additionalProperties": false,
  "properties": {
    "result_schema_version": {
      "type": "integer",
      "const": 1,
      "description": "Schema version for the Result object."
    },
    "exit_code": {
      "type": "integer",
      "enum": [0, 2, 3, 4],
      "description": "Process exit code."
    },
    "diagnostics": {
      "type": "array",
      "description": "Structured diagnostics emitted during execution.",
      "items": {
        "type": "object",
        "required": ["code", "rule", "severity", "message"],
        "additionalProperties": false,
        "properties": {
          "id": {
            "type": "string",
            "description": "Stable or deterministic diagnostic identifier."
          },
          "code": {
            "type": "string",
            "description": "Short, stable diagnostic code (e.g. PACK_NOT_FOUND)."
          },
          "rule": {
            "type": "string",
            "description": "Rule identifier or namespace (e.g. pack.requires.packs)."
          },
          "severity": {
            "type": "string",
            "enum": ["error", "warn", "info"]
          },
          "message": {
            "type": "string"
          },
          "location": {
            "type": "object",
            "description": "Optional structured location of the diagnostic.",
            "additionalProperties": true
          },
          "hint": {
            "type": "string",
            "description": "Optional remediation hint."
          },
          "details": {
            "type": "object",
            "additionalProperties": true,
            "description": "Optional machine-readable details."
          }
        }
      }
    },
    "artifacts": {
      "type": "array",
      "description": "Artifacts produced by the command (paths, packs, commands).",
      "items": {
        "type": "object",
        "additionalProperties": true
      }
    }
  }
}
```

**Step 4: Create `pantsagon/diagnostics/codes.yaml`**

```yaml
version: 1

codes:
  - code: PACK_NOT_FOUND
    severity: error
    rule: pack.catalog.fetch
    message: Pack could not be found.
    hint: Check pack id/version and configured pack sources.

  - code: PACK_MISSING_REQUIRED
    severity: error
    rule: pack.requires.packs
    message: Pack is missing required dependency packs.
    hint: Add the required pack or choose a compatible feature set.

  - code: COPIER_UNDECLARED_VARIABLE
    severity: error
    rule: pack.variables.copier_undeclared
    message: Copier defines a variable that is not declared in pack.yaml.
    hint: Declare it in pack.yaml.variables or remove it from copier.yml.

  - code: COPIER_DEFAULT_MISMATCH
    severity: warn
    rule: pack.variables.default_mismatch
    message: Copier default does not match pack.yaml default.
    hint: Align defaults, or run in strict mode to fail builds.
```

**Step 5: Commit**

```bash
git add schemas/pack.schema.v1.json \
  schemas/repo-lock.schema.v1.json \
  schemas/result.schema.v1.json \
  pantsagon/diagnostics/codes.yaml
git commit -m "docs: add schema and diagnostics sources"
```

---

### Task 8: Generate reference docs from sources

**Files:**
- Create: `docs/reference/pack.schema.v1.md`
- Create: `docs/reference/repo-lock.schema.v1.md`
- Create: `docs/reference/result.schema.v1.md`
- Create: `docs/reference/diagnostic-codes.md`

**Step 1: Run generators**

```bash
python scripts/generate_schema_docs.py
python scripts/generate_diagnostic_codes.py
```

**Step 2: Spot-check headers**

Check each generated file begins with:
- “Generated file. Do not edit directly.”
- “Run: `python scripts/...`”

**Step 3: Commit**

```bash
git add docs/reference/pack.schema.v1.md \
  docs/reference/repo-lock.schema.v1.md \
  docs/reference/result.schema.v1.md \
  docs/reference/diagnostic-codes.md
git commit -m "docs: generate reference docs"
```

---

### Task 9: Add docs GitHub Actions workflow

**Files:**
- Create: `.github/workflows/docs.yml`

**Step 1: Create `.github/workflows/docs.yml`**

```yaml
name: Docs

on:
  pull_request:
    paths:
      - "docs/**"
      - "mkdocs.yml"
      - ".github/workflows/docs.yml"
      - "schemas/**"
      - "scripts/**"
      - "pantsagon/diagnostics/codes.yaml"
  push:
    branches: ["main"]
    tags: ["v*.*.*"]
    paths:
      - "docs/**"
      - "mkdocs.yml"
      - ".github/workflows/docs.yml"
      - "schemas/**"
      - "scripts/**"
      - "pantsagon/diagnostics/codes.yaml"
  workflow_dispatch: {}

permissions:
  contents: write
  pull-requests: write

concurrency:
  group: docs-${{ github.ref }}
  cancel-in-progress: true

jobs:
  docs:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install docs dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r docs/requirements.txt

      - name: Install generator dependencies
        run: |
          pip install pyyaml

      - name: Generate reference docs (schemas + diagnostic codes)
        run: |
          python scripts/generate_schema_docs.py
          python scripts/generate_diagnostic_codes.py

      - name: Fail if generated docs are out of date
        run: |
          git diff --exit-code

      - name: Build (strict)
        run: |
          mkdocs build --strict

      - name: Configure git identity
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"

      - name: Publish PR preview
        if: github.event_name == 'pull_request'
        env:
          PR_NUM: ${{ github.event.number }}
        run: |
          mike deploy --push --branch gh-pages "pr-${PR_NUM}"

      - name: Comment PR preview URL
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v7
        with:
          script: |
            const pr = context.payload.pull_request.number;
            const owner = context.repo.owner;
            const repo = context.repo.repo;
            const url = `https://${owner}.github.io/${repo}/pr-${pr}/`;
            const body = [
              "Docs preview published:",
              "",
              url
            ].join("\n");
            await github.rest.issues.createComment({
              owner,
              repo,
              issue_number: pr,
              body
            });

      - name: Publish dev docs (main)
        if: github.event_name == 'push' && github.ref == 'refs/heads/main'
        run: |
          mike deploy --push --branch gh-pages "dev"

      - name: Publish release docs (tag) + update latest
        if: github.event_name == 'push' && startsWith(github.ref, 'refs/tags/v')
        env:
          TAG: ${{ github.ref_name }}
        run: |
          mike deploy --push --branch gh-pages --update-aliases "${TAG}" latest
```

**Step 2: Commit**

```bash
git add .github/workflows/docs.yml
git commit -m "ci: add docs build and publish workflow"
```

---

### Task 10: Verification

**Step 1: Run generators locally**

```bash
python scripts/generate_schema_docs.py
python scripts/generate_diagnostic_codes.py
```

**Step 2: Build docs locally**

```bash
mkdocs build --strict
```

Expected: `build` succeeds with no warnings or missing files.

