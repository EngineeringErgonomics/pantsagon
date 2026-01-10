from pathlib import Path

from pantsagon.domain.result import Result


def _minimal_toml(lock: dict) -> str:
    tool = lock.get("tool", {})
    return f"[tool]\nname='{tool.get('name', '')}'\nversion='{tool.get('version', '')}'\n"


def init_repo(
    repo_path: Path,
    languages: list[str],
    services: list[str],
    features: list[str],
    renderer: str,
) -> Result[None]:
    lock = {
        "tool": {"name": "pantsagon", "version": "0.1.0"},
        "settings": {"renderer": renderer, "strict": False, "strict_manifest": True, "allow_hooks": False},
        "selection": {
            "languages": languages,
            "features": features,
            "services": services,
            "augmented_coding": "none",
        },
        "resolved": {"packs": [], "answers": {}},
    }
    try:
        import tomli_w
        content = tomli_w.dumps(lock)
    except ModuleNotFoundError:
        content = _minimal_toml(lock)
    (repo_path / ".pantsagon.toml").write_text(content)
    return Result()
