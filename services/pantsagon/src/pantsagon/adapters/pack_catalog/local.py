from pathlib import Path
from typing import Any, cast

import yaml


class LocalPackCatalog:
    def load_manifest(self, pack_dir: Path) -> dict[str, Any]:
        raw: object = yaml.safe_load((pack_dir / "pack.yaml").read_text()) or {}
        if isinstance(raw, dict):
            return cast(dict[str, Any], raw)
        return {}
