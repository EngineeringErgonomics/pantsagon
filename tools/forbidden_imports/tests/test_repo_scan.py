from pathlib import Path

from forbidden_imports.checker import load_config, scan_tree


def test_repo_has_no_forbidden_imports() -> None:
    root = Path(__file__).resolve().parents[3]
    config = load_config(root / "tools/forbidden_imports/forbidden_imports.yaml")
    violations = scan_tree(config, root, languages=["python"])
    assert not violations, "\n" + "\n".join(violations)
