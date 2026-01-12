from pantsagon.adapters.workspace.filesystem import FilesystemWorkspace


def test_workspace_rollback_on_error(tmp_path, monkeypatch):
    ws = FilesystemWorkspace(tmp_path)
    stage = ws.begin_transaction()
    (stage / "file.txt").write_text("data")
    monkeypatch.setattr(ws, "_copy_file", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")))
    try:
        ws.commit(stage)
    except Exception:
        pass
    assert not (tmp_path / "file.txt").exists()


def test_workspace_restores_overwritten_file(tmp_path, monkeypatch):
    ws = FilesystemWorkspace(tmp_path)
    target = tmp_path / "file.txt"
    target.write_text("old")
    stage = ws.begin_transaction()
    (stage / "file.txt").write_text("new")
    (stage / "other.txt").write_text("data")
    original_copy = ws._copy_file
    calls = {"count": 0}

    def _flaky_copy(src, dest):
        calls["count"] += 1
        if calls["count"] == 2:
            raise RuntimeError("boom")
        return original_copy(src, dest)

    monkeypatch.setattr(ws, "_copy_file", _flaky_copy)
    try:
        ws.commit(stage)
    except Exception:
        pass
    assert target.read_text() == "old"
