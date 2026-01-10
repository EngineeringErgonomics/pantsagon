from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from pantsagon.domain.pack import PackRef


@dataclass
class RenderRequest:
    pack: PackRef
    pack_path: Path
    staging_dir: Path
    answers: dict
    allow_hooks: bool


@dataclass
class RenderOutcome:
    rendered_paths: list[Path]
    warnings: list[str]


class RendererPort(Protocol):
    def render(self, request: RenderRequest) -> RenderOutcome: ...
