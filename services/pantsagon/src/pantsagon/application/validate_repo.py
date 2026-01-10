from pathlib import Path

from pantsagon.domain.diagnostics import Diagnostic, Severity
from pantsagon.domain.result import Result


def validate_repo(repo_path: Path) -> Result[None]:
    diagnostics: list[Diagnostic] = []
    lock_path = repo_path / ".pantsagon.toml"
    if not lock_path.exists():
        diagnostics.append(
            Diagnostic(
                code="LOCK_MISSING",
                rule="repo.lock.exists",
                severity=Severity.ERROR,
                message="Repo lock (.pantsagon.toml) is missing.",
                hint="Run `pantsagon init` to create a repo lock.",
            )
        )
    return Result(diagnostics=diagnostics)
