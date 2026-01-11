from pathlib import Path
import shutil
import tempfile

from pantsagon.adapters.errors import WorkspaceCommitError


class FilesystemWorkspace:
    def _copy_file(self, src: Path, dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)


    def __init__(self, root: Path) -> None:
        self.root = root

    def begin_transaction(self) -> Path:
        return Path(tempfile.mkdtemp(prefix="pantsagon-stage-", dir=self.root.parent))

    def commit(self, stage: Path) -> None:
        created: list[Path] = []
        try:
            for path in stage.rglob("*"):
                rel = path.relative_to(stage)
                dest = self.root / rel
                if path.is_dir():
                    if not dest.exists():
                        dest.mkdir(parents=True, exist_ok=True)
                        created.append(dest)
                else:
                    self._copy_file(path, dest)
                    created.append(dest)
        except Exception as e:
            for dest in reversed(created):
                try:
                    if dest.is_file():
                        dest.unlink(missing_ok=True)
                    elif dest.is_dir():
                        dest.rmdir()
                except Exception:
                    pass
            raise WorkspaceCommitError("Workspace commit failed", cause=e)
        finally:
            shutil.rmtree(stage, ignore_errors=True)
