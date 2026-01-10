# Pantsagon

Hexagonal monorepos, generated with enforcement.

Pantsagon is a pack‑based scaffolding CLI for creating Pants‑managed monorepos that enforce hexagonal architecture (domain / application / adapters / entrypoints) from day one. It is designed for strict dependency boundaries, contract‑first APIs, and reproducible upgrades via versioned template packs.

Status: early v0.1 — core scaffolding + pack validation are in place; full pack rendering is in progress.

## Why Pantsagon

Monorepos fail in two predictable ways:

- “shared blob”: everything depends on everything
- “fake hexagonal”: directories exist but layering isn’t enforced

Pantsagon bakes hard boundaries into the bootstrap so services stay clean as they scale.

## What you get (v0.1)

- Pack‑based scaffolding with an explicit `pack.yaml` manifest + Copier templates
- Schema validation and manifest ↔ Copier cross‑checks
- Bundled packs: `core`, `python`, `openapi`, `docker` (minimal scaffolds)
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
- `init` currently writes a minimal `.pantsagon.toml` and `pants.toml` placeholder.
- Pack rendering is the next milestone (Copier adapter is already wired).

## CLI (v0.1)

```bash
pantsagon init <repo> \
  --lang python \
  --services a,b \
  --feature openapi --feature docker \
  --augmented-coding {agents|claude|gemini|none}

pantsagon add_service <name> \
  --lang python

pantsagon validate --json
```

Notes:
- `validate` returns non‑zero when `.pantsagon.toml` is missing.
- `--json` prints a structured Result payload.

## Packs

A pack is a directory with:

```
pack.yaml   # tool‑agnostic manifest (authoritative)
copier.yml  # renderer config
templates/  # rendered files
```

Pantsagon validates:
- JSON Schema conformance (`schemas/pack.schema.v1.json`)
- Manifest ↔ Copier variable alignment

Bundled packs live in `packs/`.

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

Notes:
- The Copier adapter test skips if Copier isn’t installed.
- You may see a pytest‑asyncio warning about default loop scope (safe to ignore for now).

## Roadmap (near‑term)

- Render packs during `init` (Copier integration)
- `add service` and `validate` commands
- Pack smoke‑test command for pack authors
- Git/registry pack sources + trust controls

## License

MIT. See `LICENSE`.
