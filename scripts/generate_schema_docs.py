#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import TypeGuard


REPO_ROOT = Path(__file__).resolve().parents[1]

SCHEMA_MAP = {
    "pack.schema.v1.json": "pack.schema.v1.md",
    "repo-lock.schema.v1.json": "repo-lock.schema.v1.md",
    "result.schema.v1.json": "result.schema.v1.md",
}


def _is_dict(value: object) -> TypeGuard[dict[object, object]]:
    return isinstance(value, dict)


def _is_list(value: object) -> TypeGuard[list[object]]:
    return isinstance(value, list)


def _as_dict(value: object) -> dict[str, object]:
    if not _is_dict(value):
        return {}
    return {str(k): v for k, v in value.items()}


def _as_list(value: object) -> list[object]:
    if not _is_list(value):
        return []
    return list(value)


def _load_json(path: Path) -> dict[str, object]:
    raw: object = json.loads(path.read_text(encoding="utf-8"))
    return _as_dict(raw)


def _md_escape(s: str) -> str:
    return s.replace("<", "&lt;").replace(">", "&gt;")


def _render_generated_notice(command: str) -> str:
    return "\n".join(
        [
            "> **Generated file. Do not edit directly.**",
            f"> Run: `{command}`",
        ]
    )


def _render_schema_overview(schema: dict[str, object]) -> str:
    title = str(schema.get("title") or "Schema")
    desc_raw = schema.get("description")
    desc = str(desc_raw).strip() if desc_raw else ""
    schema_id = str(schema.get("$id") or "")
    schema_version = str(schema.get("$schema") or "")

    lines: list[str] = []
    lines.append(f"# {_md_escape(title)}")
    if desc:
        lines.append("")
        lines.append(desc)
    if schema_id or schema_version:
        lines.append("")
        if schema_id:
            lines.append(f"- **$id**: `{schema_id}`")
        if schema_version:
            lines.append(f"- **$schema**: `{schema_version}`")
    return "\n".join(lines)


def _render_properties(schema: dict[str, object]) -> str:
    raw_props = schema.get("properties")
    props = _as_dict(raw_props)
    raw_required = schema.get("required")
    required_items = _as_list(raw_required)
    required: set[str] = {str(item) for item in required_items}

    if not props:
        return "## Properties\n\n(No top-level properties declared.)"

    lines: list[str] = []
    lines.append("## Properties")
    lines.append("")
    lines.append("| Name | Type | Required | Description |")
    lines.append("|---|---|---:|---|")

    for name in sorted(props.keys()):
        raw_prop = props[name]
        p = _as_dict(raw_prop)
        p_type = p.get("type")
        type_items = _as_list(p_type)
        if type_items:
            type_str = " | ".join(str(t) for t in type_items)
        elif isinstance(p_type, list):
            type_str = "(unspecified)"
        else:
            type_str = str(p_type) if p_type is not None else "(unspecified)"
        desc = str(p.get("description") or "").strip().replace("\n", " ")
        lines.append(
            f"| `{name}` | `{type_str}` | {'yes' if name in required else 'no'} | {desc} |"
        )

    return "\n".join(lines)


def _render_raw(schema: dict[str, object]) -> str:
    pretty = json.dumps(schema, indent=2, sort_keys=True)
    return "## Raw JSON\n\n```json\n" + pretty + "\n```\n"


def generate(repo_root: Path = REPO_ROOT) -> None:
    schemas_dir = repo_root / "schemas"
    shared_schemas_dir = repo_root / "shared" / "contracts" / "schemas"
    out_dir = repo_root / "docs" / "reference"
    out_dir.mkdir(parents=True, exist_ok=True)

    for in_name, out_name in SCHEMA_MAP.items():
        in_path: Path | None = None
        for base in (schemas_dir, shared_schemas_dir):
            candidate = base / in_name
            if candidate.exists():
                in_path = candidate
                break
        if in_path is None:
            raise SystemExit(
                f"Schema file not found in {schemas_dir} or {shared_schemas_dir}: {in_name}"
            )

        schema = _load_json(in_path)
        md = "\n\n".join(
            [
                _render_generated_notice("python scripts/generate_schema_docs.py"),
                _render_schema_overview(schema),
                _render_properties(schema),
                _render_raw(schema),
            ]
        )
        out_path = out_dir / out_name
        out_path.write_text(md + "\n", encoding="utf-8")

    print(f"Generated schema docs into {out_dir}")


if __name__ == "__main__":
    generate()
