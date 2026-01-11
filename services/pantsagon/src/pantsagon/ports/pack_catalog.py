from pathlib import Path
from typing import Any, Protocol

from pantsagon.domain.pack import PackRef


class PackCatalogPort(Protocol):
    def get_pack_path(self, pack: PackRef) -> Path: ...

    def load_manifest(self, pack_path: Path) -> dict[str, Any]: ...
