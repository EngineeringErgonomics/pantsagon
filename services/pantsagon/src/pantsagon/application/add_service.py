from pathlib import Path

from pantsagon.domain.diagnostics import Diagnostic, Severity
from pantsagon.domain.result import Result


_RESERVED = {"shared", "tools", "infra", "services", "packs", "docs", "schemas"}


def _is_kebab(name: str) -> bool:
    return name.islower() and all(part.isalnum() for part in name.split("-"))


def add_service(repo_path: Path, name: str, lang: str) -> Result[None]:
    if not _is_kebab(name) or name in _RESERVED:
        return Result(
            diagnostics=[
                Diagnostic(
                    code="SERVICE_NAME_INVALID",
                    rule="service.name",
                    severity=Severity.ERROR,
                    message="Invalid service name",
                )
            ]
        )
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
