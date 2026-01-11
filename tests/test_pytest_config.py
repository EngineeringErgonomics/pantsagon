from pathlib import Path
import tomllib


def test_pytest_asyncio_loop_scope_is_configured() -> None:
    pyproject_path = Path(__file__).resolve().parents[1] / "pyproject.toml"
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    pytest_options = data.get("tool", {}).get("pytest", {}).get("ini_options", {})
    assert pytest_options.get("asyncio_default_fixture_loop_scope") == "function"
