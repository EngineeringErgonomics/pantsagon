from __future__ import annotations

from pathlib import Path
import shutil
from typing import Iterable

from pantsagon.domain.diagnostics import Diagnostic, Severity
from pantsagon.domain.json_types import JsonDict
from pantsagon.domain.pack import PackRef
from pantsagon.ports.pack_catalog import PackCatalogPort
from pantsagon.ports.policy_engine import PolicyEnginePort
from pantsagon.ports.renderer import RenderRequest, RendererPort

SERVICE_PACK_VARS = {"service_name", "service_pkg"}
OPENAPI_PACK_ID = "pantsagon.openapi"
OPENAPI_SHARED_FILES = {
    Path("shared") / "contracts" / "openapi" / "README.md",
    Path("shared") / "contracts" / "openapi" / "BUILD",
}


def is_service_pack(manifest: JsonDict | None) -> bool:
    if not isinstance(manifest, dict):
        return False
    raw_vars = manifest.get("variables")
    if not isinstance(raw_vars, list):
        return False
    names = {str(item.get("name")) for item in raw_vars if isinstance(item, dict)}
    return bool(names & SERVICE_PACK_VARS)


def _is_service_path(rel: Path, service_name: str) -> bool:
    return (
        len(rel.parts) >= 2
        and rel.parts[0] == "services"
        and rel.parts[1] == service_name
    )


def copy_service_scoped(
    temp_root: Path,
    stage_root: Path,
    repo_root: Path,
    service_name: str,
    allow_openapi: bool,
) -> None:
    spec_rel = Path("shared") / "contracts" / "openapi" / f"{service_name}.yaml"
    for path in temp_root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(temp_root)
        dest = stage_root / rel
        if _is_service_path(rel, service_name):
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest)
            continue
        if allow_openapi and rel == spec_rel:
            if not dest.exists() and not (repo_root / rel).exists():
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, dest)
            continue
        if allow_openapi and rel in OPENAPI_SHARED_FILES:
            if not dest.exists() and not (repo_root / rel).exists():
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, dest)


def render_bundled_packs(
    stage_dir: Path,
    repo_path: Path,
    pack_ids: Iterable[str],
    answers: JsonDict,
    *,
    catalog: PackCatalogPort,
    renderer: RendererPort,
    policy_engine: PolicyEnginePort,
    allow_hooks: bool = False,
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []

    for pack_id in pack_ids:
        ref = PackRef(id=pack_id, version="0.0.0", source="bundled")
        pack_path = catalog.get_pack_path(ref)
        validation = policy_engine.validate_pack(pack_path)
        diagnostics.extend(validation.diagnostics)
        if any(d.severity == Severity.ERROR for d in validation.diagnostics):
            return diagnostics
        version = "0.0.0"
        if isinstance(validation.value, dict):
            version = str(validation.value.get("version", "0.0.0"))
        ref = PackRef(id=pack_id, version=version, source="bundled")
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
