from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from typing import TypeVar

from pantsagon.domain.diagnostics import Diagnostic, Location
from pantsagon.domain.json_types import JsonDict, as_json_dict
from pantsagon.domain.result import Result

T = TypeVar("T")


def _serialize_location(location: Location | None) -> JsonDict | None:
    if location is None:
        return None
    if is_dataclass(location):
        return as_json_dict(asdict(location))
    return as_json_dict({"kind": str(getattr(location, "kind", "unknown"))})


def serialize_diagnostic(diag: Diagnostic) -> JsonDict:
    return as_json_dict(
        {
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
    )


def serialize_result(
    result: Result[T],
    command: str,
    args: list[str],
) -> JsonDict:
    return as_json_dict(
        {
            "result_schema_version": 1,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "command": command,
            "args": args,
            "exit_code": result.exit_code,
            "diagnostics": [serialize_diagnostic(d) for d in result.diagnostics],
            "artifacts": result.artifacts,
        }
    )
