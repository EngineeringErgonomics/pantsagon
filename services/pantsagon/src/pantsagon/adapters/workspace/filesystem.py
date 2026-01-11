from pathlib import Path
import shutil
import tempfile

from pantsagon.adapters.errors import WorkspaceCommitError


class FilesystemWorkspace:
    def __init__(self, root: Path) -> None:
        self.root = root

    def _copy_file(self, src: Path, dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)

    def begin_transaction(self) -> Path:
        return Path(tempfile.mkdtemp(prefix="pantsagon-stage-", dir=self.root.parent))

    def commit(self, stage: Path) -> None:
        created_files: list[Path] = []
        created_dirs: list[Path] = []
        try:
            for path in stage.rglob("*"):
                rel = path.relative_to(stage)
                dest = self.root / rel
                if path.is_dir():
                    if not dest.exists():
                        dest.mkdir(parents=True, exist_ok=True)
                        created_dirs.append(dest)
                else:
                    if not dest.parent.exists():
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        created_dirs.append(dest.parent)
                    self._copy_file(path, dest)
                    created_files.append(dest)
        except Exception as e:
            for created in created_files:
                if created.exists():
                    created.unlink()
            for created_dir in sorted(created_dirs, reverse=True):
                if created_dir.exists():
                    try:
                        created_dir.rmdir()
                    except OSError:
                        pass
            raise WorkspaceCommitError("Workspace commit failed", cause=e)
        finally:
            shutil.rmtree(stage, ignore_errors=True)
