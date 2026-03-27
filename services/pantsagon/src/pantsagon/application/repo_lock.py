from __future__ import annotations

import tomllib
from pathlib import Path

from pantsagon.domain.diagnostics import Diagnostic, FileLocation, Severity
from pantsagon.domain.json_types import (
    JsonDict,
    JsonValue,
    as_json_dict,
    as_json_list,
)
from pantsagon.domain.result import Result

LockDict = JsonDict


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
        raw = as_json_dict(tomllib.loads(path.read_text(encoding="utf-8")))
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
    return Result(value=raw)


def _toml_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _toml_value(value: JsonValue) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return f'"{_toml_escape(value)}"'
    if isinstance(value, list):
        inner = ", ".join(_toml_value(item) for item in value)
        return f"[{inner}]"
    return f'"{_toml_escape(str(value))}"'


def _render_table(lines: list[str], name: str, mapping: JsonDict) -> None:
    lines.append(f"[{name}]")
    for key in sorted(mapping.keys()):
        lines.append(f"{key} = {_toml_value(mapping[key])}")
    lines.append("")


def _fallback_dumps(lock: LockDict) -> str:
    lines: list[str] = []
    settings = as_json_dict(lock.get("settings"))
    selection = as_json_dict(lock.get("selection"))
    resolved = as_json_dict(lock.get("resolved"))

    if settings:
        _render_table(lines, "settings", settings)
    if selection:
        _render_table(lines, "selection", selection)

    packs = resolved.get("packs")
    packs_list = as_json_list(packs)
    for pack in packs_list:
        if not isinstance(pack, dict):
            continue
        pack_dict = as_json_dict(pack)
        lines.append("[[resolved.packs]]")
        for key in ("id", "version", "source", "location", "ref", "digest"):
            if pack_dict.get(key) is not None:
                lines.append(f"{key} = {_toml_value(pack_dict[key])}")
        lines.append("")

    answers = as_json_dict(resolved.get("answers"))
    if answers:
        _render_table(lines, "resolved.answers", answers)

    return "\n".join(lines).rstrip() + "\n"


def write_lock(path: Path, lock: LockDict) -> None:
    try:
        import tomli_w

        payload: JsonDict = dict(lock)
        content = tomli_w.dumps(payload)
    except ModuleNotFoundError:
        content = _fallback_dumps(lock)
    path.write_text(content, encoding="utf-8")


def effective_strict(cli_strict: bool | None, lock: LockDict | None) -> bool:
    if cli_strict is not None:
        return cli_strict
    if lock is None:
        return False
    settings = as_json_dict(lock.get("settings"))
    return bool(settings.get("strict", False))


def project_reserved_services(lock: LockDict | None) -> set[str]:
    if not lock:
        return set()
    settings = as_json_dict(lock.get("settings"))
    naming = as_json_dict(settings.get("naming"))
    raw_reserved = naming.get("reserved_services")
    if isinstance(raw_reserved, list):
        return {str(item) for item in raw_reserved if item}
    return set()
