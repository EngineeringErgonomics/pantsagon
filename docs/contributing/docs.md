# Contributing to docs

Docs are part of the Pantsagon API surface. Keep them versioned and reproducible.

## Where to edit

- user docs live in `docs/`
- reference docs are generated from `shared/contracts/schemas/` and `services/pantsagon/src/pantsagon/diagnostics/codes.yaml`

## Edit links

Each page has an "Edit this page" link in the header.
If you are a pack author or plugin author, start in **Pack authoring** or **Plugin authoring**.

## Local workflow

```bash
pip install -r docs/requirements.txt
pip install pyyaml
python scripts/generate_schema_docs.py
python scripts/generate_diagnostic_codes.py
mkdocs serve
```

## Generated files

Generated reference docs must not be edited by hand.
Run the scripts above to update them.

## Publishing (CI)

Docs publish via GitHub Pages (GitHub Actions) in `.github/workflows/docs.yml`.

- `main` deploys `dev` and sets it as the default version
- tags deploy `vX.Y.Z`, update `latest`, and set the default to `latest`
- PRs run validation only (no published preview)

## Backlog

- Docs: if PR previews are reintroduced, add cleanup on PR close
