from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from pantsagon.domain.diagnostics import Diagnostic, Location
from pantsagon.domain.result import Result


def _serialize_location(location: Location | None) -> dict[str, Any] | None:
    if location is None:
        return None
    if is_dataclass(location):
        return asdict(location)
    return {"kind": getattr(location, "kind", "unknown")}


def serialize_diagnostic(diag: Diagnostic) -> dict[str, Any]:
    return {
        "id": diag.id,
        "code": diag.code,
        "rule": diag.rule,
        "severity": diag.severity.value,
        "message": diag.message,
        "hint": diag.hint,
        "details": diag.details,
        "is_execution": diag.is_execution,
        "location": _serialize_location(diag.location),
    }


def serialize_result(
    result: Result[Any],
    *,
    command: str,
    args: list[str],
) -> dict[str, Any]:
    return {
        "command": command,
        "args": args,
        "exit_code": result.exit_code,
        "diagnostics": [serialize_diagnostic(d) for d in result.diagnostics],
        "artifacts": result.artifacts,
    }
