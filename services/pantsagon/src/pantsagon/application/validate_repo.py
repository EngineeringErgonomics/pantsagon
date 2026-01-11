from pathlib import Path

from pantsagon.application.repo_lock import effective_strict, load_repo_lock
from pantsagon.domain.result import Result
from pantsagon.domain.strictness import apply_strictness


def validate_repo(repo_path: Path, strict: bool | None = None) -> Result[None]:
    diagnostics = []

    # Phase 1: lock + settings validation
    lock, lock_diags = load_repo_lock(repo_path)
    diagnostics.extend(lock_diags)
    if lock is None:
        return Result(diagnostics=apply_strictness(diagnostics, effective_strict(strict, lock)))

    # Phase 2: pack validation (to be wired later)
    # Phase 3: repo structure & collision checks (to be wired later)

    return Result(diagnostics=apply_strictness(diagnostics, effective_strict(strict, lock)))
