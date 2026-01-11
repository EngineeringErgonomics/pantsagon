# Pantsagon

[![CI](https://github.com/EngineeringErgonomics/pantsagon/actions/workflows/ci.yml/badge.svg)](https://github.com/EngineeringErgonomics/pantsagon/actions/workflows/ci.yml) [![Docs](https://github.com/EngineeringErgonomics/pantsagon/actions/workflows/docs.yml/badge.svg)](https://github.com/EngineeringErgonomics/pantsagon/actions/workflows/docs.yml) [![Codecov](https://codecov.io/gh/EngineeringErgonomics/pantsagon/branch/main/graph/badge.svg)](https://codecov.io/gh/EngineeringErgonomics/pantsagon)

Hexagonal monorepos, generated with enforcement.

Pantsagon is a pack‑based scaffolding CLI for creating Pants‑managed monorepos that enforce hexagonal architecture (domain / application / adapters / entrypoints) from day one. It is designed for strict dependency boundaries, contract‑first APIs, and reproducible upgrades via versioned template packs.

Status: v1 baseline — `init` renders bundled packs into a minimal repo skeleton; `validate` checks repo locks + pack manifests; `add-service` currently validates naming/existence (scaffolding planned).

## Why Pantsagon

Monorepos fail in two predictable ways:

- “shared blob”: everything depends on everything
- “fake hexagonal”: directories exist but layering isn’t enforced

Pantsagon bakes hard boundaries into the bootstrap so services stay clean as they scale.

## What you get (v1)

- Pack‑based scaffolding with an explicit `pack.yaml` manifest + Copier templates
- Pack index resolution via `packs/_index.json` (languages/features → pack ids)
- Schema validation and manifest ↔ Copier cross‑checks
- Structured diagnostics + stable exit codes (`pantsagon validate --json`)
- Bundled packs: `core`, `python`, `openapi`, `docker` (minimal scaffolds)
- Pack validation tool: `python -m pantsagon.tools.validate_packs --bundled`
- Deterministic mode for tests (`PANTSAGON_DETERMINISTIC=1`)
- Optional augmented‑coding files (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`)

## Quick start (from source)

```bash
# inside this repo
python -m pip install -e .

# initialize a repo
pantsagon init /path/to/my-repo \
  --lang python \
  --services monitors,governance \
  --feature openapi \
  --feature docker
```

Notes:
- `init` renders bundled packs into a minimal skeleton and writes `.pantsagon.toml`.
- Bundled pack content is intentionally small and will expand toward fuller hexagonal scaffolds.

## Docs

Project docs live in `docs/` (MkDocs). To preview locally:

```bash
pip install -r docs/requirements.txt
python scripts/generate_schema_docs.py
mkdocs serve
```

## Repo lock (.pantsagon.toml)

The repo lock captures tool version, selection, and resolved packs/answers:

```toml
[tool]
name = "pantsagon"
version = "0.1.0"

[settings]
renderer = "copier"
strict = false
strict_manifest = true
allow_hooks = false

[selection]
languages = ["python"]
features = ["openapi", "docker"]
services = ["monitors", "governance"]
augmented_coding = "none"

[[resolved.packs]]
id = "pantsagon.core"
version = "1.0.0"
source = "bundled"

[resolved.answers]
repo_name = "my-repo"
service_name = "monitors"
```

## CLI (v1)

```bash
pantsagon init <repo> \
  --lang python \
  --services a,b \
  --feature openapi --feature docker \
  --augmented-coding {agents|claude|gemini|none}

pantsagon add-service <name> \
  --lang python \
  --strict

pantsagon validate --json --strict
```

Notes:
- `validate` returns non‑zero when `.pantsagon.toml` is missing.
- `--json` prints a structured Result payload.
- `add-service` currently validates naming/existence only; it does not render packs yet.

## Validation & strictness

Naming rules are enforced early, before filesystem writes:

- **Service names**: strict kebab-case, no leading/trailing or doubled dashes, and no reserved names.
- **Pack ids**: lowercase dot-namespaced identifiers (e.g. `pantsagon.core`).
- **Features**: lowercase kebab-case or snake_case (no dots).
- **Variables**: valid identifiers matching Copier variables.

Strictness tiers:

- `--strict` upgrades upgradeable warnings to errors.
- Repo defaults live in `.pantsagon.toml` under `[settings]` (CLI `--strict` overrides repo settings).
- Project-specific reserved service names can be added under `[settings.naming]` with `reserved_services = [...]`.

## Packs

A pack is a directory with:

```
pack.yaml   # tool‑agnostic manifest (authoritative)
copier.yml  # renderer config
templates/  # rendered files
```

Pantsagon validates:
- JSON Schema conformance (`shared/contracts/schemas/pack.schema.v1.json`)
- Manifest ↔ Copier variable alignment
- Bundled pack smoke-render validation (`python -m pantsagon.tools.validate_packs --bundled`)

Bundled packs live in `packs/`.

## Example generated tree

Example (Python + OpenAPI + Docker):

```
my-repo/
  pants.toml
  .pantsagon.toml
  .github/workflows/ci.yml
  services/
    monitor-cost/
      BUILD
      Dockerfile
      README.md
      src/monitor_cost/
        domain/
        ports/
        application/
        adapters/
        entrypoints/
  shared/
    foundation/
    adapters/
    contracts/
      openapi/
        monitor-cost.yaml
  docs/
    README.md
  tools/
    forbidden_imports/
      README.md
  3rdparty/
    python/
      requirements.txt
      BUILD
```

## Augmented coding files

If you pass `--augmented-coding`, Pantsagon creates a repo guidance file:

- `agents` → `AGENTS.md`
- `claude` → `CLAUDE.md`
- `gemini` → `GEMINI.md`

## Architecture (hexagonal core)

The core is split into:

- `domain/`: pure objects (`PackRef`, `Diagnostic`, `Result`)
- `application/`: use‑cases (`init`, `add service`, `validate`)
- `ports/`: contracts for pack catalog, renderer, workspace, policy, commands
- `adapters/`: implementations (Copier renderer, local/bundled packs, filesystem workspace)
- `entrypoints/`: CLI (Typer)

## Development

Run tests:

```bash
pytest -q
```

Pack validation:

```bash
PANTSAGON_DETERMINISTIC=1 PYTHONPATH=services/pantsagon/src \
  python -m pantsagon.tools.validate_packs --bundled --quiet
```

Notes:
- The Copier adapter test skips if Copier isn’t installed.
- You may see a pytest‑asyncio warning about default loop scope (safe to ignore for now).

## Roadmap (near‑term)

- Render pack templates for `add-service` (and update `.pantsagon.toml`)
- Git/registry pack sources + trust controls
- Expand bundled pack content toward full hexagonal scaffolds

## License

Apache License 2.0. See `LICENSE`.
