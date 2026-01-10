# Pants Monorepo Conversion Design

**Date:** 2026-01-10

## Goal
Convert this repo into a Pants-managed monorepo with strict hexagonal layering, hard dependency boundaries, and contract-first guardrails, using Pants as the single control plane.

## Decisions (validated)
- `pantsagon` becomes a **service**: `services/pantsagon/src/pantsagon/` with top-level layers: `domain/`, `ports/`, `application/`, `adapters/`, `entrypoints/`.
- CLI stays in `entrypoints/cli.py` and is executed via a packaging target at the service root.
- `ports/` is a first-class layer (not nested under application).
- `packs/` stays at repo root; `schemas/` move to `shared/contracts/schemas/`.
- Entry points are **non-importable**: only a packaging target may depend on them.
- Tag taxonomy includes an explicit `layer:ports`.
- No cross-service imports by default; add a `public_api` target only if needed later.

## Target Layout
```
repo/
  pants.toml
  pyproject.toml
  pyrightconfig.json
  .ruff.toml

  3rdparty/
    python/
      requirements.txt
      BUILD

  shared/
    foundation/
      src/...
      tests/...
      BUILD
    adapters/
      <integration>/
        src/...
        tests/...
        BUILD
    contracts/
      schemas/
        pack.schema.v1.json
      BUILD

  services/
    pantsagon/
      src/pantsagon/
        domain/
        ports/
        application/
        adapters/
        entrypoints/
      tests/
      BUILD

  packs/
    core/
    python/
    openapi/
    docker/

  tools/
    forbidden_imports/
      forbidden_imports.yaml
      src/...
      tests/...
      BUILD
```

## Dependency Rules (Hexagonal Enforcement)
- **domain** → domain + `shared/foundation`
- **ports** → ports + domain + `shared/foundation`
- **application** → application + ports + domain + `shared/foundation`
- **adapters** → adapters + application + ports + domain + `shared/foundation` + allowlisted `shared/adapters` + 3rdparty
- **entrypoints** → entrypoints + adapters + application + ports + domain + `shared/foundation`

**Service boundary:** each layer target uses `__dependents_rules__` limited to `svc:pantsagon` tags, except entrypoints which are only depended on by a packaging target.

## Tags
- `svc:pantsagon`
- `layer:domain|ports|application|adapters|entrypoints`
- `shared:foundation|adapters|contracts`
- `adapter:<integration>`
- Optional: `domain:<group>`, `team:<name>`

## BUILD Snippet Patterns (key example: entrypoints)
```python
# services/pantsagon/src/pantsagon/entrypoints/BUILD
__dependents_rules__ = [
  {"address": "services/pantsagon:cli"},
]

python_sources(
  name="entrypoints",
  tags=["svc:pantsagon", "layer:entrypoints"],
  dependencies=[
    "//services/pantsagon/src/pantsagon/adapters:adapters",
    "//services/pantsagon/src/pantsagon/application:application",
    "//services/pantsagon/src/pantsagon/ports:ports",
    "//services/pantsagon/src/pantsagon/domain:domain",
    "//shared/foundation:lib",
  ],
  __dependencies_rules__=[
    {"path": "services/pantsagon/src/pantsagon/entrypoints/**"},
    {"path": "services/pantsagon/src/pantsagon/adapters/**"},
    {"path": "services/pantsagon/src/pantsagon/application/**"},
    {"path": "services/pantsagon/src/pantsagon/ports/**"},
    {"path": "services/pantsagon/src/pantsagon/domain/**"},
    {"path": "shared/foundation/src/**"},
    {"path": "shared/adapters/**"},
    {"path": "3rdparty/python/**"},
  ],
)
```

```python
# services/pantsagon/BUILD
pex_binary(
  name="cli",
  entry_point="pantsagon.entrypoints.cli:app",
  dependencies=["//services/pantsagon/src/pantsagon/entrypoints:entrypoints"],
)
```

## Pants Baseline
- `pants.toml` per guide (Python, docker, ruff, pyright, pytest, openapi, visibility, terraform optional).
- `[python-infer].unowned_dependency_behavior = "error"`
- `[visibility].enforce = true`
- Single resolve at `3rdparty/python/python-default.lock`.

## Contracts & Assets
- JSON Schemas in `shared/contracts/schemas/` (validated with Pants/OpenAPI tooling if applicable).
- Packs remain at repo root as tool-owned assets (`packs/`).

## Forbidden Imports Tooling
- Extend the forbidden-import checker to include **ports** (deny frameworks/SDKs in `services/**/ports/**`).
- Keep domain/application/ports checks as developer-friendly errors; Pants rules remain authoritative.

## Tests Policy
- Domain tests: depend on domain only.
- Application tests: depend on application + ports + domain.
- Adapter tests: depend on adapters + ports + domain + application.
- Entry point tests: minimal; prefer integration tests.

## CI Commands
- `pants tailor --check ::`
- `pants update-build-files --check ::`
- `pants lint check test ::`

## Migration Summary
- Move `pantsagon/` → `services/pantsagon/src/pantsagon/`
- Keep layer subdirectories and add `ports/` as a top-level layer.
- Move `tests/` → `services/pantsagon/tests/`
- Move `schemas/pack.schema.v1.json` → `shared/contracts/schemas/`
- Keep `packs/` at repo root
