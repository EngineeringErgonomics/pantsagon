from pathlib import Path
from typing import Any, cast

import yaml

from pantsagon.domain.pack import PackRef


class BundledPackCatalog:
    def __init__(self, root: Path) -> None:
        self.root = root

    def get_pack_path(self, pack: PackRef) -> Path:
        return self.root / pack.id.split(".")[-1]

    def load_manifest(self, pack_path: Path) -> dict[str, Any]:
        raw: object = yaml.safe_load((pack_path / "pack.yaml").read_text()) or {}
        if isinstance(raw, dict):
            return cast(dict[str, Any], raw)
        return {}
