from datetime import datetime, timezone

from pantsagon.domain.diagnostics import FileLocation
from pantsagon.domain.result import Result


def _serialize_location(loc):
    if loc is None:
        return None
    data = {"kind": loc.kind}
    if isinstance(loc, FileLocation):
        data.update({"path": loc.path, "line": loc.line, "col": loc.col})
    return data


def serialize_result(result: Result, command: str, args: list[str]) -> dict:
    return {
        "result_schema_version": 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "command": command,
        "args": args,
        "exit_code": result.exit_code,
        "diagnostics": [
            {
                "id": d.id,
                "code": d.code,
                "rule": d.rule,
                "severity": d.severity.value,
                "message": d.message,
                "location": _serialize_location(d.location),
                "hint": d.hint,
                "details": d.details,
                "is_execution": d.is_execution,
            }
            for d in result.diagnostics
        ],
        "artifacts": result.artifacts,
    }
