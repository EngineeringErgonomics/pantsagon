from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import yaml

from pantsagon.domain.diagnostics import Diagnostic, Severity

SCHEMA_PATH = Path(__file__).resolve().parents[3] / "schemas" / "pack.schema.v1.json"


def load_manifest(pack_dir: Path) -> dict:
    return yaml.safe_load((pack_dir / "pack.yaml").read_text()) or {}


def load_copier_vars(pack_dir: Path) -> set[str]:
    data = yaml.safe_load((pack_dir / "copier.yml").read_text()) or {}
    return {k for k in data.keys() if not k.startswith("_")}


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


def crosscheck_variables(manifest: dict, copier_vars: set[str]) -> list[Diagnostic]:
    declared = {v["name"] for v in manifest.get("variables", [])}
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
