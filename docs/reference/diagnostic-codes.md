> **Generated file. Do not edit directly.**
> Run: `python scripts/generate_diagnostic_codes.py`

# Diagnostic codes

This page is generated from `services/pantsagon/src/pantsagon/diagnostics/codes.yaml`.

| Code | Severity | Rule | Message | Hint |
|---|---|---|---|---|
| `COPIER_DEFAULT_MISMATCH` | `warn` | `pack.variables.default_mismatch` | Copier default does not match pack.yaml default. | Align defaults, or run in strict mode to fail builds. |
| `COPIER_UNDECLARED_VARIABLE` | `error` | `pack.variables.copier_undeclared` | Copier defines a variable that is not declared in pack.yaml. | Declare it in pack.yaml.variables or remove it from copier.yml. |
| `FEATURE_NAME_INVALID` | `error` | `naming.feature.format` | Feature name format is invalid. | Use lowercase kebab-case or snake_case with no dots. |
| `FEATURE_NAME_SHADOWS_PACK` | `warn` | `naming.feature.shadows_pack` | Feature name shadows a pack id. | Rename the feature to avoid confusion with pack identifiers. |
| `INIT_PORTS_MISSING` | `error` | `init.ports` | Init requires renderer, pack catalog, policy engine, and workspace ports. | Ensure the entrypoint wires required adapters for init. |
| `LOCK_MISSING` | `error` | `lock.exists` | Repo lock file is missing. | Run pantsagon init or restore .pantsagon.toml. |
| `LOCK_PACK_DUPLICATE` | `error` | `lock.resolved.packs` | Repo lock contains duplicate pack entries. | Remove duplicate pack ids from resolved.packs. |
| `LOCK_PACK_INVALID` | `error` | `lock.resolved.packs` | Repo lock contains an invalid pack entry. | Ensure each pack has id, version, and source. |
| `LOCK_PARSE_FAILED` | `error` | `lock.parse` | Repo lock file could not be parsed. | Fix invalid TOML in .pantsagon.toml. |
| `LOCK_SECTION_MISSING` | `error` | `lock.section` | Repo lock is missing a required section. | Regenerate the repo lock or repair the missing section. |
| `LOCK_SELECTION_MISMATCH` | `warn` | `lock.selection` | Selection does not match resolved pack set. | Update selection or re-resolve packs to align. |
| `PACK_COMPAT_INVALID` | `error` | `pack.compatibility` | Pack compatibility metadata is invalid. | Ensure compatibility.pants is a string. |
| `PACK_FILE_MISSING` | `error` | `pack.files` | Pack is missing a required file. | Ensure pack.yaml and copier.yml exist in the pack directory. |
| `PACK_ID_INVALID` | `error` | `naming.pack.id` | Pack id format is invalid. | Use lowercase dot-namespaced ids (e.g. pantsagon.core). |
| `PACK_INDEX_UNKNOWN_FEATURE` | `error` | `pack.index.feature` | Selection feature is not defined in the pack index. | Add the feature mapping to packs/_index.json. |
| `PACK_INDEX_UNKNOWN_LANGUAGE` | `error` | `pack.index.language` | Selection language is not defined in the pack index. | Add the language mapping to packs/_index.json. |
| `PACK_LOCATION_MISSING` | `error` | `pack.catalog.fetch` | Local pack is missing a location. | Set location for local pack refs in the lock. |
| `PACK_MISSING_REQUIRED` | `error` | `pack.requires.packs` | Pack is missing required dependency packs. | Add the required pack or choose a compatible feature set. |
| `PACK_NOT_FOUND` | `error` | `pack.catalog.fetch` | Pack could not be found. | Check pack id/version and configured pack sources. |
| `PACK_RENDER_FAILED` | `error` | `pack.render` | Pack render failed. | Check Copier templates and inputs. |
| `REPO_LAYER_MISSING` | `error` | `repo.layer.exists` | Service layer directory is missing. | Regenerate the service skeleton or fix the layout. |
| `REPO_SERVICE_MISSING` | `error` | `repo.service.exists` | Service directory is missing for a declared service. | Regenerate the service or remove it from selection. |
| `SERVICE_NAME_INVALID` | `error` | `naming.service.format` | Service name format is invalid. | Use lowercase kebab-case without leading, trailing, or doubled dashes. |
| `SERVICE_NAME_RESERVED` | `error` | `naming.service.reserved` | Service name is reserved. | Choose a different name or add project-level reserved names in .pantsagon.toml. |
| `VARIABLE_NAME_INVALID` | `error` | `naming.variable.format` | Variable name format is invalid. | Use a valid identifier (letters, numbers, underscore) starting with a letter or underscore. |
