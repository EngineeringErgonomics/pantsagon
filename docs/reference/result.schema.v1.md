> **Generated file. Do not edit directly.**
> Run: `python scripts/generate_schema_docs.py`

# Pantsagon Result (v1)

Structured output returned by Pantsagon commands for humans and machines.

- **$id**: `https://pantsagon.dev/schemas/result.schema.v1.json`
- **$schema**: `https://json-schema.org/draft/2020-12/schema`

## Properties

| Name | Type | Required | Description |
|---|---|---:|---|
| `artifacts` | `array` | no | Artifacts produced by the command (paths, packs, commands). |
| `diagnostics` | `array` | yes | Structured diagnostics emitted during execution. |
| `exit_code` | `integer` | yes | Process exit code. |
| `result_schema_version` | `integer` | yes | Schema version for the Result object. |

## Raw JSON

```json
{
  "$id": "https://pantsagon.dev/schemas/result.schema.v1.json",
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "additionalProperties": false,
  "description": "Structured output returned by Pantsagon commands for humans and machines.",
  "properties": {
    "artifacts": {
      "description": "Artifacts produced by the command (paths, packs, commands).",
      "items": {
        "additionalProperties": true,
        "type": "object"
      },
      "type": "array"
    },
    "diagnostics": {
      "description": "Structured diagnostics emitted during execution.",
      "items": {
        "additionalProperties": false,
        "properties": {
          "code": {
            "description": "Short, stable diagnostic code (e.g. PACK_NOT_FOUND).",
            "type": "string"
          },
          "details": {
            "additionalProperties": true,
            "description": "Optional machine-readable details.",
            "type": "object"
          },
          "hint": {
            "description": "Optional remediation hint.",
            "type": "string"
          },
          "id": {
            "description": "Stable or deterministic diagnostic identifier.",
            "type": "string"
          },
          "location": {
            "additionalProperties": true,
            "description": "Optional structured location of the diagnostic.",
            "type": "object"
          },
          "message": {
            "type": "string"
          },
          "rule": {
            "description": "Rule identifier or namespace (e.g. pack.requires.packs).",
            "type": "string"
          },
          "severity": {
            "enum": [
              "error",
              "warn",
              "info"
            ],
            "type": "string"
          }
        },
        "required": [
          "code",
          "rule",
          "severity",
          "message"
        ],
        "type": "object"
      },
      "type": "array"
    },
    "exit_code": {
      "description": "Process exit code.",
      "enum": [
        0,
        2,
        3,
        4
      ],
      "type": "integer"
    },
    "result_schema_version": {
      "const": 1,
      "description": "Schema version for the Result object.",
      "type": "integer"
    }
  },
  "required": [
    "result_schema_version",
    "exit_code",
    "diagnostics"
  ],
  "title": "Pantsagon Result (v1)",
  "type": "object"
}
```

