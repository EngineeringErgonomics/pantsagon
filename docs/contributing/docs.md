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

## Backlog

- Docs: remove PR preview versions from mike on PR close
