#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]

SCHEMA_MAP = {
    "pack.schema.v1.json": "pack.schema.v1.md",
    "repo-lock.schema.v1.json": "repo-lock.schema.v1.md",
    "result.schema.v1.json": "result.schema.v1.md",
}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _md_escape(s: str) -> str:
    return s.replace("<", "&lt;").replace(">", "&gt;")


def _render_generated_notice(command: str) -> str:
    return "\n".join(
        [
            "> **Generated file. Do not edit directly.**",
            f"> Run: `{command}`",
        ]
    )


def _render_schema_overview(schema: dict[str, Any]) -> str:
    title = schema.get("title") or "Schema"
    desc = schema.get("description") or ""
    schema_id = schema.get("$id") or ""
    schema_version = schema.get("$schema") or ""

    lines: list[str] = []
    lines.append(f"# {_md_escape(title)}")
    if desc:
        lines.append("")
        lines.append(desc.strip())
    if schema_id or schema_version:
        lines.append("")
        if schema_id:
            lines.append(f"- **$id**: `{schema_id}`")
        if schema_version:
            lines.append(f"- **$schema**: `{schema_version}`")
    return "\n".join(lines)


def _render_properties(schema: dict[str, Any]) -> str:
    props: dict[str, Any] = schema.get("properties") or {}
    required: set[str] = set(schema.get("required") or [])

    if not props:
        return "## Properties\n\n(No top-level properties declared.)"

    lines: list[str] = []
    lines.append("## Properties")
    lines.append("")
    lines.append("| Name | Type | Required | Description |")
    lines.append("|---|---|---:|---|")

    for name in sorted(props.keys()):
        p = props[name] or {}
        p_type = p.get("type")
        if isinstance(p_type, list):
            type_str = " | ".join(str(t) for t in p_type)
        else:
            type_str = str(p_type) if p_type is not None else "(unspecified)"
        desc = (p.get("description") or "").strip().replace("\n", " ")
        lines.append(
            f"| `{name}` | `{type_str}` | {'yes' if name in required else 'no'} | {desc} |"
        )

    return "\n".join(lines)


def _render_raw(schema: dict[str, Any]) -> str:
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
