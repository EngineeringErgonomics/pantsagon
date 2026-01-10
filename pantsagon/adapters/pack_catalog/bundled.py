from pathlib import Path


class BundledPackCatalog:
    def __init__(self, root: Path) -> None:
        self.root = root

    def get_pack_path(self, pack_id: str) -> Path:
        return self.root / pack_id.split(".")[-1]
