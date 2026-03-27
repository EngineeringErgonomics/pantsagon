from pantsagon.application.add_service import add_service


def test_add_service_rejects_bad_name(tmp_path):
    (tmp_path / ".pantsagon.toml").write_text("")
    result = add_service(repo_path=tmp_path, name="BadName", lang="python")
    assert any(d.code == "SERVICE_NAME_INVALID" for d in result.diagnostics)
