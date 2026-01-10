from pathlib import Path
from typing import Any, Protocol

from pantsagon.domain.result import Result


class PolicyEnginePort(Protocol):
    def validate_repo(self, repo_path: Path) -> Result[None]: ...

    def validate_pack(self, pack_path: Path) -> Result[dict[str, Any]]: ...
