from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import yaml

from pantsagon.application.pack_index import load_pack_index, resolve_pack_ids
from pantsagon.application.rendering import render_bundled_packs
from pantsagon.application.repo_lock import write_lock
from pantsagon.domain.diagnostics import Diagnostic, Severity
from pantsagon.domain.naming import BUILTIN_RESERVED_SERVICES, validate_service_name
from pantsagon.domain.pack import PackRef
from pantsagon.domain.result import Result
from pantsagon.domain.strictness import apply_strictness
from pantsagon.ports.pack_catalog import PackCatalogPort
from pantsagon.ports.policy_engine import PolicyEnginePort
from pantsagon.ports.renderer import RendererPort
from pantsagon.ports.workspace import WorkspacePort


def _repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "packs").is_dir():
            return parent
    raise RuntimeError("Could not locate repo root")


def _bundled_packs_root() -> Path:
    return _repo_root() / "packs"


def _load_manifest(pack_path: Path) -> dict[str, Any]:
    try:
        raw: object = yaml.safe_load((pack_path / "pack.yaml").read_text()) or {}
    except FileNotFoundError:
        return {}
    return raw if isinstance(raw, dict) else {}


def _extract_requires(manifest: dict[str, Any]) -> list[str]:
    requires_block = manifest.get("requires")
    if isinstance(requires_block, dict):
        raw = requires_block.get("packs")
        if isinstance(raw, list):
            return [str(item) for item in raw]
    return []


def _order_packs_by_requires(packs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pack_ids = {str(pack.get("id")) for pack in packs if pack.get("id") is not None}
    requires_map: dict[str, set[str]] = {}
    for pack in packs:
        pack_id = str(pack.get("id"))
        raw_requires = pack.get("requires")
        requires = set(raw_requires) if isinstance(raw_requires, list) else set()
        requires_map[pack_id] = {req for req in requires if req in pack_ids}

    dependents: dict[str, set[str]] = {pid: set() for pid in pack_ids}
    indegree: dict[str, int] = {pid: 0 for pid in pack_ids}
    for pack_id, requires in requires_map.items():
        indegree[pack_id] = len(requires)
        for req in requires:
            dependents[req].add(pack_id)

    ready = sorted([pid for pid, degree in indegree.items() if degree == 0])
    ordered_ids: list[str] = []
    while ready:
        current = ready.pop(0)
        ordered_ids.append(current)
        for dependent in sorted(dependents.get(current, set())):
            indegree[dependent] -= 1
            if indegree[dependent] == 0:
                ready.append(dependent)
                ready.sort()

    remaining = sorted([pid for pid in pack_ids if pid not in ordered_ids])
    ordered_ids.extend(remaining)
    pack_by_id = {str(pack.get("id")): pack for pack in packs if pack.get("id") is not None}
    return [pack_by_id[pid] for pid in ordered_ids]


def _render_order(packs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered = _order_packs_by_requires(packs)
    core = [pack for pack in ordered if pack.get("id") == "pantsagon.core"]
    rest = [pack for pack in ordered if pack.get("id") != "pantsagon.core"]
    return rest + core if core else ordered


def _write_augmented(path: Path, augmented: str) -> None:
    if augmented == "agents":
        (path / "AGENTS.md").write_text("# AGENTS\n")
    elif augmented == "claude":
        (path / "CLAUDE.md").write_text("# CLAUDE\n")
    elif augmented == "gemini":
        (path / "GEMINI.md").write_text("# GEMINI\n")


def _ensure_minimal_pants_toml(path: Path) -> None:
    if not path.exists():
        path.write_text('[GLOBAL]\npants_version = "2.30.0"\n')


def init_repo(
    repo_path: Path,
    languages: list[str],
    services: list[str],
    features: list[str],
    renderer: str,
    *,
    renderer_port: RendererPort | None = None,
    pack_catalog: PackCatalogPort | None = None,
    policy_engine: PolicyEnginePort | None = None,
    workspace: WorkspacePort | None = None,
    allow_hooks: bool = False,
    augmented_coding: str | None = None,
    strict: bool | None = None,
) -> Result[None]:
    diagnostics: list[Diagnostic] = []
    strict_enabled = bool(strict)
    for service in services:
        diagnostics.extend(validate_service_name(service, BUILTIN_RESERVED_SERVICES, set()))
    if any(d.severity == Severity.ERROR for d in diagnostics):
        return Result(diagnostics=apply_strictness(diagnostics, strict_enabled))

    repo_root = _repo_root()
    index_path = repo_root / "packs" / "_index.json"
    index = load_pack_index(index_path)
    resolved_ids = resolve_pack_ids(index, languages=languages, features=features)
    diagnostics.extend(resolved_ids.diagnostics)
    if any(d.severity == Severity.ERROR for d in diagnostics):
        return Result(diagnostics=apply_strictness(diagnostics, strict_enabled))

    resolved_packs: list[dict[str, Any]] = []
    for pack_id in resolved_ids.value or []:
        if pack_catalog is not None:
            pack_path = pack_catalog.get_pack_path(PackRef(id=pack_id, version="0.0.0", source="bundled"))
        else:
            pack_path = _bundled_packs_root() / pack_id.split(".")[-1]
        if not pack_path.exists():
            diagnostics.append(
                Diagnostic(
                    code="PACK_NOT_FOUND",
                    rule="pack.catalog.fetch",
                    severity=Severity.ERROR,
                    message=f"Pack not found: {pack_id}",
                )
            )
            continue

        manifest: dict[str, Any] = {}
        if pack_catalog is not None:
            manifest = pack_catalog.load_manifest(pack_path)
        else:
            manifest = _load_manifest(pack_path)

        if policy_engine is not None:
            manifest_result = policy_engine.validate_pack(pack_path)
            diagnostics.extend(manifest_result.diagnostics)
            if any(d.severity == Severity.ERROR for d in manifest_result.diagnostics):
                continue
            if isinstance(manifest_result.value, dict):
                manifest = manifest_result.value

        resolved_packs.append(
            {
                "id": pack_id,
                "version": str(manifest.get("version", "0.0.0")),
                "source": "bundled",
                "requires": _extract_requires(manifest),
            }
        )

    if any(d.severity == Severity.ERROR for d in diagnostics):
        return Result(diagnostics=apply_strictness(diagnostics, strict_enabled))

    service_packages = {name: name.replace("-", "_") for name in services}
    service_name = services[0] if services else "service"
    service_pkg = service_packages.get(service_name, service_name.replace("-", "_"))
    answers = {
        "repo_name": repo_path.name,
        "service_name": service_name,
        "service_pkg": service_pkg,
        "service_packages": service_packages,
    }

    ordered_packs = _render_order(resolved_packs)
    ordered_ids = [pack["id"] for pack in ordered_packs]
    lock: dict[str, Any] = {
        "tool": {"name": "pantsagon", "version": "0.1.0"},
        "settings": {
            "renderer": renderer,
            "strict": strict_enabled,
            "strict_manifest": True,
            "allow_hooks": allow_hooks,
        },
        "selection": {
            "languages": languages,
            "features": features,
            "services": services,
            "augmented_coding": augmented_coding or "none",
        },
        "resolved": {
            "packs": [
                {"id": pack["id"], "version": pack["version"], "source": pack["source"]}
                for pack in ordered_packs
            ],
            "answers": answers,
        },
    }

    ports_requested = any([renderer_port, pack_catalog, policy_engine, workspace])
    if ports_requested and not all([renderer_port, pack_catalog, policy_engine, workspace]):
        diagnostics.append(
            Diagnostic(
                code="INIT_PORTS_MISSING",
                rule="init.ports",
                severity=Severity.ERROR,
                message="Init requires renderer, pack catalog, policy engine, and workspace ports.",
            )
        )
        return Result(diagnostics=apply_strictness(diagnostics, strict_enabled))

    augmented = augmented_coding or "none"
    if ports_requested and workspace is not None:
        stage = workspace.begin_transaction()
        try:
            write_lock(stage / ".pantsagon.toml", lock)
            render_diags = render_bundled_packs(
                stage_dir=stage,
                repo_path=repo_path,
                pack_ids=ordered_ids,
                answers=answers,
                catalog=pack_catalog,
                renderer=renderer_port,
                policy_engine=policy_engine,
                allow_hooks=allow_hooks,
            )
            diagnostics.extend(render_diags)
            if any(d.severity == Severity.ERROR for d in render_diags):
                return Result(diagnostics=apply_strictness(diagnostics, strict_enabled))

            _write_augmented(stage, augmented)
            _ensure_minimal_pants_toml(stage / "pants.toml")
            workspace.commit(stage)
            return Result(diagnostics=apply_strictness(diagnostics, strict_enabled))
        finally:
            if stage.exists():
                shutil.rmtree(stage, ignore_errors=True)

    write_lock(repo_path / ".pantsagon.toml", lock)
    _ensure_minimal_pants_toml(repo_path / "pants.toml")
    _write_augmented(repo_path, augmented)
    return Result(diagnostics=apply_strictness(diagnostics, strict_enabled))
