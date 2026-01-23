#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


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

    codes = data.get("codes")
    if not isinstance(codes, list):
        raise SystemExit("Invalid codes.yaml: expected top-level 'codes' list")

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

    for item in sorted(codes, key=lambda x: (x.get("code") or "")):
        code = (item.get("code") or "").strip()
        sev = (item.get("severity") or "").strip()
        rule = (item.get("rule") or "").strip()
        msg = (item.get("message") or "").strip().replace("\n", " ")
        hint = (item.get("hint") or "").strip().replace("\n", " ")

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
