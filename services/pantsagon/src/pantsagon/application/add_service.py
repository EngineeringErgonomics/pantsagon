from pathlib import Path

from pantsagon.domain.diagnostics import Diagnostic, Severity
from pantsagon.domain.result import Result


def add_service(repo_path: Path, name: str, lang: str) -> Result[None]:
    svc_dir = repo_path / "services" / name
    if svc_dir.exists():
        return Result(
            diagnostics=[
                Diagnostic(
                    code="SERVICE_EXISTS",
                    rule="service.name",
                    severity=Severity.ERROR,
                    message="Service already exists",
                )
            ]
        )
    return Result()
