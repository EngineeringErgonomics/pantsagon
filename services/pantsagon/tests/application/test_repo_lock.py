import tomllib

from pantsagon.application.repo_lock import read_lock, write_lock


def test_read_lock_missing(tmp_path):
    result = read_lock(tmp_path / ".pantsagon.toml")
    assert any(d.code == "LOCK_MISSING" for d in result.diagnostics)


def test_write_lock_roundtrip(tmp_path):
    lock = {
        "tool": {"name": "pantsagon", "version": "0.1.0"},
        "settings": {
            "renderer": "copier",
            "strict": False,
            "strict_manifest": True,
            "allow_hooks": False,
        },
        "selection": {
            "languages": ["python"],
            "features": ["openapi"],
            "services": ["svc"],
            "augmented_coding": "none",
        },
        "resolved": {
            "packs": [{"id": "pantsagon.core", "version": "1.0.0", "source": "bundled"}],
            "answers": {"repo_name": "demo"},
        },
    }
    path = tmp_path / ".pantsagon.toml"
    write_lock(path, lock)
    parsed = tomllib.loads(path.read_text(encoding="utf-8"))
    assert parsed["tool"]["name"] == "pantsagon"
    assert parsed["resolved"]["packs"][0]["id"] == "pantsagon.core"
