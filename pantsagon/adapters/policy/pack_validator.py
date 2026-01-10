from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema
import yaml

from pantsagon.domain.diagnostics import Diagnostic, Severity, ValueLocation
from pantsagon.domain.naming import (
    validate_feature_name,
    validate_pack_id as validate_pack_id_format,
    validate_variable_name,
)

SCHEMA_PATH = Path(__file__).resolve().parents[3] / "schemas" / "pack.schema.v1.json"


def load_manifest(pack_dir: Path) -> dict:
    return yaml.safe_load((pack_dir / "pack.yaml").read_text()) or {}


def load_copier_vars(pack_dir: Path) -> dict[str, Any]:
    data = yaml.safe_load((pack_dir / "copier.yml").read_text()) or {}
    return {k: v for k, v in data.items() if not k.startswith("_")}


def validate_manifest_schema(manifest: dict) -> list[Diagnostic]:
    schema = json.loads(SCHEMA_PATH.read_text())
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


def validate_pack_id(manifest: dict) -> list[Diagnostic]:
    pack_id = (manifest.get("id") or "").strip()
    if not pack_id:
        return []
    return validate_pack_id_format(pack_id)


def validate_feature_names(manifest: dict) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    provides = manifest.get("provides", {}) or {}
    features = provides.get("features", []) or []
    for feature in features:
        diagnostics.extend(validate_feature_name(str(feature)))
    return diagnostics


def validate_variable_names(manifest: dict) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    variables = manifest.get("variables", []) or []
    for var in variables:
        name = str(var.get("name", ""))
        diagnostics.extend(validate_variable_name(name))
    return diagnostics


def crosscheck_variables(manifest: dict, copier_vars: dict[str, Any]) -> list[Diagnostic]:
    declared = {v.get("name") for v in manifest.get("variables", []) if v.get("name")}
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
        for var in manifest.get("variables", []) or []:
            if var.get("name") == name:
                pack_default = var.get("default")
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
