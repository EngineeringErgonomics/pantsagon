from pathlib import Path

from pantsagon.domain.diagnostics import Diagnostic, Severity
from pantsagon.domain.result import Result


def validate_repo(repo_path: Path) -> Result[None]:
    lock = repo_path / ".pantsagon.toml"
    if not lock.exists():
        return Result(diagnostics=[
            Diagnostic(code="LOCK_MISSING", rule="lock.missing", severity=Severity.ERROR, message=".pantsagon.toml not found")
        ])
    return Result()
