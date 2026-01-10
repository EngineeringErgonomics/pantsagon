from pathlib import Path
import os

import pytest


def _repo_root() -> Path:
    buildroot = os.environ.get("PANTS_BUILDROOT")
    if buildroot:
        return Path(buildroot)
    for parent in Path(__file__).resolve().parents:
        if (parent / "pants.toml").exists():
            return parent
    pytest.skip("Could not locate repo root")
    return Path(".")


def test_repo_layout_basics_exist() -> None:
    root = _repo_root()
    assert (root / "pants.toml").exists()
    assert (root / "3rdparty/python/requirements.txt").exists()
    assert (root / "shared/contracts/schemas/pack.schema.v1.json").exists()
    assert (root / "services/pantsagon/src/pantsagon/entrypoints/cli.py").exists()
    assert (root / "services/pantsagon/tests/packs/test_bundled_packs.py").exists()
    assert (root / "services/pantsagon/src/pantsagon/domain/BUILD").exists()
    assert (root / "packs/BUILD").exists()
