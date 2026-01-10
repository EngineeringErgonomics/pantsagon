> **Generated file. Do not edit directly.**
> Run: `python scripts/generate_diagnostic_codes.py`

# Diagnostic codes

This page is generated from `pantsagon/diagnostics/codes.yaml`.

| Code | Severity | Rule | Message | Hint |
|---|---|---|---|---|
| `COPIER_DEFAULT_MISMATCH` | `warn` | `pack.variables.default_mismatch` | Copier default does not match pack.yaml default. | Align defaults, or run in strict mode to fail builds. |
| `COPIER_UNDECLARED_VARIABLE` | `error` | `pack.variables.copier_undeclared` | Copier defines a variable that is not declared in pack.yaml. | Declare it in pack.yaml.variables or remove it from copier.yml. |
| `PACK_MISSING_REQUIRED` | `error` | `pack.requires.packs` | Pack is missing required dependency packs. | Add the required pack or choose a compatible feature set. |
| `PACK_NOT_FOUND` | `error` | `pack.catalog.fetch` | Pack could not be found. | Check pack id/version and configured pack sources. |
