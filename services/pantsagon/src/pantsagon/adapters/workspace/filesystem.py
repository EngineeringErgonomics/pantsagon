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
        overwritten_files: dict[Path, Path] = {}
        backup_root = Path(
            tempfile.mkdtemp(prefix="pantsagon-backup-", dir=self.root.parent)
        )
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
                    if dest.exists():
                        backup_path = backup_root / rel
                        backup_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(dest, backup_path)
                        overwritten_files[dest] = backup_path
                    else:
                        created_files.append(dest)
                    self._copy_file(path, dest)
        except Exception as e:
            for copied in reversed(created_files):
                if copied.exists():
                    copied.unlink()
            for dest, backup in overwritten_files.items():
                if backup.exists():
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(backup, dest)
            for directory in reversed(created_dirs):
                if directory.exists():
                    try:
                        directory.rmdir()
                    except OSError:
                        pass
            raise WorkspaceCommitError("Workspace commit failed", cause=e)
        finally:
            shutil.rmtree(stage, ignore_errors=True)
            shutil.rmtree(backup_root, ignore_errors=True)
