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
