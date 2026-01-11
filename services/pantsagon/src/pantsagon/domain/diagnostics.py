from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
from typing import Any


class Severity(str, Enum):
    ERROR = "error"
    WARN = "warn"
    INFO = "info"


@dataclass(frozen=True)
class Location:
    kind: str


@dataclass(frozen=True)
class FileLocation(Location):
    path: str
    line: int | None = None
    col: int | None = None

    def __init__(self, path: str, line: int | None = None, col: int | None = None):
        object.__setattr__(self, "kind", "file")
        object.__setattr__(self, "path", path)
        object.__setattr__(self, "line", line)
        object.__setattr__(self, "col", col)


@dataclass(frozen=True)
class ValueLocation(Location):
    field: str
    value: str

    def __init__(self, field: str, value: str):
        object.__setattr__(self, "kind", "value")
        object.__setattr__(self, "field", field)
        object.__setattr__(self, "value", value)


@dataclass(frozen=True)
class Diagnostic:
    code: str
    rule: str
    severity: Severity
    message: str
    location: Location | None = None
    hint: str | None = None
    details: dict[str, Any] | None = None
    is_execution: bool = False
    upgradeable: bool = False
    id: str = field(init=False)

    def __post_init__(self) -> None:
        raw = f"{self.code}|{self.rule}|{self.severity}|{self.message}|{self.location}"
        object.__setattr__(self, "id", hashlib.sha256(raw.encode()).hexdigest()[:12])
