from pathlib import Path

from forbidden_imports.checker import load_config, scan_files


def test_ports_reject_framework_import(tmp_path: Path) -> None:
    cfg = tmp_path / "forbidden_imports.yaml"
    cfg.write_text(
        "layers:\n"
        "  ports:\n"
        "    include: ['ports/*.py']\n"
        "    deny: ['fastapi', 'requests']\n"
    )
    bad = tmp_path / "ports" / "bad.py"
    bad.parent.mkdir(parents=True)
    bad.write_text("import fastapi\n")

    config = load_config(cfg)
    violations = scan_files(config, [bad])
    assert violations, "Expected a violation for ports layer"
