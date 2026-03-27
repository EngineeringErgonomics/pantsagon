#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from typing import TypeGuard

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]


def _is_dict(value: object) -> TypeGuard[dict[object, object]]:
    return isinstance(value, dict)


def _is_list(value: object) -> TypeGuard[list[object]]:
    return isinstance(value, list)


def _as_dict(value: object) -> dict[str, object]:
    if not _is_dict(value):
        return {}
    return {str(k): v for k, v in value.items()}


def _load_yaml(path: Path) -> dict[str, object]:
    raw: object = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return _as_dict(raw)


def _render_generated_notice(command: str) -> str:
    return "\n".join(
        [
            "> **Generated file. Do not edit directly.**",
            f"> Run: `{command}`",
        ]
    )


def generate(repo_root: Path = REPO_ROOT) -> None:
    src = (
        repo_root
        / "services"
        / "pantsagon"
        / "src"
        / "pantsagon"
        / "diagnostics"
        / "codes.yaml"
    )
    out = repo_root / "docs" / "reference" / "diagnostic-codes.md"

    if not src.exists():
        raise SystemExit(f"Diagnostics source not found: {src}")

    data = _load_yaml(src)
    if data.get("version") != 1:
        raise SystemExit(f"Unsupported diagnostics version: {data.get('version')}")

    raw_codes = data.get("codes")
    if not _is_list(raw_codes):
        raise SystemExit("Invalid codes.yaml: expected top-level 'codes' list")
    codes: list[dict[str, object]] = []
    for entry in raw_codes:
        if not _is_dict(entry):
            raise SystemExit("Invalid codes.yaml: entries must be mappings")
        codes.append(_as_dict(entry))

    lines: list[str] = []
    lines.append(
        _render_generated_notice("python scripts/generate_diagnostic_codes.py")
    )
    lines.append("")
    lines.append("# Diagnostic codes")
    lines.append("")
    lines.append(
        "This page is generated from "
        "`services/pantsagon/src/pantsagon/diagnostics/codes.yaml`."
    )
    lines.append("")
    lines.append("| Code | Severity | Rule | Message | Hint |")
    lines.append("|---|---|---|---|---|")

    for item in sorted(codes, key=lambda x: str(x.get("code", ""))):
        code = str(item.get("code") or "").strip()
        sev = str(item.get("severity") or "").strip()
        rule = str(item.get("rule") or "").strip()
        msg = str(item.get("message") or "").strip().replace("\n", " ")
        hint = str(item.get("hint") or "").strip().replace("\n", " ")

        if not code or not sev or not rule:
            raise SystemExit(
                f"Invalid diagnostic entry (missing required fields): {item}"
            )

        lines.append(f"| `{code}` | `{sev}` | `{rule}` | {msg} | {hint} |")

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Generated {out}")


if __name__ == "__main__":
    generate()
