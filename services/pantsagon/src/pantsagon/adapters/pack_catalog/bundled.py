from pathlib import Path

import yaml

from pantsagon.domain.json_types import JsonDict, as_json_dict
from pantsagon.domain.pack import PackRef


class BundledPackCatalog:
    def __init__(self, root: Path) -> None:
        self.root = root

    def get_pack_path(self, pack: PackRef) -> Path:
        return self.root / pack.id.split(".")[-1]

    def load_manifest(self, pack_path: Path) -> JsonDict:
        raw: object = yaml.safe_load((pack_path / "pack.yaml").read_text()) or {}
        return as_json_dict(raw)
