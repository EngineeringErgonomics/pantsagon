from pantsagon.application.add_service import add_service


def test_add_service_fails_on_existing(tmp_path):
    (tmp_path / ".pantsagon.toml").write_text("")
    svc_dir = tmp_path / "services" / "foo"
    svc_dir.mkdir(parents=True)
    result = add_service(repo_path=tmp_path, name="foo", lang="python")
    assert any(d.code == "SERVICE_EXISTS" for d in result.diagnostics)


def test_add_service_rejects_reserved(tmp_path):
    (tmp_path / ".pantsagon.toml").write_text(
        "[settings.naming]\nreserved_services=['api']\n"
    )
    result = add_service(repo_path=tmp_path, name="api", lang="python")
    assert any(d.code == "SERVICE_NAME_RESERVED" for d in result.diagnostics)
