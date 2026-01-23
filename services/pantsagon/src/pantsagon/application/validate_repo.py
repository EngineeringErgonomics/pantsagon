from __future__ import annotations

from pathlib import Path
import os
from typing import Any

import yaml

from pantsagon.application.pack_index import load_pack_index, resolve_pack_ids
from pantsagon.application.repo_lock import (
    effective_strict,
    project_reserved_services,
    read_lock,
)
from pantsagon.domain.diagnostics import (
    Diagnostic,
    FileLocation,
    Severity,
    ValueLocation,
)
from pantsagon.domain.naming import (
    BUILTIN_RESERVED_SERVICES,
    validate_feature_name,
    validate_pack_id,
    validate_service_name,
)
from pantsagon.domain.result import Result
from pantsagon.domain.strictness import apply_strictness
from pantsagon.ports.policy_engine import PolicyEnginePort


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


def _bundled_pack_path(pack_id: str) -> Path:
    return _bundled_packs_root() / pack_id.split(".")[-1]


def _get_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _load_manifest(pack_path: Path) -> dict[str, Any]:
    try:
        raw: object = yaml.safe_load((pack_path / "pack.yaml").read_text()) or {}
    except FileNotFoundError:
        return {}
    return raw if isinstance(raw, dict) else {}


def _maybe_warn_feature_shadow(feature: str, pack_ids: set[str]) -> Diagnostic | None:
    if feature in pack_ids:
        return Diagnostic(
            code="FEATURE_NAME_SHADOWS_PACK",
            rule="naming.feature.shadows_pack",
            severity=Severity.WARN,
            message=f"Feature name shadows pack id: {feature}",
            location=ValueLocation("feature", feature),
            upgradeable=True,
        )
    return None


def validate_repo(
    repo_path: Path,
    strict: bool | None = None,
    policy_engine: PolicyEnginePort | None = None,
) -> Result[None]:
    diagnostics: list[Diagnostic] = []
    lock_result = read_lock(repo_path / ".pantsagon.toml")
    diagnostics.extend(lock_result.diagnostics)
    strict_enabled = effective_strict(strict, lock_result.value)
    if lock_result.value is None:
        return Result(diagnostics=apply_strictness(diagnostics, strict_enabled))

    lock = lock_result.value
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

    pack_ids: list[str] = []
    pack_entries: list[dict[str, Any]] = []
    seen: set[str] = set()
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
        pack_id = str(pack_id)
        diagnostics.extend(validate_pack_id(pack_id))
        if pack_id in seen:
            diagnostics.append(
                Diagnostic(
                    code="LOCK_PACK_DUPLICATE",
                    rule="lock.resolved.packs",
                    severity=Severity.ERROR,
                    message=f"Duplicate pack id: {pack_id}",
                )
            )
            continue
        seen.add(pack_id)
        pack_ids.append(pack_id)
        pack_entries.append(entry)

    if any(d.severity == Severity.ERROR for d in diagnostics):
        return Result(diagnostics=apply_strictness(diagnostics, strict_enabled))

    pack_id_set = set(pack_ids)
    for entry in pack_entries:
        pack_id = str(entry.get("id"))
        source = str(entry.get("source"))
        pack_path: Path | None = None
        if source == "bundled":
            pack_path = _bundled_pack_path(pack_id)
            if not pack_path.exists():
                diagnostics.append(
                    Diagnostic(
                        code="PACK_NOT_FOUND",
                        rule="pack.catalog.fetch",
                        severity=Severity.ERROR,
                        message=f"Bundled pack not found: {pack_id}",
                    )
                )
                continue
        elif source == "local":
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
                continue
            location_path = Path(str(location))
            pack_path = (
                location_path
                if location_path.is_absolute()
                else repo_path / location_path
            )
            if not pack_path.exists():
                diagnostics.append(
                    Diagnostic(
                        code="PACK_NOT_FOUND",
                        rule="pack.catalog.fetch",
                        severity=Severity.ERROR,
                        message=f"Local pack not found: {pack_id}",
                    )
                )
                continue
        else:
            diagnostics.append(
                Diagnostic(
                    code="LOCK_PACK_INVALID",
                    rule="lock.resolved.packs",
                    severity=Severity.ERROR,
                    message=f"Unsupported pack source: {source}",
                )
            )
            continue

        manifest: dict[str, Any] = {}
        if policy_engine is not None:
            manifest_result = policy_engine.validate_pack(pack_path)
            diagnostics.extend(manifest_result.diagnostics)
            if isinstance(manifest_result.value, dict):
                manifest = manifest_result.value
        if not manifest:
            manifest = _load_manifest(pack_path)

        compatibility = manifest.get("compatibility")
        if compatibility is not None and not isinstance(compatibility, dict):
            diagnostics.append(
                Diagnostic(
                    code="PACK_COMPAT_INVALID",
                    rule="pack.compatibility",
                    severity=Severity.ERROR,
                    message=f"Invalid compatibility block in pack {pack_id}",
                )
            )
        elif isinstance(compatibility, dict):
            pants_req = compatibility.get("pants")
            if pants_req is not None and not isinstance(pants_req, str):
                diagnostics.append(
                    Diagnostic(
                        code="PACK_COMPAT_INVALID",
                        rule="pack.compatibility",
                        severity=Severity.ERROR,
                        message=f"Invalid pants compatibility in pack {pack_id}",
                    )
                )

        provides = manifest.get("provides")
        if isinstance(provides, dict):
            raw_features = provides.get("features")
            for feature in _get_list(raw_features):
                diagnostics.extend(validate_feature_name(str(feature)))
                shadow = _maybe_warn_feature_shadow(str(feature), pack_id_set)
                if shadow:
                    diagnostics.append(shadow)

        requires = []
        requires_block = manifest.get("requires")
        if isinstance(requires_block, dict):
            raw_requires = requires_block.get("packs")
            requires = (
                [str(item) for item in raw_requires]
                if isinstance(raw_requires, list)
                else []
            )
        for req in requires:
            if req not in pack_ids:
                diagnostics.append(
                    Diagnostic(
                        code="PACK_MISSING_REQUIRED",
                        rule="pack.requires.packs",
                        severity=Severity.ERROR,
                        message=f"Pack {pack_id} requires missing pack {req}",
                    )
                )

    selection = lock.get("selection") if isinstance(lock.get("selection"), dict) else {}
    services = (
        _get_list(selection.get("services")) if isinstance(selection, dict) else []
    )
    reserved = project_reserved_services(lock)
    for svc in services:
        svc_name = str(svc)
        diagnostics.extend(
            validate_service_name(svc_name, BUILTIN_RESERVED_SERVICES, reserved)
        )
        svc_root = repo_path / "services" / svc_name
        if not svc_root.exists():
            diagnostics.append(
                Diagnostic(
                    code="REPO_SERVICE_MISSING",
                    rule="repo.service.exists",
                    severity=Severity.ERROR,
                    message=f"Service directory missing: {svc_name}",
                    location=FileLocation(str(svc_root)),
                )
            )
            continue
        if "pantsagon.python" in pack_ids:
            for layer in ("domain", "ports", "application", "adapters", "entrypoints"):
                layer_path = svc_root / layer
                if not layer_path.exists():
                    diagnostics.append(
                        Diagnostic(
                            code="REPO_LAYER_MISSING",
                            rule="repo.layer.exists",
                            severity=Severity.ERROR,
                            message=f"Missing layer directory {layer} for service {svc_name}",
                            location=FileLocation(str(layer_path)),
                        )
                    )

    if isinstance(selection, dict):
        languages = [str(item) for item in _get_list(selection.get("languages"))]
        features = [str(item) for item in _get_list(selection.get("features"))]
        for feature in features:
            diagnostics.extend(validate_feature_name(feature))
            shadow = _maybe_warn_feature_shadow(feature, pack_id_set)
            if shadow:
                diagnostics.append(shadow)
        index_path = _bundled_packs_root() / "_index.json"
        if index_path.exists():
            index = load_pack_index(index_path)
            selection_result = resolve_pack_ids(
                index, languages=languages, features=features
            )
            diagnostics.extend(selection_result.diagnostics)
            expected = set(selection_result.value or [])
            if expected:
                missing = sorted(expected - set(pack_ids))
                extra = sorted(set(pack_ids) - expected)
                if missing or extra:
                    diagnostics.append(
                        Diagnostic(
                            code="LOCK_SELECTION_MISMATCH",
                            rule="lock.selection",
                            severity=Severity.WARN,
                            message="Selection does not match resolved pack set",
                            details={"missing": missing, "extra": extra},
                        )
                    )

    return Result(diagnostics=apply_strictness(diagnostics, strict_enabled))
