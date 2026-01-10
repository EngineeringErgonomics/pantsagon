from pantsagon.application.init_repo import init_repo


def test_init_repo_writes_lock(tmp_path):
    init_repo(
        repo_path=tmp_path,
        languages=["python"],
        services=["monitors"],
        features=["openapi"],
        renderer="copier",
    )
    assert (tmp_path / ".pantsagon.toml").exists()
