# Pack authoring

Packs are the primary extension mechanism.

A pack contains:

- `pack.yaml` (authoritative manifest)
- `copier.yml` (renderer config)
- `templates/`

Pantsagon enforces:

- schema validation
- manifest to copier variable cross-check
- render smoke-test (for bundled packs)
