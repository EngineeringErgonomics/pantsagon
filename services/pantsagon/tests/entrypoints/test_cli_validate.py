from typer.testing import CliRunner

from pantsagon.entrypoints.cli import app


def test_cli_validate_exits_nonzero_when_lock_missing():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["validate", "--json"])
    assert result.exit_code != 0
