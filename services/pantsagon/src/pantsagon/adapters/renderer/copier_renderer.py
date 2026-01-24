from pathlib import Path

from pantsagon.adapters.errors import RendererExecutionError
from pantsagon.domain.json_types import as_json_dict
from pantsagon.ports.renderer import RenderOutcome, RenderRequest


def _ensure_githooks(staging_dir: Path) -> None:
    hooks_dir = staging_dir / ".githooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    guards_dir = staging_dir / "tools" / "guards"
    if not guards_dir.exists():
        return
    hook_pairs = {
        "pre-commit": guards_dir / "pre-commit.sh",
        "pre-push": guards_dir / "pre-push.sh",
    }
    for hook_name, target in hook_pairs.items():
        if not target.exists():
            continue
        hook_path = hooks_dir / hook_name
        content = "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                "",
                'ROOT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"',
                f'exec "$ROOT_DIR/{target.relative_to(staging_dir)}"',
                "",
            ]
        )
        if hook_path.exists():
            try:
                if hook_path.read_text() == content:
                    continue
            except Exception:
                pass
        hooks_dir.mkdir(parents=True, exist_ok=True)
        hook_path.write_text(content)


class CopierRenderer:
    def render(self, request: RenderRequest) -> RenderOutcome:
        try:
            from copier import run_copy

            run_copy(
                str(request.pack_path),
                str(request.staging_dir),
                data=request.answers,
                defaults=True,
                unsafe=request.allow_hooks,
                overwrite=True,
            )
            _ensure_githooks(Path(request.staging_dir))
        except Exception as e:  # Copier raises various exceptions
            raise RendererExecutionError(
                "Copier failed",
                details=as_json_dict({"pack": request.pack.id}),
                cause=e,
            )
        return RenderOutcome(rendered_paths=[request.staging_dir], warnings=[])
