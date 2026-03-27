from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import yaml

from pantsagon.domain.diagnostics import Diagnostic, Severity, ValueLocation
from pantsagon.domain.json_types import JsonDict, JsonValue, as_json_dict, as_json_list
from pantsagon.domain.naming import (
    validate_feature_name,
    validate_pack_id as validate_pack_id_format,
    validate_variable_name,
)
from pantsagon.domain.result import Result
from pantsagon.ports.policy_engine import PolicyEnginePort

Manifest = JsonDict


def schema_path(root: Path | None = None) -> Path:
    return _schema_path(root)


def _schema_path(root: Path | None = None) -> Path:
    base = root or Path.cwd()
    return base / "shared/contracts/schemas/pack.schema.v1.json"


SCHEMA_PATH = _schema_path()


def load_manifest(pack_dir: Path) -> Manifest:
    raw: object = yaml.safe_load((pack_dir / "pack.yaml").read_text()) or {}
    return as_json_dict(raw)


def load_copier_vars(pack_dir: Path) -> JsonDict:
    raw: object = yaml.safe_load((pack_dir / "copier.yml").read_text()) or {}
    data: JsonDict = {}
    for key, value in as_json_dict(raw).items():
        key_str = str(key)
        if key_str.startswith("_"):
            continue
        data[key_str] = value
    return data


def validate_manifest_schema(manifest: Manifest) -> list[Diagnostic]:
    schema_raw = json.loads(SCHEMA_PATH.read_text())
    schema = as_json_dict(schema_raw)
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


def _copier_default(value: JsonValue) -> JsonValue | None:
    if isinstance(value, dict):
        return value.get("default")
    return value


def _variables_list(manifest: Manifest) -> list[JsonDict]:
    variables: list[JsonDict] = []
    for item in as_json_list(manifest.get("variables")):
        if isinstance(item, dict):
            variables.append(as_json_dict(item))
    return variables


def validate_pack_id(manifest: Manifest) -> list[Diagnostic]:
    pack_id = str(manifest.get("id") or "").strip()
    if not pack_id:
        return []
    return validate_pack_id_format(pack_id)


def validate_feature_names(manifest: Manifest) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    provides = manifest.get("provides")
    if isinstance(provides, dict):
        features = provides.get("features")
        if isinstance(features, list):
            for feature in features:
                diagnostics.extend(validate_feature_name(str(feature)))
    return diagnostics


def validate_variable_names(manifest: Manifest) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for item in _variables_list(manifest):
        name = str(item.get("name", ""))
        diagnostics.extend(validate_variable_name(name))
    return diagnostics


def crosscheck_variables(manifest: Manifest, copier_vars: JsonDict) -> list[Diagnostic]:
    variables = _variables_list(manifest)
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
        for item in variables:
            if item.get("name") == name:
                pack_default = item.get("default")
                break
        copier_default = (
            _copier_default(copier_vars.get(name)) if name in copier_vars else None
        )
        if (
            pack_default is not None
            and copier_default is not None
            and copier_default != pack_default
        ):
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
