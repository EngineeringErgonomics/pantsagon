from pantsagon.application.pack_validation import validate_pack


def test_manifest_schema_validation(tmp_path):
    pack = tmp_path / "pack"
    pack.mkdir()
    (pack / "pack.yaml").write_text("id: x\nversion: 1.0.0\n")
    (pack / "copier.yml").write_text("_min_copier_version: '9.0'\n")
    result = validate_pack(pack)
    assert any(d.code == "PACK_SCHEMA_INVALID" for d in result.diagnostics)
