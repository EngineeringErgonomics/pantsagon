> **Generated file. Do not edit directly.**
> Run: `python scripts/generate_schema_docs.py`

# Pantsagon Repo Lock (.pantsagon.toml) (v1)

Single source of truth for a Pantsagon-generated repository.

- **$id**: `https://pantsagon.dev/schemas/repo-lock.schema.v1.json`
- **$schema**: `https://json-schema.org/draft/2020-12/schema`

## Properties

| Name | Type | Required | Description |
|---|---|---:|---|
| `resolved` | `object` | yes |  |
| `selection` | `object` | no |  |
| `settings` | `object` | no |  |
| `tool` | `object` | yes |  |

## Raw JSON

```json
{
  "$id": "https://pantsagon.dev/schemas/repo-lock.schema.v1.json",
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "additionalProperties": false,
  "description": "Single source of truth for a Pantsagon-generated repository.",
  "properties": {
    "resolved": {
      "additionalProperties": false,
      "properties": {
        "answers": {
          "additionalProperties": true,
          "description": "Resolved variable answers passed to the renderer.",
          "type": "object"
        },
        "packs": {
          "items": {
            "additionalProperties": false,
            "properties": {
              "id": {
                "type": "string"
              },
              "location": {
                "description": "Filesystem path or URL, depending on source.",
                "type": "string"
              },
              "ref": {
                "description": "Git ref, commit, or registry digest.",
                "type": "string"
              },
              "source": {
                "enum": [
                  "bundled",
                  "local",
                  "git",
                  "registry"
                ],
                "type": "string"
              },
              "version": {
                "type": "string"
              }
            },
            "required": [
              "id",
              "version",
              "source"
            ],
            "type": "object"
          },
          "type": "array"
        }
      },
      "required": [
        "packs"
      ],
      "type": "object"
    },
    "selection": {
      "additionalProperties": false,
      "properties": {
        "features": {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        "languages": {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        "services": {
          "items": {
            "pattern": "^[a-z](?:[a-z0-9]*(-[a-z0-9]+)*)$",
            "type": "string"
          },
          "type": "array"
        }
      },
      "type": "object"
    },
    "settings": {
      "additionalProperties": false,
      "properties": {
        "allow_hooks": {
          "default": false,
          "description": "Whether pack hooks are allowed to execute.",
          "type": "boolean"
        },
        "naming": {
          "additionalProperties": false,
          "properties": {
            "reserved_services": {
              "description": "Project-specific additional reserved service names.",
              "items": {
                "type": "string"
              },
              "type": "array"
            }
          },
          "type": "object"
        },
        "renderer": {
          "default": "copier",
          "description": "Renderer adapter to use.",
          "type": "string"
        },
        "strict": {
          "default": false,
          "description": "Whether strict mode is enabled.",
          "type": "boolean"
        },
        "strict_manifest": {
          "default": true,
          "description": "Whether manifest/Copier mismatches are fatal.",
          "type": "boolean"
        }
      },
      "type": "object"
    },
    "tool": {
      "additionalProperties": false,
      "properties": {
        "name": {
          "const": "pantsagon",
          "type": "string"
        },
        "version": {
          "description": "Pantsagon tool version used to generate or update this repo.",
          "type": "string"
        }
      },
      "required": [
        "name",
        "version"
      ],
      "type": "object"
    }
  },
  "required": [
    "tool",
    "resolved"
  ],
  "title": "Pantsagon Repo Lock (.pantsagon.toml) (v1)",
  "type": "object"
}
```

