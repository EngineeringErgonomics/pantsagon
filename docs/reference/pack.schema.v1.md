> **Generated file. Do not edit directly.**
> Run: `python scripts/generate_schema_docs.py`

# Pantsagon Pack Manifest (v1)

Tool-agnostic manifest describing a Pantsagon pack: identity, compatibility, features, and variables.

- **$id**: `https://pantsagon.dev/schemas/pack.schema.v1.json`
- **$schema**: `https://json-schema.org/draft/2020-12/schema`

## Properties

| Name | Type | Required | Description |
|---|---|---:|---|
| `compatibility` | `object` | yes |  |
| `description` | `string` | no | Human-readable description of the pack. |
| `id` | `string` | yes | Globally unique pack identifier (e.g. pantsagon.python). |
| `provides` | `object` | no |  |
| `requires` | `object` | no |  |
| `schema_version` | `integer` | no | Schema version for this manifest. |
| `variables` | `array` | no | Variables required or accepted by this pack. |
| `version` | `string` | yes | SemVer version of the pack. |

## Raw JSON

```json
{
  "$id": "https://pantsagon.dev/schemas/pack.schema.v1.json",
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "additionalProperties": false,
  "description": "Tool-agnostic manifest describing a Pantsagon pack: identity, compatibility, features, and variables.",
  "properties": {
    "compatibility": {
      "additionalProperties": false,
      "properties": {
        "languages": {
          "additionalProperties": {
            "description": "Supported version range for a language (e.g. python: \">=3.12,<3.15\").",
            "type": "string"
          },
          "type": "object"
        },
        "pants": {
          "description": "Supported Pants version range (PEP 440 / semver-style range).",
          "type": "string"
        }
      },
      "required": [
        "pants"
      ],
      "type": "object"
    },
    "description": {
      "description": "Human-readable description of the pack.",
      "type": "string"
    },
    "id": {
      "description": "Globally unique pack identifier (e.g. pantsagon.python).",
      "pattern": "^[a-z0-9_.-]+$",
      "type": "string"
    },
    "provides": {
      "additionalProperties": false,
      "properties": {
        "features": {
          "description": "Feature flags provided by this pack (e.g. openapi, docker).",
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        "service_templates": {
          "description": "Service template capabilities exposed by this pack.",
          "items": {
            "additionalProperties": false,
            "properties": {
              "kind": {
                "description": "Template kind.",
                "enum": [
                  "service"
                ],
                "type": "string"
              },
              "language": {
                "description": "Language supported by this template.",
                "type": "string"
              },
              "layout": {
                "description": "Declared layout (e.g. hexagonal).",
                "type": "string"
              }
            },
            "required": [
              "kind",
              "language"
            ],
            "type": "object"
          },
          "type": "array"
        }
      },
      "type": "object"
    },
    "requires": {
      "additionalProperties": false,
      "properties": {
        "packs": {
          "description": "Other packs that must be present for this pack to be applied.",
          "items": {
            "pattern": "^[a-z0-9_.-]+$",
            "type": "string"
          },
          "type": "array"
        }
      },
      "type": "object"
    },
    "schema_version": {
      "const": 1,
      "description": "Schema version for this manifest.",
      "type": "integer"
    },
    "variables": {
      "description": "Variables required or accepted by this pack.",
      "items": {
        "additionalProperties": false,
        "properties": {
          "default": {
            "description": "Default value if not provided."
          },
          "enum": {
            "description": "Allowed values when type is enum.",
            "items": {
              "type": "string"
            },
            "type": "array"
          },
          "name": {
            "description": "Variable name.",
            "pattern": "^[a-zA-Z_][a-zA-Z0-9_]*$",
            "type": "string"
          },
          "required": {
            "default": false,
            "description": "Whether the variable is required.",
            "type": "boolean"
          },
          "type": {
            "description": "Variable type.",
            "enum": [
              "string",
              "int",
              "bool",
              "enum"
            ],
            "type": "string"
          }
        },
        "required": [
          "name",
          "type"
        ],
        "type": "object"
      },
      "type": "array"
    },
    "version": {
      "description": "SemVer version of the pack.",
      "pattern": "^\\d+\\.\\d+\\.\\d+$",
      "type": "string"
    }
  },
  "required": [
    "id",
    "version",
    "compatibility"
  ],
  "title": "Pantsagon Pack Manifest (v1)",
  "type": "object"
}
```

