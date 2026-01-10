from pantsagon.application.pack_validation import validate_pack


def test_copier_crosscheck_detects_undeclared_var(tmp_path):
    pack = tmp_path / "pack"
    pack.mkdir()
    (pack / "pack.yaml").write_text("id: x\nversion: 1.0.0\nvariables: [{name: service_name, type: string}]\n")
    (pack / "copier.yml").write_text("service_name: {type: str}\nextra_var: {type: str}\n")
    result = validate_pack(pack)
    assert any(d.code == "COPIER_UNDECLARED_VARIABLE" for d in result.diagnostics)
