from __future__ import annotations

from pathlib import Path
from typing import Iterable

from pantsagon.domain.diagnostics import Diagnostic, Severity
from pantsagon.domain.pack import PackRef
from pantsagon.ports.pack_catalog import PackCatalogPort
from pantsagon.ports.policy_engine import PolicyEnginePort
from pantsagon.ports.renderer import RenderRequest, RendererPort


def resolve_pack_ids(languages: Iterable[str], features: Iterable[str]) -> list[str]:
    packs = ["pantsagon.core"]
    if "python" in languages:
        packs.append("pantsagon.python")
    if "openapi" in features:
        packs.append("pantsagon.openapi")
    if "docker" in features:
        packs.append("pantsagon.docker")
    return packs


def render_bundled_packs(
    stage_dir: Path,
    repo_path: Path,
    languages: list[str],
    services: list[str],
    features: list[str],
    *,
    catalog: PackCatalogPort,
    renderer: RendererPort,
    policy_engine: PolicyEnginePort,
    allow_hooks: bool = False,
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    pack_ids = resolve_pack_ids(languages, features)
    service_name = services[0] if services else "service"
    answers = {
        "repo_name": repo_path.name,
        "service_name": service_name,
    }

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
