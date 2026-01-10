# Pantsagon v1.0 Milestone Checklist

**Goal:** Reach a credible v1.0 release of Pantsagon with real pack rendering, complete CLI surface, and accurate docs.

## M0 — Documentation + Licensing Baseline
- [ ] README reflects current state and planned features
- [ ] README explicitly states Apache License 2.0 (not MIT)
- [ ] `LICENSE` confirmed as Apache 2.0

## M1 — Pack Rendering in `init` (Core Capability)
- [ ] Resolve pack selection: `core`, `python`, `openapi`, `docker`
- [ ] Validate pack schema + manifest↔Copier variables
- [ ] Render packs into staging dir via Copier
- [ ] Atomic commit to repo
- [ ] `.pantsagon.toml` written into staged output
- [ ] E2E test verifies real skeleton files
- [ ] README updated to reflect rendering behavior

## M2 — CLI Surface Complete
- [ ] `pantsagon add service` implemented (naming rules, idempotent)
- [ ] `pantsagon validate` implemented (schema + lock drift + cross‑check)
- [ ] JSON output contract implemented
- [ ] Exit code precedence enforced
- [ ] README updated with full CLI usage

## M3 — Repo Lock Fidelity
- [ ] `.pantsagon.toml` split into `[tool]`, `[selection]`, `[resolved]`, `[settings]`
- [ ] Persist pack refs (id/version/source + optional location/ref/digest)
- [ ] Persist resolved answers from Copier
- [ ] Validation detects lock drift
- [ ] README updated with lock structure

## M4 — Real Pack Content (Hexagonal Skeleton)
- [ ] `core` pack: repo layout, CI scaffold, shared foundation/adapters
- [ ] `python` pack: hex layers + BUILD rules
- [ ] `openapi` pack: contract scaffolding + openapi targets
- [ ] `docker` pack: Dockerfile + `docker_image` target
- [ ] Pack tests cover schema + cross‑check + render smoke‑test
- [ ] README updated with example tree

## M5 — Policy + Validation Hardening
- [ ] Naming rules: kebab‑case + reserved names
- [ ] Strictness tiers (`--strict` upgrades warnings → errors)
- [ ] Diagnostic codes + structured locations
- [ ] README updated with validation behavior

## M6 — CI + Release Readiness
- [ ] GitHub Actions runs pytest + pack validation
- [ ] Deterministic mode used in CI for reproducible tests
- [ ] Release checklist for v1.0.0
- [ ] README final pass
