from pathlib import Path


def test_repo_layout_basics_exist() -> None:
    root = Path(__file__).resolve().parents[3]
    assert (root / "pants.toml").exists()
    assert (root / "3rdparty/python/requirements.txt").exists()
    assert (root / "shared/contracts/schemas/pack.schema.v1.json").exists()
