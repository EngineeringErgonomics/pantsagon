from __future__ import annotations

from pathlib import Path
from typing import Iterable

from pantsagon.adapters.pack_catalog.bundled import BundledPackCatalog
from pantsagon.adapters.policy import pack_validator
from pantsagon.adapters.policy.pack_validator import PackPolicyEngine
from pantsagon.adapters.renderer.copier_renderer import CopierRenderer
from pantsagon.application.pack_validation import validate_pack
from pantsagon.domain.diagnostics import Diagnostic, Severity
from pantsagon.domain.pack import PackRef
from pantsagon.ports.renderer import RenderRequest


def _repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "packs").is_dir():
            return parent
    raise RuntimeError("Could not locate repo root")


def render_bundled_packs(
    stage_dir: Path,
    repo_path: Path,
    pack_ids: Iterable[str],
    answers: dict[str, str],
    allow_hooks: bool = False,
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    repo_root = _repo_root()
    catalog = BundledPackCatalog(repo_root / "packs")
    renderer = CopierRenderer()
    pack_validator.SCHEMA_PATH = pack_validator._schema_path(repo_root)
    engine = PackPolicyEngine()

    for pack_id in pack_ids:
        pack_path = catalog.get_pack_path(pack_id)
        validation = validate_pack(pack_path, engine)
        diagnostics.extend(validation.diagnostics)
        if any(d.severity == Severity.ERROR for d in validation.diagnostics):
            return diagnostics
        manifest = validation.value or {}
        ref = PackRef(
            id=pack_id,
            version=str(manifest.get("version", "0.0.0")),
            source="bundled",
        )
        renderer.render(
            RenderRequest(
                pack=ref,
                pack_path=pack_path,
                staging_dir=stage_dir,
                answers=answers,
                allow_hooks=allow_hooks,
            )
        )
    return diagnostics
