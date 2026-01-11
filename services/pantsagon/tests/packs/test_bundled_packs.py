from pathlib import Path
import os

import pytest

from pantsagon.adapters.policy.pack_validator import PackPolicyEngine
from pantsagon.application.pack_validation import validate_pack


def _repo_root() -> Path:
    buildroot = os.environ.get("PANTS_BUILDROOT")
    if buildroot:
        return Path(buildroot)
    for parent in Path(__file__).resolve().parents:
        if (parent / "pants.toml").exists() and (parent / "packs").is_dir():
            return parent
    pytest.skip("Could not locate repo root")
    return Path(".")


def _packs_root(root: Path) -> Path:
    packs_dir = root / "packs"
    if packs_dir.is_dir():
        return packs_dir
    for child in root.iterdir():
        if child.is_dir() and (child / "pack.yaml").is_file():
            return root
    pytest.skip("Could not locate bundled packs")
    return root


def test_all_bundled_packs_validate():
    root = _repo_root()
    packs_dir = _packs_root(root)
    engine = PackPolicyEngine()
    for pack in ["core", "python", "openapi", "docker"]:
        result = validate_pack(packs_dir / pack, engine)
        assert not [d for d in result.diagnostics if d.severity.value == "error"]
