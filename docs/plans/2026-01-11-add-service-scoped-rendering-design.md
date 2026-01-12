# Add Service Scoped Rendering Design

**Goal:** Implement `pantsagon add service` to render only service-scoped outputs from already-pinned packs, update the repo lock minimally, and avoid unintended shared-file changes.

## Context
- v1 contract: `.pantsagon.toml` is authoritative; `add service` must not mutate `resolved.packs`.
- Rendering must be service-scoped: only `services/<svc>/...` and optional service-scoped OpenAPI artifacts.
- No pack schema changes for v1.

## Requirements
- Validate service name (format + reserved) and ensure the service directory does not already exist.
- Render each pinned pack to a temporary directory.
- Copy only allowed paths into a staging workspace:
  - `services/<service_name_kebab>/**`
  - If `pantsagon.openapi` is selected in `resolved.packs`, allow:
    - `shared/contracts/openapi/<service_name_kebab>.yaml`
    - `shared/contracts/openapi/README.md` (only if it does not exist yet)
- Copy nothing else (no root files, no `pants.toml`, no `.github/`, no tools, no shared foundation, no other services).
- Commit staging atomically (best-effort rollback on failure).
- Update `.pantsagon.toml`:
  - append `selection.services`
  - merge service answers into `resolved.answers`
  - keep `resolved.packs` unchanged (order and pins preserved)

## Proposed Approach
- Add a new scoped rendering path to `application/add_service.py`:
  - Read lock, validate, and build service answers (kebab + snake variants).
  - For each resolved pack in lock, resolve pack path (bundled for v1; local supported if lock entry contains `location`).
  - Render to `tmp/<pack-id>` with Copier (hooks disabled).
  - Filter copy from temp to staging using explicit path rules.
  - Write updated lock to staging and commit.

## Error Handling
- If any copy/render fails, emit diagnostics and roll back staging without touching the repo.
- If OpenAPI artifacts are allowed but already exist, skip copying README and only copy the service-specific spec if missing.

## Testing
- Add unit tests covering:
  - `add service` renders only allowed paths.
  - OpenAPI artifact rules (spec created; README not overwritten if present).
  - Lock updates (services appended; answers merged; resolved.packs unchanged).
- Add CLI test to ensure `pantsagon add-service` produces expected files.

