import tomllib

from pantsagon.application.init_repo import init_repo


def test_init_repo_writes_full_lock(tmp_path):
    init_repo(
        repo_path=tmp_path,
        languages=["python"],
        services=["monitors"],
        features=["openapi"],
        renderer="copier",
    )
    lock = tomllib.loads((tmp_path / ".pantsagon.toml").read_text(encoding="utf-8"))
    assert "tool" not in lock
    assert "settings" in lock
    assert "selection" in lock
    assert "resolved" in lock
    assert lock["resolved"]["packs"]
    assert "answers" in lock["resolved"]
