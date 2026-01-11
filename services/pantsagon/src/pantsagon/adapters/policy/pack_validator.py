from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import jsonschema
import yaml

from pantsagon.domain.diagnostics import Diagnostic, Severity, ValueLocation
from pantsagon.domain.naming import (
    validate_feature_name,
    validate_pack_id as validate_pack_id_format,
    validate_variable_name,
)
from pantsagon.domain.result import Result
from pantsagon.ports.policy_engine import PolicyEnginePort

Manifest = dict[str, Any]


def _schema_path(root: Path | None = None) -> Path:
    base = root or Path.cwd()
    return base / "shared/contracts/schemas/pack.schema.v1.json"


SCHEMA_PATH = _schema_path()


def load_manifest(pack_dir: Path) -> Manifest:
    raw: object = yaml.safe_load((pack_dir / "pack.yaml").read_text()) or {}
    if isinstance(raw, dict):
        return cast(Manifest, raw)
    return {}


def load_copier_vars(pack_dir: Path) -> dict[str, Any]:
    raw: object = yaml.safe_load((pack_dir / "copier.yml").read_text()) or {}
    data: dict[str, Any] = cast(dict[str, Any], raw) if isinstance(raw, dict) else {}
    return {k: v for k, v in data.items() if not k.startswith("_")}


def validate_manifest_schema(manifest: Manifest) -> list[Diagnostic]:
    schema_raw = json.loads(SCHEMA_PATH.read_text())
    schema: dict[str, Any] = (
        cast(dict[str, Any], schema_raw) if isinstance(schema_raw, dict) else {}
    )
    try:
        jsonschema.validate(manifest, schema)
        return []
    except jsonschema.ValidationError as e:
        return [
            Diagnostic(
                code="PACK_SCHEMA_INVALID",
                rule="pack.schema",
                severity=Severity.ERROR,
                message=str(e),
            )
        ]


def _copier_default(value: Any) -> Any | None:
    if isinstance(value, dict):
        return value.get("default")
    return value


def validate_pack_id(manifest: Manifest) -> list[Diagnostic]:
    pack_id = str(manifest.get("id") or "").strip()
    if not pack_id:
        return []
    return validate_pack_id_format(pack_id)


def validate_feature_names(manifest: Manifest) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    provides = manifest.get("provides", {}) or {}
    features = provides.get("features", []) or []
    for feature in features:
        diagnostics.extend(validate_feature_name(str(feature)))
    return diagnostics


def validate_variable_names(manifest: Manifest) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    raw_variables: object = manifest.get("variables", [])
    if isinstance(raw_variables, list):
        for item in cast(list[object], raw_variables):
            if isinstance(item, dict):
                name = str(item.get("name", ""))
                diagnostics.extend(validate_variable_name(name))
    return diagnostics


def crosscheck_variables(manifest: Manifest, copier_vars: dict[str, Any]) -> list[Diagnostic]:
    raw_variables: object = manifest.get("variables", [])
    variables: list[dict[str, Any]] = []
    if isinstance(raw_variables, list):
        for item in cast(list[object], raw_variables):
            if isinstance(item, dict):
                variables.append(cast(dict[str, Any], item))
    declared = {str(v.get("name")) for v in variables if v.get("name") is not None}
    diagnostics: list[Diagnostic] = []
    undeclared = set(copier_vars.keys()) - declared
    for var in sorted(undeclared):
        diagnostics.append(
            Diagnostic(
                code="COPIER_UNDECLARED_VARIABLE",
                rule="pack.variables.copier_undeclared",
                severity=Severity.ERROR,
                message=f"Undeclared variable: {var}",
                location=ValueLocation("variable", var),
            )
        )
    for name in sorted(declared):
        pack_default = None
        raw_variables: object = manifest.get("variables", [])
        if isinstance(raw_variables, list):
            for item in cast(list[object], raw_variables):
                if isinstance(item, dict) and item.get("name") == name:
                    pack_default = item.get("default")
                    break
        copier_default = _copier_default(copier_vars.get(name)) if name in copier_vars else None
        if pack_default is not None and copier_default is not None and copier_default != pack_default:
            diagnostics.append(
                Diagnostic(
                    code="COPIER_DEFAULT_MISMATCH",
                    rule="pack.variables.default_mismatch",
                    severity=Severity.WARN,
                    message=f"Default mismatch for variable: {name}",
                    location=ValueLocation("variable", name),
                    upgradeable=True,
                )
            )
    return diagnostics


class PackPolicyEngine(PolicyEnginePort):
    def validate_repo(self, repo_path: Path) -> Result[None]:
        return Result()

    def validate_pack(self, pack_path: Path) -> Result[Manifest]:
        manifest = load_manifest(pack_path)
        copier_vars = load_copier_vars(pack_path)
        diagnostics: list[Diagnostic] = []
        diagnostics.extend(validate_manifest_schema(manifest))
        diagnostics.extend(validate_pack_id(manifest))
        diagnostics.extend(validate_feature_names(manifest))
        diagnostics.extend(validate_variable_names(manifest))
        diagnostics.extend(crosscheck_variables(manifest, copier_vars))
        return Result(value=manifest, diagnostics=diagnostics)
