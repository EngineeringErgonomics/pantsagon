from pathlib import Path

from pantsagon.application.pack_validation import validate_pack


def test_all_bundled_packs_validate():
    packs_dir = Path(__file__).resolve().parents[2] / "packs"
    for pack in ["core", "python", "openapi", "docker"]:
        result = validate_pack(packs_dir / pack)
        assert not [d for d in result.diagnostics if d.severity.value == "error"]
