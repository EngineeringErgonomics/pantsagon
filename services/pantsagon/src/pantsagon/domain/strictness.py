from __future__ import annotations

from dataclasses import replace

from pantsagon.domain.diagnostics import Diagnostic, Severity


def apply_strictness(diagnostics: list[Diagnostic], strict: bool) -> list[Diagnostic]:
    if not strict:
        return diagnostics
    upgraded: list[Diagnostic] = []
    for d in diagnostics:
        if d.severity == Severity.WARN and d.upgradeable:
            upgraded.append(replace(d, severity=Severity.ERROR))
        else:
            upgraded.append(d)
    return upgraded
