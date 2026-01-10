from __future__ import annotations

import tomllib
from pathlib import Path

from pantsagon.domain.diagnostics import Diagnostic, FileLocation, Severity


def load_repo_lock(repo_path: Path) -> tuple[dict | None, list[Diagnostic]]:
    lock_path = repo_path / ".pantsagon.toml"
    if not lock_path.exists():
        return (
            None,
            [
                Diagnostic(
                    code="LOCK_MISSING",
                    rule="repo.lock.missing",
                    severity=Severity.ERROR,
                    message="Missing .pantsagon.toml",
                    location=FileLocation(str(lock_path)),
                )
            ],
        )
    try:
        return tomllib.loads(lock_path.read_text()), []
    except Exception as e:
        return (
            None,
            [
                Diagnostic(
                    code="LOCK_INVALID",
                    rule="repo.lock.invalid",
                    severity=Severity.ERROR,
                    message=f"Invalid .pantsagon.toml: {e}",
                    location=FileLocation(str(lock_path)),
                )
            ],
        )


def effective_strict(cli_strict: bool | None, lock: dict | None) -> bool:
    if cli_strict is not None:
        return cli_strict
    if lock is None:
        return False
    return bool(lock.get("settings", {}).get("strict", False))


def project_reserved_services(lock: dict | None) -> set[str]:
    if not lock:
        return set()
    naming = lock.get("settings", {}).get("naming", {})
    return set(naming.get("reserved_services", []) or [])
