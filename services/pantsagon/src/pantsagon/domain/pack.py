from dataclasses import dataclass
from typing import Literal

PackSource = Literal["bundled", "local", "git", "registry"]


@dataclass(frozen=True)
class PackRef:
    id: str
    version: str
    source: PackSource
    location: str | None = None
    git_ref: str | None = None
    commit: str | None = None
    digest: str | None = None
    subdir: str | None = None
