from __future__ import annotations

from pathlib import Path
import os
import shutil
import tempfile
from typing import Any

from pantsagon.adapters.errors import RendererExecutionError
from pantsagon.adapters.policy.pack_validator import PackPolicyEngine
from pantsagon.adapters.renderer.copier_renderer import CopierRenderer
from pantsagon.adapters.workspace.filesystem import FilesystemWorkspace
from pantsagon.application.repo_lock import effective_strict, project_reserved_services, read_lock, write_lock
from pantsagon.domain.diagnostics import Diagnostic, Severity
from pantsagon.domain.naming import BUILTIN_RESERVED_SERVICES, validate_service_name
from pantsagon.domain.pack import PackRef
from pantsagon.domain.result import Result
from pantsagon.domain.strictness import apply_strictness
from pantsagon.ports.policy_engine import PolicyEnginePort
from pantsagon.ports.renderer import RenderRequest, RendererPort
from pantsagon.ports.workspace import WorkspacePort


OPENAPI_PACK_ID = "pantsagon.openapi"


def _pack_roots() -> list[Path]:
    roots: list[Path] = []
    buildroot = os.environ.get("PANTS_BUILDROOT")
    if buildroot:
        roots.append(Path(buildroot))
    cwd = Path.cwd().resolve()
    roots.extend([cwd, *cwd.parents])
    roots.extend(Path(__file__).resolve().parents)
    seen: set[Path] = set()
    ordered: list[Path] = []
    for root in roots:
        if root in seen:
            continue
        seen.add(root)
        ordered.append(root)
    return ordered


def _bundled_pack_path(pack_id: str) -> Path | None:
    pack_name = pack_id.split(".")[-1]
    for root in _pack_roots():
        candidate = root / "packs" / pack_name
        if candidate.exists():
            return candidate
    return None


def _get_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _build_answers(lock: dict[str, Any], repo_path: Path, name: str) -> dict[str, Any]:
    resolved = lock.get("resolved") if isinstance(lock.get("resolved"), dict) else {}
    existing = resolved.get("answers") if isinstance(resolved.get("answers"), dict) else {}
    answers = dict(existing)
    service_pkg = name.replace("-", "_")
    service_packages: dict[str, str] = {}
    if isinstance(existing.get("service_packages"), dict):
        service_packages = dict(existing.get("service_packages", {}))
    service_packages[name] = service_pkg
    answers.setdefault("repo_name", repo_path.name)
    answers["service_name"] = name
    answers["service_pkg"] = service_pkg
    answers["service_packages"] = service_packages
    return answers


def _resolve_pack_path(entry: dict[str, Any], repo_path: Path) -> tuple[Path | None, list[Diagnostic]]:
    diagnostics: list[Diagnostic] = []
    pack_id = str(entry.get("id") or "")
    source = str(entry.get("source") or "")
    if source == "bundled":
        pack_path = _bundled_pack_path(pack_id)
        if pack_path is None or not pack_path.exists():
            diagnostics.append(
                Diagnostic(
                    code="PACK_NOT_FOUND",
                    rule="pack.catalog.fetch",
                    severity=Severity.ERROR,
                    message=f"Bundled pack not found: {pack_id}",
                )
            )
            return None, diagnostics
        return pack_path, diagnostics
    if source == "local":
        location = entry.get("location")
        if not location:
            diagnostics.append(
                Diagnostic(
                    code="PACK_LOCATION_MISSING",
                    rule="pack.catalog.fetch",
                    severity=Severity.ERROR,
                    message=f"Local pack missing location: {pack_id}",
                )
            )
            return None, diagnostics
        location_path = Path(str(location))
        pack_path = location_path if location_path.is_absolute() else repo_path / location_path
        if not pack_path.exists():
            diagnostics.append(
                Diagnostic(
                    code="PACK_NOT_FOUND",
                    rule="pack.catalog.fetch",
                    severity=Severity.ERROR,
                    message=f"Local pack not found: {pack_id}",
                )
            )
            return None, diagnostics
        return pack_path, diagnostics

    diagnostics.append(
        Diagnostic(
            code="LOCK_PACK_INVALID",
            rule="lock.resolved.packs",
            severity=Severity.ERROR,
            message=f"Unsupported pack source: {source}",
        )
    )
    return None, diagnostics


def _is_service_path(rel: Path, service_name: str) -> bool:
    return len(rel.parts) >= 2 and rel.parts[0] == "services" and rel.parts[1] == service_name


def _openapi_spec_path(service_name: str) -> Path:
    return Path("shared") / "contracts" / "openapi" / f"{service_name}.yaml"


def _openapi_readme_path() -> Path:
    return Path("shared") / "contracts" / "openapi" / "README.md"


def _copy_service_scoped(
    temp_root: Path,
    stage_root: Path,
    repo_root: Path,
    service_name: str,
    allow_openapi: bool,
) -> None:
    spec_rel = _openapi_spec_path(service_name)
    readme_rel = _openapi_readme_path()
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
        if allow_openapi and rel == readme_rel:
            if not dest.exists() and not (repo_root / rel).exists():
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, dest)


def add_service(
    repo_path: Path,
    name: str,
    lang: str,
    strict: bool | None = None,
    *,
    renderer_port: RendererPort | None = None,
    policy_engine: PolicyEnginePort | None = None,
    workspace: WorkspacePort | None = None,
) -> Result[None]:
    diagnostics: list[Diagnostic] = []
    lock_result = read_lock(repo_path / ".pantsagon.toml")
    diagnostics.extend(lock_result.diagnostics)
    lock = lock_result.value
    strict_enabled = effective_strict(strict, lock)
    if lock is None:
        return Result(diagnostics=apply_strictness(diagnostics, strict_enabled))

    diagnostics.extend(
        validate_service_name(name, BUILTIN_RESERVED_SERVICES, project_reserved_services(lock))
    )
    if any(d.severity == Severity.ERROR for d in diagnostics):
        return Result(diagnostics=apply_strictness(diagnostics, strict_enabled))

    svc_dir = repo_path / "services" / name
    if svc_dir.exists():
        diagnostics.append(
            Diagnostic(
                code="SERVICE_EXISTS",
                rule="service.name",
                severity=Severity.ERROR,
                message="Service already exists",
            )
        )
        return Result(diagnostics=apply_strictness(diagnostics, strict_enabled))

    selection = lock.get("selection") if isinstance(lock.get("selection"), dict) else {}
    existing_services = _get_list(selection.get("services"))
    if name in existing_services:
        diagnostics.append(
            Diagnostic(
                code="SERVICE_EXISTS",
                rule="service.name",
                severity=Severity.ERROR,
                message="Service already exists",
            )
        )
        return Result(diagnostics=apply_strictness(diagnostics, strict_enabled))

    resolved = lock.get("resolved")
    if not isinstance(resolved, dict):
        diagnostics.append(
            Diagnostic(
                code="LOCK_SECTION_MISSING",
                rule="lock.section",
                severity=Severity.ERROR,
                message="Missing [resolved] section in .pantsagon.toml",
            )
        )
        return Result(diagnostics=apply_strictness(diagnostics, strict_enabled))

    raw_packs = resolved.get("packs")
    packs = _get_list(raw_packs)
    if not packs:
        diagnostics.append(
            Diagnostic(
                code="LOCK_SECTION_MISSING",
                rule="lock.section",
                severity=Severity.ERROR,
                message="Missing [resolved.packs] entries in .pantsagon.toml",
            )
        )
        return Result(diagnostics=apply_strictness(diagnostics, strict_enabled))

    pack_entries: list[dict[str, Any]] = []
    pack_ids: set[str] = set()
    for entry in packs:
        if not isinstance(entry, dict):
            diagnostics.append(
                Diagnostic(
                    code="LOCK_PACK_INVALID",
                    rule="lock.resolved.packs",
                    severity=Severity.ERROR,
                    message="Pack entry must be a table",
                )
            )
            continue
        pack_id = entry.get("id")
        version = entry.get("version")
        source = entry.get("source")
        if not pack_id or not version or not source:
            diagnostics.append(
                Diagnostic(
                    code="LOCK_PACK_INVALID",
                    rule="lock.resolved.packs",
                    severity=Severity.ERROR,
                    message="Pack entry must include id, version, and source",
                )
            )
            continue
        pack_entries.append(entry)
        pack_ids.add(str(pack_id))

    if any(d.severity == Severity.ERROR for d in diagnostics):
        return Result(diagnostics=apply_strictness(diagnostics, strict_enabled))

    renderer = renderer_port or CopierRenderer()
    engine = policy_engine or PackPolicyEngine()
    workspace_impl = workspace or FilesystemWorkspace(repo_path)
    allow_hooks = bool(lock.get("settings", {}).get("allow_hooks", False))

    answers = _build_answers(lock, repo_path, name)
    allow_openapi = OPENAPI_PACK_ID in pack_ids

    stage = workspace_impl.begin_transaction()
    try:
        for entry in pack_entries:
            pack_id = str(entry.get("id"))
            version = str(entry.get("version"))
            pack_path, pack_diags = _resolve_pack_path(entry, repo_path)
            diagnostics.extend(pack_diags)
            if pack_path is None:
                return Result(diagnostics=apply_strictness(diagnostics, strict_enabled))

            validation = engine.validate_pack(pack_path)
            diagnostics.extend(validation.diagnostics)
            if any(d.severity == Severity.ERROR for d in validation.diagnostics):
                return Result(diagnostics=apply_strictness(diagnostics, strict_enabled))

            with tempfile.TemporaryDirectory() as tempdir:
                request = RenderRequest(
                    pack=PackRef(id=pack_id, version=version, source=str(entry.get("source"))),
                    pack_path=pack_path,
                    staging_dir=Path(tempdir),
                    answers=answers,
                    allow_hooks=allow_hooks,
                )
                try:
                    renderer.render(request)
                except RendererExecutionError as exc:
                    diagnostics.append(
                        Diagnostic(
                            code="PACK_RENDER_FAILED",
                            rule="pack.render",
                            severity=Severity.ERROR,
                            message=str(exc),
                            is_execution=True,
                        )
                    )
                    return Result(diagnostics=apply_strictness(diagnostics, strict_enabled))

                _copy_service_scoped(
                    Path(tempdir),
                    stage,
                    repo_path,
                    name,
                    allow_openapi,
                )

        selection = dict(selection)
        selection_services = list(existing_services)
        selection_services.append(name)
        selection["services"] = selection_services
        lock["selection"] = selection
        resolved["answers"] = answers
        lock["resolved"] = resolved
        write_lock(stage / ".pantsagon.toml", lock)
        workspace_impl.commit(stage)
        return Result(diagnostics=apply_strictness(diagnostics, strict_enabled))
    finally:
        if stage.exists():
            shutil.rmtree(stage, ignore_errors=True)
