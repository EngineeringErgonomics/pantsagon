from pathlib import Path
from typing import Any

from pantsagon.domain.result import Result


def _minimal_toml(lock: dict[str, Any]) -> str:
    tool_raw = lock.get("tool", {})
    tool: dict[str, Any] = tool_raw if isinstance(tool_raw, dict) else {}
    name = str(tool.get("name", ""))
    version = str(tool.get("version", ""))
    return f"[tool]\nname='{name}'\nversion='{version}'\n"


def init_repo(
    repo_path: Path,
    languages: list[str],
    services: list[str],
    features: list[str],
    renderer: str,
    augmented_coding: str | None = None,
) -> Result[None]:
    lock: dict[str, Any] = {
        "tool": {"name": "pantsagon", "version": "0.1.0"},
        "settings": {
            "renderer": renderer,
            "strict": False,
            "strict_manifest": True,
            "allow_hooks": False,
        },
        "selection": {
            "languages": languages,
            "features": features,
            "services": services,
            "augmented_coding": augmented_coding or "none",
        },
        "resolved": {"packs": [], "answers": {}},
    }
    content = _minimal_toml(lock)
    (repo_path / ".pantsagon.toml").write_text(content)
    # Minimal core file for now; later replaced by rendered pack output.
    (repo_path / "pants.toml").write_text('[GLOBAL]\npants_version = "2.30.0"\n')

    augmented = augmented_coding or "none"
    if augmented == "agents":
        (repo_path / "AGENTS.md").write_text("# AGENTS\n")
    elif augmented == "claude":
        (repo_path / "CLAUDE.md").write_text("# CLAUDE\n")
    elif augmented == "gemini":
        (repo_path / "GEMINI.md").write_text("# GEMINI\n")
    return Result()
