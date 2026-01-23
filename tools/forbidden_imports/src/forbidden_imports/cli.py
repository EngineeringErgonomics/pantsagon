from __future__ import annotations

from forbidden_imports.checker import find_repo_root, load_config, load_languages, scan_tree


def main() -> int:
    root = find_repo_root()
    config_path = root / "tools" / "forbidden_imports" / "forbidden_imports.yaml"
    if not config_path.exists():
        print(f"forbidden imports config not found: {config_path}")
        return 2
    config = load_config(config_path)
    languages = load_languages(root / ".pantsagon.toml")
    violations = scan_tree(config, root, languages=languages)
    if violations:
        print("\n".join(violations))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
