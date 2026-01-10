from __future__ import annotations

from pathlib import Path
from typing import Any

from pantsagon.adapters.pack_catalog.bundled import BundledPackCatalog
from pantsagon.adapters.policy.pack_validator import PackPolicyEngine
from pantsagon.adapters.workspace.filesystem import FilesystemWorkspace
from pantsagon.application.pack_index import load_pack_index, resolve_pack_ids
from pantsagon.application.repo_lock import write_lock
from pantsagon.domain.diagnostics import Diagnostic, Severity
from pantsagon.domain.result import Result


def _repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "packs").is_dir():
            return parent
    raise RuntimeError("Could not locate repo root")


def _bundled_packs_root() -> Path:
    return _repo_root() / "packs"


def _order_packs_by_requires(packs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pack_ids = {str(p.get("id")) for p in packs if p.get("id") is not None}
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


def init_repo(
    repo_path: Path,
    languages: list[str],
    services: list[str],
    features: list[str],
    renderer: str,
    augmented_coding: str | None = None,
) -> Result[None]:
    diagnostics: list[Diagnostic] = []
    repo_root = _repo_root()
    index_path = repo_root / "packs" / "_index.json"
    index = load_pack_index(index_path)
    resolved_ids = resolve_pack_ids(index, languages=languages, features=features)
    diagnostics.extend(resolved_ids.diagnostics)
    if any(d.severity == Severity.ERROR for d in diagnostics):
        return Result(diagnostics=diagnostics)

    catalog = BundledPackCatalog(_bundled_packs_root())
    policy = PackPolicyEngine()
    resolved_packs: list[dict[str, Any]] = []
    for pack_id in resolved_ids.value or []:
        pack_path = catalog.get_pack_path(pack_id)
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
        manifest_result = policy.validate_pack(pack_path)
        diagnostics.extend(manifest_result.diagnostics)
        if any(d.severity == Severity.ERROR for d in manifest_result.diagnostics):
            continue
        manifest = manifest_result.value or {}
        resolved_packs.append(
            {
                "id": pack_id,
                "version": str(manifest.get("version", "0.0.0")),
                "source": "bundled",
                "requires": list(manifest.get("requires", {}).get("packs", []))
                if isinstance(manifest.get("requires"), dict)
                else [],
            }
        )

    if any(d.severity == Severity.ERROR for d in diagnostics):
        return Result(diagnostics=diagnostics)

    service_name = services[0] if services else "service"
    answers = {"repo_name": repo_path.name, "service_name": service_name}
    resolved_packs = _order_packs_by_requires(resolved_packs)
    resolved_pack_ids = {p["id"] for p in resolved_packs}
    lock: dict[str, Any] = {
        "tool": {"name": "pantsagon", "version": "0.1.0"},
        "settings": {
            "renderer": renderer,
            "strict": False,
            "strict_manifest": True,
            "allow_hooks": False,
        },
        "selection": {
            "languages": languages,
            "features": features,
            "services": services,
            "augmented_coding": augmented_coding or "none",
        },
        "resolved": {
            "packs": [
                {"id": p["id"], "version": p["version"], "source": p["source"]}
                for p in resolved_packs
            ],
            "answers": answers,
        },
    }

    workspace = FilesystemWorkspace(repo_path)
    stage = workspace.begin_transaction()
    write_lock(stage / ".pantsagon.toml", lock)
    (stage / "pants.toml").write_text('[GLOBAL]\npants_version = "2.30.0"\n')
    for service in services:
        svc_root = stage / "services" / service
        svc_root.mkdir(parents=True, exist_ok=True)
        if "pantsagon.python" in resolved_pack_ids:
            for layer in ("domain", "ports", "application", "adapters", "entrypoints"):
                (svc_root / layer).mkdir(parents=True, exist_ok=True)

    workspace.commit(stage)

    augmented = augmented_coding or "none"
    if augmented == "agents":
        (repo_path / "AGENTS.md").write_text("# AGENTS\n")
    elif augmented == "claude":
        (repo_path / "CLAUDE.md").write_text("# CLAUDE\n")
    elif augmented == "gemini":
        (repo_path / "GEMINI.md").write_text("# GEMINI\n")
    return Result(diagnostics=diagnostics)
