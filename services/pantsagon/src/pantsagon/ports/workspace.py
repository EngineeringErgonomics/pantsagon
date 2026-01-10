from pathlib import Path
from typing import Protocol


class WorkspacePort(Protocol):
    def begin_transaction(self) -> Path: ...
    def commit(self, stage: Path) -> None: ...
