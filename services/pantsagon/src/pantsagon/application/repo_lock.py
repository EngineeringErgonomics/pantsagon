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


def write_lock(path: Path, lock: LockDict) -> None:
    import tomli_w

    content = tomli_w.dumps(lock)
    path.write_text(content, encoding="utf-8")
