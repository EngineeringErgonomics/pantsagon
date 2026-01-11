from pantsagon.adapters.workspace.filesystem import FilesystemWorkspace


def test_workspace_commit_writes_files(tmp_path):
    ws = FilesystemWorkspace(tmp_path)
    stage = ws.begin_transaction()
    (stage / "hello.txt").write_text("hi")
    ws.commit(stage)
    assert (tmp_path / "hello.txt").read_text() == "hi"
