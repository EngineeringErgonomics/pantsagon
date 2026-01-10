from pantsagon.application.pack_validation import validate_pack


def test_default_mismatch_warns(tmp_path):
    pack = tmp_path / "pack"
    pack.mkdir()
    (pack / "pack.yaml").write_text(
        "id: pantsagon.core\nversion: 1.0.0\ncompatibility: {pants: '>=2.0.0'}\n"
        "variables: [{name: repo_name, type: string, default: repo}]\n"
    )
    (pack / "copier.yml").write_text("repo_name: {type: str, default: other}\n")
    result = validate_pack(pack)
    assert any(d.code == "COPIER_DEFAULT_MISMATCH" for d in result.diagnostics)
