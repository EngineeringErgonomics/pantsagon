# Quickstart

## Install Pantsagon

Recommended (isolated):
- `pipx install pantsagon`

## Create a repo

```bash
pantsagon init my-repo \
  --lang python \
  --services monitors,governance \
  --feature openapi \
  --feature docker
```

## Add a service

```bash
cd my-repo
pantsagon add service billing --lang python --feature docker
```

## Validate

```bash
pantsagon validate
pantsagon validate --exec
```

- `validate` checks structure and manifests
- `validate --exec` runs Pants goals (lint/check/test as configured)

See **CLI -> init** for full flags and semantics.
