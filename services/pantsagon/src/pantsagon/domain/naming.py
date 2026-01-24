from __future__ import annotations

import keyword
import re

from pantsagon.domain.diagnostics import Diagnostic, Severity, ValueLocation
from pantsagon.domain.json_types import as_json_dict

SERVICE_PATTERN = re.compile(r"^[a-z](?:[a-z0-9]*(-[a-z0-9]+)*)$")
PACK_ID_PATTERN = re.compile(r"^[a-z][a-z0-9-]*(\.[a-z][a-z0-9-]*)+$")
FEATURE_PATTERN = re.compile(r"^[a-z][a-z0-9_-]*$")
VARIABLE_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

BUILTIN_RESERVED_SERVICES = {
    "services",
    "shared",
    "tools",
    "docs",
    "packs",
    "schemas",
    "infra",
    "tests",
    "domain",
    "ports",
    "application",
    "adapters",
    "entrypoints",
    "pantsagon",
    "core",
    "foundation",
    *keyword.kwlist,
}


def validate_service_name(
    name: str, builtins: set[str], project: set[str]
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    if not SERVICE_PATTERN.match(name):
        diagnostics.append(
            Diagnostic(
                code="SERVICE_NAME_INVALID",
                rule="naming.service.format",
                severity=Severity.ERROR,
                message=f"Invalid service name: {name}",
                location=ValueLocation("service", name),
            )
        )
        return diagnostics
    if name in builtins:
        diagnostics.append(
            Diagnostic(
                code="SERVICE_NAME_RESERVED",
                rule="naming.service.reserved",
                severity=Severity.ERROR,
                message=f"Service name is reserved: {name}",
                location=ValueLocation("service", name),
                details=as_json_dict({"scope": "builtin"}),
            )
        )
    if name in project:
        diagnostics.append(
            Diagnostic(
                code="SERVICE_NAME_RESERVED",
                rule="naming.service.reserved",
                severity=Severity.ERROR,
                message=f"Service name is reserved: {name}",
                location=ValueLocation("service", name),
                details=as_json_dict({"scope": "project"}),
            )
        )
    return diagnostics


def validate_pack_id(pack_id: str) -> list[Diagnostic]:
    if PACK_ID_PATTERN.match(pack_id):
        return []
    return [
        Diagnostic(
            code="PACK_ID_INVALID",
            rule="naming.pack.id",
            severity=Severity.ERROR,
            message=f"Invalid pack id: {pack_id}",
            location=ValueLocation("pack.id", pack_id),
        )
    ]


def validate_feature_name(feature: str) -> list[Diagnostic]:
    if FEATURE_PATTERN.match(feature) and "." not in feature:
        return []
    return [
        Diagnostic(
            code="FEATURE_NAME_INVALID",
            rule="naming.feature.format",
            severity=Severity.ERROR,
            message=f"Invalid feature name: {feature}",
            location=ValueLocation("feature", feature),
        )
    ]


def validate_variable_name(name: str) -> list[Diagnostic]:
    if VARIABLE_PATTERN.match(name):
        return []
    return [
        Diagnostic(
            code="VARIABLE_NAME_INVALID",
            rule="naming.variable.format",
            severity=Severity.ERROR,
            message=f"Invalid variable name: {name}",
            location=ValueLocation("variable", name),
        )
    ]
