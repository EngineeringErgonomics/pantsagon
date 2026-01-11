from pathlib import Path

from pantsagon.adapters.policy.pack_validator import PackPolicyEngine
from pantsagon.application.pack_validation import validate_pack


def test_all_bundled_packs_validate():
    root = Path(__file__).resolve().parents[4]
    packs_dir = root / "packs"
    engine = PackPolicyEngine()
    for pack in ["core", "python", "openapi", "docker"]:
        result = validate_pack(packs_dir / pack, engine)
        assert not [d for d in result.diagnostics if d.severity.value == "error"]
