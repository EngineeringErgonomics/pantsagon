> **Generated file. Do not edit directly.**
> Run: `python scripts/generate_diagnostic_codes.py`

# Diagnostic codes

This page is generated from `pantsagon/diagnostics/codes.yaml`.

| Code | Severity | Rule | Message | Hint |
|---|---|---|---|---|
| `COPIER_DEFAULT_MISMATCH` | `warn` | `pack.variables.default_mismatch` | Copier default does not match pack.yaml default. | Align defaults, or run in strict mode to fail builds. |
| `COPIER_UNDECLARED_VARIABLE` | `error` | `pack.variables.copier_undeclared` | Copier defines a variable that is not declared in pack.yaml. | Declare it in pack.yaml.variables or remove it from copier.yml. |
| `FEATURE_NAME_INVALID` | `error` | `naming.feature.format` | Feature name format is invalid. | Use lowercase kebab-case or snake_case with no dots. |
| `FEATURE_NAME_SHADOWS_PACK` | `warn` | `naming.feature.shadows_pack` | Feature name shadows a pack id. | Rename the feature to avoid confusion with pack identifiers. |
| `LOCK_INVALID` | `error` | `repo.lock.invalid` | Repo lock (.pantsagon.toml) is invalid. | Fix the TOML syntax or regenerate the repo lock with init. |
| `LOCK_MISSING` | `error` | `repo.lock.missing` | Repo lock (.pantsagon.toml) is missing. | Run init to create a new repo lock file. |
| `PACK_ID_INVALID` | `error` | `naming.pack.id` | Pack id format is invalid. | Use lowercase dot-namespaced ids (e.g. pantsagon.core). |
| `PACK_MISSING_REQUIRED` | `error` | `pack.requires.packs` | Pack is missing required dependency packs. | Add the required pack or choose a compatible feature set. |
| `PACK_NOT_FOUND` | `error` | `pack.catalog.fetch` | Pack could not be found. | Check pack id/version and configured pack sources. |
| `SERVICE_NAME_INVALID` | `error` | `naming.service.format` | Service name format is invalid. | Use lowercase kebab-case without leading, trailing, or doubled dashes. |
| `SERVICE_NAME_RESERVED` | `error` | `naming.service.reserved` | Service name is reserved. | Choose a different name or add project-level reserved names in .pantsagon.toml. |
| `VARIABLE_NAME_INVALID` | `error` | `naming.variable.format` | Variable name format is invalid. | Use a valid identifier (letters, numbers, underscore) starting with a letter or underscore. |
