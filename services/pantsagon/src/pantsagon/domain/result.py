from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

from pantsagon.domain.diagnostics import Diagnostic, Severity

T = TypeVar("T")


@dataclass
class Result(Generic[T]):
    value: T | None = None
    diagnostics: list[Diagnostic] = field(default_factory=list)
    artifacts: list[dict[str, Any]] = field(default_factory=list)

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
