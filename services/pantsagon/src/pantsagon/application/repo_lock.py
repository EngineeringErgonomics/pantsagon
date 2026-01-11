from __future__ import annotations

from pathlib import Path
import tomllib
from typing import Any

from pantsagon.domain.diagnostics import Diagnostic, FileLocation, Severity
from pantsagon.domain.result import Result

LockDict = dict[str, Any]


def read_lock(path: Path) -> Result[LockDict]:
    if not path.exists():
        return Result(
            diagnostics=[
                Diagnostic(
                    code="LOCK_MISSING",
                    rule="lock.exists",
                    severity=Severity.ERROR,
                    message=".pantsagon.toml not found",
                )
            ]
        )
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return Result(
            diagnostics=[
                Diagnostic(
                    code="LOCK_PARSE_FAILED",
                    rule="lock.parse",
                    severity=Severity.ERROR,
                    message=str(e),
                    location=FileLocation(str(path)),
                )
            ]
        )
    return Result(value=data)


def _toml_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\"", "\\\"")


def _toml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return f"\"{_toml_escape(value)}\""
    if isinstance(value, list):
        inner = ", ".join(_toml_value(item) for item in value)
        return f"[{inner}]"
    return f"\"{_toml_escape(str(value))}\""


def _render_table(lines: list[str], name: str, mapping: dict[str, Any]) -> None:
    lines.append(f"[{name}]")
    for key in sorted(mapping.keys()):
        lines.append(f"{key} = {_toml_value(mapping[key])}")
    lines.append("")


def _fallback_dumps(lock: LockDict) -> str:
    lines: list[str] = []
    tool = lock.get("tool", {}) if isinstance(lock.get("tool"), dict) else {}
    settings = lock.get("settings", {}) if isinstance(lock.get("settings"), dict) else {}
    selection = lock.get("selection", {}) if isinstance(lock.get("selection"), dict) else {}
    resolved = lock.get("resolved", {}) if isinstance(lock.get("resolved"), dict) else {}

    _render_table(lines, "tool", tool)
    if settings:
        _render_table(lines, "settings", settings)
    if selection:
        _render_table(lines, "selection", selection)

    packs = resolved.get("packs") if isinstance(resolved.get("packs"), list) else []
    for pack in packs:
        if not isinstance(pack, dict):
            continue
        lines.append("[[resolved.packs]]")
        for key in ("id", "version", "source", "location", "ref", "digest"):
            if pack.get(key) is not None:
                lines.append(f"{key} = {_toml_value(pack[key])}")
        lines.append("")

    answers = resolved.get("answers") if isinstance(resolved.get("answers"), dict) else {}
    if answers:
        _render_table(lines, "resolved.answers", answers)

    return "\n".join(lines).rstrip() + "\n"


def write_lock(path: Path, lock: LockDict) -> None:
    try:
        import tomli_w
        content = tomli_w.dumps(lock)
    except ModuleNotFoundError:
        content = _fallback_dumps(lock)
    path.write_text(content, encoding="utf-8")
