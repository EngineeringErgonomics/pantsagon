from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from pantsagon.domain.json_types import JsonDict
from pantsagon.domain.pack import PackRef


@dataclass
class RenderRequest:
    pack: PackRef
    pack_path: Path
    staging_dir: Path
    answers: JsonDict
    allow_hooks: bool


@dataclass
class RenderOutcome:
    rendered_paths: list[Path]
    warnings: list[str]


class RendererPort(Protocol):
    def render(self, request: RenderRequest) -> RenderOutcome: ...
