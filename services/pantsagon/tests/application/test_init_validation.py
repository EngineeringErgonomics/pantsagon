from pantsagon.application.init_repo import init_repo


def test_init_rejects_invalid_service_name(tmp_path):
    result = init_repo(
        repo_path=tmp_path,
        languages=["python"],
        services=["bad--name"],
        features=[],
        renderer="copier",
    )
    assert any(d.code == "SERVICE_NAME_INVALID" for d in result.diagnostics)
