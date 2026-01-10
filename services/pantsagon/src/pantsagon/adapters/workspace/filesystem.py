from pathlib import Path
import shutil
import tempfile

from pantsagon.adapters.errors import WorkspaceCommitError


class FilesystemWorkspace:
    def __init__(self, root: Path) -> None:
        self.root = root

    def begin_transaction(self) -> Path:
        return Path(tempfile.mkdtemp(prefix="pantsagon-stage-", dir=self.root.parent))

    def commit(self, stage: Path) -> None:
        try:
            for path in stage.rglob("*"):
                rel = path.relative_to(stage)
                dest = self.root / rel
                if path.is_dir():
                    dest.mkdir(parents=True, exist_ok=True)
                else:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(path, dest)
        except Exception as e:
            raise WorkspaceCommitError("Workspace commit failed", cause=e)
        finally:
            shutil.rmtree(stage, ignore_errors=True)
