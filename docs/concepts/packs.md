# Packs

A pack is a versioned directory containing:

- `pack.yaml` - tool-agnostic manifest (authoritative)
- `copier.yml` - Copier rendering config
- `templates/` - template files

Pantsagon validates:

- `pack.yaml` against a JSON Schema
- `pack.yaml.variables` to `copier.yml` variable consistency

Packs can be bundled with Pantsagon or loaded from a local directory in v1.
