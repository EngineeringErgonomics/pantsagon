from pathlib import Path

from pantsagon.application.add_service import add_service
from pantsagon.application.repo_lock import write_lock


def _lock_with_source(source: object) -> dict[str, object]:
    return {
        "settings": {
            "renderer": "copier",
            "strict": False,
            "strict_manifest": True,
            "allow_hooks": False,
        },
        "selection": {
            "languages": ["python"],
            "features": [],
            "services": [],
            "augmented_coding": "none",
        },
        "resolved": {
            "packs": [
                {"id": "pantsagon.core", "version": "1.0.0", "source": source},
            ],
            "answers": {},
        },
    }


def test_add_service_rejects_non_string_pack_source(tmp_path: Path) -> None:
    write_lock(tmp_path / ".pantsagon.toml", _lock_with_source({"bad": "value"}))

    result = add_service(
        repo_path=tmp_path,
        name="monitor-cost",
        lang="python",
    )

    assert any(d.code == "LOCK_PACK_INVALID" for d in result.diagnostics)
