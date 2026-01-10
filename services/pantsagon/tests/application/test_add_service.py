from pathlib import Path

from pantsagon.application.add_service import add_service


def test_add_service_fails_on_existing(tmp_path):
    (tmp_path / ".pantsagon.toml").write_text("[tool]\nname='pantsagon'\nversion='0.1.0'\n")
    svc_dir = tmp_path / "services" / "foo"
    svc_dir.mkdir(parents=True)
    result = add_service(repo_path=tmp_path, name="foo", lang="python")
    assert any(d.code == "SERVICE_EXISTS" for d in result.diagnostics)
