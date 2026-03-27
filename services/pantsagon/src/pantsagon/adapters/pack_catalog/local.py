from pathlib import Path

import yaml

from pantsagon.domain.json_types import JsonDict, as_json_dict


class LocalPackCatalog:
    def load_manifest(self, pack_dir: Path) -> JsonDict:
        raw: object = yaml.safe_load((pack_dir / "pack.yaml").read_text()) or {}
        return as_json_dict(raw)
