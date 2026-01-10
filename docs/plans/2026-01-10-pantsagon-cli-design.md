# Pantsagon CLI + Pack System Design

**Goal:** Ship Pantsagon v1 as a hexagonal, pack-based scaffolding CLI that generates enforced Pants hexagonal monorepos with contract-first (OpenAPI) and Docker packaging support.

**Architecture:** Hexagonal core (domain/application) with ports/adapters. Packs are tool-agnostic via `pack.yaml`, rendered via Copier. CLI is a thin entrypoint; logic lives in application use-cases. `.pantsagon.toml` is the single source of truth for repo state.

**Tech Stack:** Python, Typer (CLI), Copier (renderer), Pants.

## Scope (v1)
- Commands: `init`, `add service`, `validate`.
- Packs: `core`, `python`, `openapi`, `docker`.
- Pack sources: bundled + local only (no git/registry in v1).
- Hooks: disabled by default; bundled packs may be allowed with explicit trust.
- No upgrade command in v1.

## Repo Layout
```
pantsagon/
  pantsagon/
    domain/
    application/
    ports/
    adapters/
      pack_catalog/
      renderer/
      workspace/
      policy/
      command/
    entrypoints/
  packs/
    _shared/
      templates/
    core/
    python/
    openapi/
    docker/
  schemas/
    pack.schema.v1.json
    lock.schema.v1.json
  tests/
  docs/
  pyproject.toml
  README.md
```

## Domain Model
- **Blueprint**: user intent (repo name, languages, services, features).
- **PackRef**: `{id, version, source, location?, git_ref?, commit?, digest?, subdir?}`.
- **PackDigest**: optional hash for content-addressing (v1 unused, but modeled).
- **PackSelection**: ordered list of PackRef + resolved dependency graph.
- **RenderPlan**: deterministic plan of outputs and a patch (create/modify/delete).
- **RepoLock**: representation of `.pantsagon.toml` (single source of truth).
- **Diagnostic**: structured error/warn/info with `code`, `rule`, `id`, `severity`, `message`, `location`, `hint`, `details`.
- **Result[T]**: `value?`, `diagnostics[]`, `artifacts[]`, `exit_code`.
- **Location** union: Pack(id,path), File(path,line,col), Path(path), Command(name).

## `.pantsagon.toml` Structure
```toml
[tool]
name = "pantsagon"
version = "1.0.0"

[settings]
renderer = "copier"
strict = false
strict_manifest = true
allow_hooks = false

[selection]
languages = ["python"]
features = ["openapi", "docker"]
services = ["monitors", "governance"]

[[resolved.packs]]
id = "pantsagon.core"
version = "1.0.0"
source = "bundled"

[resolved.answers]
python_min = "3.12"
python_max = "3.14"
```

## Use-Case Flows
### `init`
1. Parse inputs → `Blueprint`.
2. Resolve `PackSelection` (validate compatibility, required/conflicts).
3. Validate pack schema (`pack.yaml`) + manifest↔Copier cross-check.
4. Build deterministic `RenderPlan` (patch-oriented).
5. Workspace transaction: render into staging dir, write `.pantsagon.toml` in staging, then atomic commit.
6. Run repo policy checks.
7. Optional execution (`pants tailor --check`, `pants lint/check/test`) if explicitly requested.

### `add service`
- Validate repo + load `.pantsagon.toml`.
- Enforce naming rules (kebab-case, reserved names forbidden, deterministic package name mapping).
- Idempotent by default: fail if service exists unless `--overwrite` (future).
- Render only service-scoped `RenderPlan` into staging and commit atomically.
- Update `.pantsagon.toml`.

### `validate`
- Validate schema, compatibility, pack selection, and repo invariants.
- Detect lock drift: recompute expected paths from lock and check existence.
- Optional exec validation with `--exec`.

### `validate_pack` (internal use-case)
- Schema validation
- Manifest↔Copier cross-check
- Render smoke-test into temp dir

## Ports (Contracts)
- **PackCatalogPort**: list/find/fetch packs (by PackRef).
- **RendererPort**: render `RenderRequest` → `RenderOutcome` (renderer-agnostic).
- **WorkspacePort**: begin transaction, apply patch, commit/rollback atomically.
- **PolicyEnginePort**: validate packs + repo invariants, return Diagnostics.
- **CommandRunnerPort**: execute Pants commands (optional, explicit).

### Errors and Results
- Expected validation failures return `Result` with diagnostics (exit code 2).
- Execution/IO failures raise typed `AdapterError` (exit code 3).
- Exit code precedence: exec error → 3, else validation error → 2, else 0; unexpected → 4.

**AdapterError taxonomy** (stable):
- PackFetchError, PackReadError, PackParseError
- RendererTemplateError, RendererExecutionError
- WorkspaceTransactionError, WorkspaceCommitError
- CommandNotFound, CommandFailed, CommandTimeout

## Packs
- Pack format: `pack.yaml` (authoritative) + `copier.yml` (renderer config) + `templates/`.
- `pack.yaml` schema is validated by `schemas/pack.schema.v1.json`.
- Cross-check rules (strict by default):
  - all manifest variables must exist in Copier
  - no undeclared Copier variables unless `extra_variables=true`
  - default mismatch = warning (upgraded to error in `--strict`)

## Trust Model
- Trust is split between **content** and **hook execution**.
- Defaults: allow content from bundled/local; allow hooks from bundled only.
- `--allow-hooks` overrides (explicit).

## CLI Contract (v1)
- `pantsagon init <repo>`
  - `--lang python` (required)
  - `--services a,b`
  - `--feature openapi --feature docker` (alias `--with`)
  - `--non-interactive`
  - `--strict`
  - `--renderer copier`
  - `--json`
- `pantsagon add service <name>`
  - `--lang python`
  - `--feature openapi --feature docker`
  - `--strict`
  - `--json`
- `pantsagon validate`
  - `--exec`
  - `--strict`
  - `--json`

## JSON Output
- Always include `result_schema_version`, `timestamp`, `command`, `args`, `exit_code`.
- `Diagnostic` is stable with structured `location` and deterministic `id`.

## Testing Strategy
- Deterministic mode via `--deterministic` or `PANTSAGON_DETERMINISTIC=1`.
- Unit tests: domain invariants, pack resolution, naming rules, exit-code precedence.
- Adapter tests: Copier failure mapping, workspace commit/rollback, policy checks.
- Pack tests (gated on any change under `packs/**`):
  1) schema validation
  2) manifest↔Copier cross-check
  3) render smoke-test
- E2E tests: verify key files/paths and invariants (avoid full-tree diffs by default).

## Versioning & Compatibility
- Tool and packs use SemVer independently.
- Packs declare compatibility ranges in `pack.yaml`.
- Bundled pack compatibility is verified in CI.
- Pack SemVer rules:
  - Patch: docs/typos, non-functional tweaks
  - Minor: additive variables with defaults, additive files
  - Major: variable removals, path renames, behavior changes
- Schema versions are file-based (`pack.schema.v1.json`).

## Implementation Notes (v1)
- Bundled packs: core/python/openapi/docker.
- Local pack catalog adapter reads `pack.yaml` from path.
- Renderer adapter uses Copier; no Copier concepts leak into ports.
- Workspace adapter provides atomic staging + commit.
