from __future__ import annotations

from pathlib import Path
from typing import Iterable

from pantsagon.adapters.pack_catalog.bundled import BundledPackCatalog
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


def _bundled_packs_root() -> Path:
    return _repo_root() / "packs"


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
    service_packages: dict[str, str] | None = None,
    allow_hooks: bool = False,
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    catalog = BundledPackCatalog(_bundled_packs_root())
    renderer = CopierRenderer()

    pack_ids = resolve_pack_ids(languages, features)
    service_name = services[0] if services else "service"
    service_pkg = (service_packages or {}).get(service_name, service_name.replace("-", "_"))
    answers = {
        "repo_name": repo_path.name,
        "service_name": service_name,
        "service_pkg": service_pkg,
    }

    for pack_id in pack_ids:
        pack_path = catalog.get_pack_path(pack_id)
        validation = validate_pack(pack_path)
        diagnostics.extend(validation.diagnostics)
        if any(d.severity == Severity.ERROR for d in validation.diagnostics):
            return diagnostics
        ref = PackRef(id=pack_id, version=validation.value.get("version", "0.0.0"), source="bundled")
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
