import tomllib
from pathlib import Path

import tomli_w

from pantsagon.application.init_repo import init_repo
from pantsagon.application.validate_repo import validate_repo


def test_validate_repo_missing_lock(tmp_path):
    result = validate_repo(repo_path=tmp_path)
    assert any(d.code == "LOCK_MISSING" for d in result.diagnostics)


def test_validate_repo_invalid_lock(tmp_path):
    (tmp_path / ".pantsagon.toml").write_text("not=toml:::")
    result = validate_repo(repo_path=tmp_path)
    assert any(d.code == "LOCK_PARSE_FAILED" for d in result.diagnostics)


def test_validate_repo_missing_service_dir(tmp_path):
    init_repo(repo_path=tmp_path, languages=["python"], services=["missing"], features=[], renderer="copier")
    svc_dir = tmp_path / "services" / "missing"
    if svc_dir.exists():
        for path in sorted(svc_dir.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
        svc_dir.rmdir()
    result = validate_repo(repo_path=tmp_path)
    assert any(d.code == "REPO_SERVICE_MISSING" for d in result.diagnostics)


def test_validate_repo_pack_not_found(tmp_path):
    init_repo(repo_path=tmp_path, languages=["python"], services=["svc"], features=[], renderer="copier")
    lock_path = tmp_path / ".pantsagon.toml"
    lock = tomllib.loads(lock_path.read_text(encoding="utf-8"))
    lock["resolved"]["packs"][0]["id"] = "pantsagon.missing"
    lock_path.write_text(tomli_w.dumps(lock), encoding="utf-8")

    result = validate_repo(repo_path=tmp_path)
    assert any(d.code == "PACK_NOT_FOUND" for d in result.diagnostics)
