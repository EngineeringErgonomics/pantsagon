from pantsagon.application.validate_repo import validate_repo


def test_validate_repo_missing_lock(tmp_path):
    result = validate_repo(repo_path=tmp_path)
    assert any(d.code == "LOCK_MISSING" for d in result.diagnostics)
