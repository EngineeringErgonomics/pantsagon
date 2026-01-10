from pantsagon.application.validate_repo import validate_repo


def test_validate_repo_missing_lock(tmp_path):
    result = validate_repo(repo_path=tmp_path)
    assert any(d.code == "LOCK_MISSING" for d in result.diagnostics)


def test_validate_repo_invalid_lock(tmp_path):
    (tmp_path / ".pantsagon.toml").write_text("not=toml:::")
    result = validate_repo(repo_path=tmp_path)
    assert any(d.code == "LOCK_INVALID" for d in result.diagnostics)
