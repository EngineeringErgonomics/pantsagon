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

Start with **Getting started -> Quickstart**.

Looking to contribute? See **Contributing -> Docs**.
