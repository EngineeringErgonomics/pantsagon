from pathlib import Path

import yaml


class LocalPackCatalog:
    def load_manifest(self, pack_dir: Path) -> dict:
        return yaml.safe_load((pack_dir / "pack.yaml").read_text()) or {}
