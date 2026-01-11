from pathlib import Path

from pantsagon.adapters.policy.pack_validator import PackPolicyEngine, _schema_path
from pantsagon.application.pack_validation import validate_pack


def test_schema_path_points_to_shared_contracts() -> None:
    root = Path(__file__).resolve().parents[4]
    assert (
        _schema_path(root)
        .as_posix()
        .endswith("shared/contracts/schemas/pack.schema.v1.json")
    )


def test_manifest_schema_validation(tmp_path):
    pack = tmp_path / "pack"
    pack.mkdir()
    (pack / "pack.yaml").write_text("id: x\nversion: 1.0.0\n")
    (pack / "copier.yml").write_text("_min_copier_version: '9.0'\n")
    engine = PackPolicyEngine()
    result = validate_pack(pack, engine)
    assert any(d.code == "PACK_SCHEMA_INVALID" for d in result.diagnostics)
