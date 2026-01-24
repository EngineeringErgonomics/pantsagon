from __future__ import annotations

from dataclasses import dataclass, field
from typing import Generic, TypeVar

from pantsagon.domain.diagnostics import Diagnostic, Severity
from pantsagon.domain.json_types import JsonDict

T = TypeVar("T")


def _new_diagnostics() -> list[Diagnostic]:
    return []


def _new_artifacts() -> list[JsonDict]:
    return []


@dataclass
class Result(Generic[T]):
    value: T | None = None
    diagnostics: list[Diagnostic] = field(default_factory=_new_diagnostics)
    artifacts: list[JsonDict] = field(default_factory=_new_artifacts)

    @property
    def exit_code(self) -> int:
        has_exec = any(
            d.is_execution and d.severity == Severity.ERROR for d in self.diagnostics
        )
        has_val = any(
            (not d.is_execution) and d.severity == Severity.ERROR
            for d in self.diagnostics
        )
        if has_exec:
            return 3
        if has_val:
            return 2
        return 0
