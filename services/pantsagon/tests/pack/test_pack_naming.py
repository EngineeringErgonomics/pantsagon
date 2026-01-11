from pantsagon.adapters.policy.pack_validator import PackPolicyEngine
from pantsagon.application.pack_validation import validate_pack


def test_pack_id_must_be_namespaced(tmp_path):
    pack = tmp_path / "pack"
    pack.mkdir()
    (pack / "pack.yaml").write_text(
        "id: bad\nversion: 1.0.0\ncompatibility: {pants: '>=2.0.0'}\n"
    )
    (pack / "copier.yml").write_text("_min_copier_version: '9.0'\n")
    engine = PackPolicyEngine()
    result = validate_pack(pack, engine)
    assert any(d.code == "PACK_ID_INVALID" for d in result.diagnostics)
