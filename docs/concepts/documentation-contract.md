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
- `latest` - alias for the newest release (updated on tags)
- `vX.Y.Z` - tagged releases

PR builds validate docs but do not publish previews.

## Publishing (CI)

Docs are published via GitHub Pages (GitHub Actions) in `.github/workflows/docs.yml`.

- `main` deploys `dev` and sets it as the default version
- tags deploy `vX.Y.Z`, update `latest`, and set the default to `latest`
- mike writes versioned output to the `gh-pages` branch, which is then deployed via Pages

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

- Docs: if PR previews are reintroduced, add cleanup on PR close
