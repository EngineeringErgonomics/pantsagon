# Dependabot Configuration Design

**Date:** 2026-01-11

## Goal
Add Dependabot to keep GitHub Actions and Python dependencies up to date with a daily cadence, while controlling PR volume and keeping triage simple.

## Scope
- GitHub Actions workflow updates (from `.github/workflows`).
- Python dependencies for:
  - root `pyproject.toml` (`/`)
  - `3rdparty/python/requirements.txt`
  - `docs/requirements.txt`

## Non-Goals
- No custom ignore rules or security-only configuration.
- No auto-merge or external bot integrations.

## Design Decisions
1) **Single config file**: Use `.github/dependabot.yml` (version 2) with explicit update entries per ecosystem and directory.

2) **Daily cadence**: All updates run `interval: "daily"` per requirement.

3) **PR limits**:
   - `github-actions`: `open-pull-requests-limit: 5`
   - `pip`: `open-pull-requests-limit: 10`

4) **Grouping** (noise reduction):
   - Root `pip` entry groups runtime deps (typer, rich, pyyaml, tomli-w, jsonschema, copier) separately from dev tooling (pytest*).
   - `3rdparty/python` and `docs` entries group everything into a single PR per directory.

5) **Maintenance quality**:
   - `rebase-strategy: auto` to keep PRs current.
   - Labels for quick triage: `dependencies` everywhere; `ci` for Actions; `docs` for docs deps.

## Expected Outcome
Dependabot will open a bounded number of daily PRs for Actions and Python dependencies, grouped to minimize noise while still separating runtime versus dev tooling changes at the root.
