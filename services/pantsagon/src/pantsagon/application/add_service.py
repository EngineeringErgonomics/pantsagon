from pathlib import Path

from pantsagon.application.repo_lock import effective_strict, project_reserved_services, read_lock
from pantsagon.domain.diagnostics import Diagnostic, Severity
from pantsagon.domain.naming import BUILTIN_RESERVED_SERVICES, validate_service_name
from pantsagon.domain.result import Result
from pantsagon.domain.strictness import apply_strictness


def add_service(repo_path: Path, name: str, lang: str, strict: bool | None = None) -> Result[None]:
    diagnostics = []
    lock_result = read_lock(repo_path / ".pantsagon.toml")
    diagnostics.extend(lock_result.diagnostics)
    lock = lock_result.value
    if lock is None:
        return Result(diagnostics=apply_strictness(diagnostics, effective_strict(strict, lock)))

    diagnostics.extend(
        validate_service_name(name, BUILTIN_RESERVED_SERVICES, project_reserved_services(lock))
    )
    if any(d.severity == Severity.ERROR for d in diagnostics):
        return Result(diagnostics=apply_strictness(diagnostics, effective_strict(strict, lock)))
    svc_dir = repo_path / "services" / name
    if svc_dir.exists():
        diagnostics.append(
            Diagnostic(
                code="SERVICE_EXISTS",
                rule="service.name",
                severity=Severity.ERROR,
                message="Service already exists",
            )
        )
    return Result(diagnostics=apply_strictness(diagnostics, effective_strict(strict, lock)))
