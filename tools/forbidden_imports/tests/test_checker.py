from pathlib import Path

from forbidden_imports.checker import load_config, scan_files


def test_ports_reject_framework_import(tmp_path: Path) -> None:
    cfg = tmp_path / "forbidden_imports.yaml"
    cfg.write_text(
        "languages:\n"
        "  python:\n"
        "    extensions: ['.py']\n"
        "    layers:\n"
        "      ports:\n"
        "        include: ['ports/*.py']\n"
        "        deny: ['fastapi', 'requests']\n"
    )
    bad = tmp_path / "ports" / "bad.py"
    bad.parent.mkdir(parents=True)
    bad.write_text("import fastapi\n")

    config = load_config(cfg)
    violations = scan_files(config, [bad], languages=["python"])
    assert violations, "Expected a violation for ports layer"


def test_typescript_rejects_import(tmp_path: Path) -> None:
    cfg = tmp_path / "forbidden_imports.yaml"
    cfg.write_text(
        "languages:\n"
        "  typescript:\n"
        "    extensions: ['.ts']\n"
        "    layers:\n"
        "      domain:\n"
        "        include: ['domain/*.ts']\n"
        "        deny: ['axios']\n"
    )
    bad = tmp_path / "domain" / "bad.ts"
    bad.parent.mkdir(parents=True)
    bad.write_text("import axios from 'axios'\\n")

    config = load_config(cfg)
    violations = scan_files(config, [bad], languages=["typescript"])
    assert violations, "Expected a violation for TypeScript domain layer"


def test_rust_rejects_import(tmp_path: Path) -> None:
    cfg = tmp_path / "forbidden_imports.yaml"
    cfg.write_text(
        "languages:\n"
        "  rust:\n"
        "    extensions: ['.rs']\n"
        "    layers:\n"
        "      domain:\n"
        "        include: ['domain/*.rs']\n"
        "        deny: ['reqwest']\n"
    )
    bad = tmp_path / "domain" / "bad.rs"
    bad.parent.mkdir(parents=True)
    bad.write_text("use reqwest::Client;\\n")

    config = load_config(cfg)
    violations = scan_files(config, [bad], languages=["rust"])
    assert violations, "Expected a violation for Rust domain layer"


def test_go_rejects_import(tmp_path: Path) -> None:
    cfg = tmp_path / "forbidden_imports.yaml"
    cfg.write_text(
        "languages:\n"
        "  go:\n"
        "    extensions: ['.go']\n"
        "    layers:\n"
        "      domain:\n"
        "        include: ['domain/*.go']\n"
        "        deny: ['net/http']\n"
    )
    bad = tmp_path / "domain" / "bad.go"
    bad.parent.mkdir(parents=True)
    bad.write_text('package domain\nimport "net/http"\n')

    config = load_config(cfg)
    violations = scan_files(config, [bad], languages=["go"])
    assert violations, "Expected a violation for Go domain layer"
