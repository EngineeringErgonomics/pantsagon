# Documentation contract

This page defines documentation requirements and rules for Pantsagon releases.

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

## Backlog

- Docs: remove PR preview versions from mike on PR close
