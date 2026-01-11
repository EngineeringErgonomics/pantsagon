from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import jsonschema
import yaml

from pantsagon.domain.diagnostics import Diagnostic, Severity
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


def load_copier_vars(pack_dir: Path) -> set[str]:
    raw: object = yaml.safe_load((pack_dir / "copier.yml").read_text()) or {}
    data: dict[str, Any] = cast(dict[str, Any], raw) if isinstance(raw, dict) else {}
    return {k for k in data.keys() if not k.startswith("_")}


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


def crosscheck_variables(manifest: Manifest, copier_vars: set[str]) -> list[Diagnostic]:
    raw_variables: object = manifest.get("variables", [])
    variables: list[dict[str, Any]] = []
    if isinstance(raw_variables, list):
        for item in cast(list[object], raw_variables):
            if isinstance(item, dict):
                variables.append(cast(dict[str, Any], item))
    declared = {str(v.get("name")) for v in variables if v.get("name") is not None}
    diagnostics: list[Diagnostic] = []
    undeclared = copier_vars - declared
    for var in sorted(undeclared):
        diagnostics.append(
            Diagnostic(
                code="PACK_COPIER_UNDECLARED_VAR",
                rule="pack.copier",
                severity=Severity.ERROR,
                message=f"Undeclared variable: {var}",
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
        diagnostics.extend(crosscheck_variables(manifest, copier_vars))
        return Result(value=manifest, diagnostics=diagnostics)
