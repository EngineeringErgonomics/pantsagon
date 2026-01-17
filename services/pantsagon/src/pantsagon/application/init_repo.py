from __future__ import annotations

import shutil
import tempfile
import subprocess
import stat
from pathlib import Path
import os
from typing import Any

import yaml

from pantsagon.application.pack_index import load_pack_index, resolve_pack_ids
from pantsagon.application.rendering import (
    OPENAPI_PACK_ID,
    copy_service_scoped,
    is_service_pack,
    render_bundled_packs,
)
from pantsagon.application.repo_lock import write_lock
from pantsagon.domain.diagnostics import Diagnostic, Severity
from pantsagon.domain.naming import BUILTIN_RESERVED_SERVICES, validate_service_name
from pantsagon.domain.pack import PackRef
from pantsagon.domain.result import Result
from pantsagon.domain.strictness import apply_strictness
from pantsagon.ports.pack_catalog import PackCatalogPort
from pantsagon.ports.policy_engine import PolicyEnginePort
from pantsagon.ports.renderer import RenderRequest, RendererPort
from pantsagon.ports.workspace import WorkspacePort


def _repo_root() -> Path:
    buildroot = os.environ.get("PANTS_BUILDROOT")
    if buildroot:
        return Path(buildroot)
    cwd = Path.cwd().resolve()
    for parent in (cwd, *cwd.parents):
        if (parent / "packs").is_dir():
            return parent
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


def _agents_content(languages: list[str]) -> str:
    langs = {lang.lower() for lang in languages}
    lines = [
        "# AGENTS.md",
        "",
        "## Purpose",
        "This repo is built around strict hexagonal boundaries. Keep layers isolated and code easy to reason about.",
        "",
        "## Hexagonal Architecture Rules",
        "- Domain depends on nothing.",
        "- Ports depend only on domain.",
        "- Application depends on domain + ports.",
        "- Adapters depend on application + ports.",
        "- Entrypoints depend on adapters/application/ports.",
        "- Shared contracts live under shared/contracts and are the only cross-service dependency.",
        "",
        "## Service Layout (per language)",
        "- Python: services/<svc>/src/<pkg>/...",
        "- TypeScript: services/<svc>/src/...",
        "- Rust: services/<svc>/src/...",
        "- Go: services/<svc>/internal/... and cmd/<svc>/main.go",
        "",
        "## Guardrails",
        "- Hooks are installed via tools/guards/install-git-hooks.sh",
        "- Guards live under tools/guards/",
        "- Forbidden imports: pants run tools/forbidden_imports:check",
        "",
        "## Language Notes",
    ]
    if "python" in langs:
        lines.extend(
            [
                "### Python",
                "- Lint/format with ruff: pants lint :: / pants fmt ::",
                "- Typecheck with pyright: pants check ::",
                "- Tests: pants test ::",
                "",
            ]
        )
    if "typescript" in langs:
        lines.extend(
            [
                "### TypeScript",
                "- Keep sources under services/<svc>/src/",
                "- Use pants lint/check when configured for TS targets.",
                "",
            ]
        )
    if "rust" in langs:
        lines.extend(
            [
                "### Rust",
                "- Use cargo build/test locally (or Pants when configured).",
                "",
            ]
        )
    if "go" in langs:
        lines.extend(
            [
                "### Go",
                "- Use go test ./... locally (or Pants when configured).",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def _write_augmented(path: Path, augmented: str, languages: list[str]) -> None:
    if augmented == "agents":
        (path / "AGENTS.md").write_text(_agents_content(languages))
    elif augmented == "claude":
        (path / "CLAUDE.md").write_text("# CLAUDE\n")
    elif augmented == "gemini":
        (path / "GEMINI.md").write_text("# GEMINI\n")


def _ensure_minimal_pants_toml(path: Path) -> None:
    if not path.exists():
        path.write_text('[GLOBAL]\npants_version = "2.30.0"\n')


def _has_shebang(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            return handle.read(2) == b"#!"
    except OSError:
        return False


def _make_executable_tree(path: Path) -> None:
    if not path.exists():
        return
    if path.is_file():
        if _has_shebang(path):
            mode = path.stat().st_mode
            path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        return
    for file in path.rglob("*"):
        if not file.is_file():
            continue
        if _has_shebang(file):
            mode = file.stat().st_mode
            file.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _post_init_setup(repo_path: Path, diagnostics: list[Diagnostic]) -> None:
    _make_executable_tree(repo_path / "tools" / "guards")
    _make_executable_tree(repo_path / ".githooks")

    git = shutil.which("git")
    if git is None:
        diagnostics.append(
            Diagnostic(
                code="INIT_HOOKS_SETUP_FAILED",
                rule="init.hooks",
                severity=Severity.WARN,
                message="git not found; skipping git init and hook installation.",
            )
        )
        return

    try:
        subprocess.run([git, "init"], cwd=repo_path, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as exc:
        diagnostics.append(
            Diagnostic(
                code="INIT_HOOKS_SETUP_FAILED",
                rule="init.hooks",
                severity=Severity.WARN,
                message=f"git init failed: {exc}",
            )
        )
        return

    hook_script = repo_path / "tools" / "guards" / "install-git-hooks.sh"
    if not hook_script.exists():
        diagnostics.append(
            Diagnostic(
                code="INIT_HOOKS_SETUP_FAILED",
                rule="init.hooks",
                severity=Severity.WARN,
                message="install-git-hooks.sh missing; git hooks not installed.",
            )
        )
        return

    try:
        subprocess.run([str(hook_script)], cwd=repo_path, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as exc:
        diagnostics.append(
            Diagnostic(
                code="INIT_HOOKS_SETUP_FAILED",
                rule="init.hooks",
                severity=Severity.WARN,
                message=f"hook installation failed: {exc}",
            )
        )


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
                "service_scoped": is_service_pack(manifest),
            }
        )

    if any(d.severity == Severity.ERROR for d in diagnostics):
        return Result(diagnostics=apply_strictness(diagnostics, strict_enabled))

    service_packages = {name: name.replace("-", "_") for name in services}
    service_name = services[0] if services else "service"
    service_pkg = service_packages.get(service_name, service_name.replace("-", "_"))
    answers_base = {
        "repo_name": repo_path.name,
        "service_packages": service_packages,
        "languages": languages,
        "features": features,
    }
    answers = {
        **answers_base,
        "service_name": service_name,
        "service_pkg": service_pkg,
    }

    ordered_packs = _render_order(resolved_packs)
    ordered_ids = [pack["id"] for pack in ordered_packs]
    service_packs = [pack for pack in ordered_packs if pack.get("service_scoped")]
    global_packs = [pack for pack in ordered_packs if not pack.get("service_scoped")]
    lock: dict[str, Any] = {
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
            if global_packs:
                render_diags = render_bundled_packs(
                    stage_dir=stage,
                    repo_path=repo_path,
                    pack_ids=[pack["id"] for pack in global_packs],
                    answers=answers,
                    catalog=pack_catalog,
                    renderer=renderer_port,
                    policy_engine=policy_engine,
                    allow_hooks=allow_hooks,
                )
                diagnostics.extend(render_diags)
                if any(d.severity == Severity.ERROR for d in render_diags):
                    return Result(diagnostics=apply_strictness(diagnostics, strict_enabled))

            for service in services:
                service_pkg = service_packages.get(service, service.replace("-", "_"))
                service_answers = {
                    **answers_base,
                    "service_name": service,
                    "service_pkg": service_pkg,
                }
                for pack in service_packs:
                    pack_id = str(pack.get("id"))
                    version = str(pack.get("version"))
                    if pack_catalog is not None:
                        pack_path = pack_catalog.get_pack_path(
                            PackRef(id=pack_id, version=version, source="bundled")
                        )
                    else:
                        pack_path = _bundled_packs_root() / pack_id.split(".")[-1]
                    with tempfile.TemporaryDirectory() as tempdir:
                        renderer_port.render(
                            RenderRequest(
                                pack=PackRef(id=pack_id, version=version, source="bundled"),
                                pack_path=pack_path,
                                staging_dir=Path(tempdir),
                                answers=service_answers,
                                allow_hooks=allow_hooks,
                            )
                        )
                        copy_service_scoped(
                            Path(tempdir),
                            stage,
                            repo_path,
                            service,
                            allow_openapi=pack_id == OPENAPI_PACK_ID,
                        )

            _write_augmented(stage, augmented, languages)
            _ensure_minimal_pants_toml(stage / "pants.toml")
            workspace.commit(stage)
            _post_init_setup(repo_path, diagnostics)
            return Result(diagnostics=apply_strictness(diagnostics, strict_enabled))
        finally:
            if stage.exists():
                shutil.rmtree(stage, ignore_errors=True)

    write_lock(repo_path / ".pantsagon.toml", lock)
    _ensure_minimal_pants_toml(repo_path / "pants.toml")
    _write_augmented(repo_path, augmented, languages)
    _post_init_setup(repo_path, diagnostics)
    return Result(diagnostics=apply_strictness(diagnostics, strict_enabled))
