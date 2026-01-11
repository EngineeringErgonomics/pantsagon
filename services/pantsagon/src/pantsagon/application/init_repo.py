from pathlib import Path
from typing import Any

import shutil

from pantsagon.adapters.workspace.filesystem import FilesystemWorkspace
from pantsagon.application.rendering import render_bundled_packs
from pantsagon.domain.diagnostics import Severity
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
    workspace = FilesystemWorkspace(repo_path)
    stage = workspace.begin_transaction()
    diagnostics = render_bundled_packs(
        stage_dir=stage,
        repo_path=repo_path,
        languages=languages,
        services=services,
        features=features,
        allow_hooks=False,
    )
    if any(d.severity == Severity.ERROR for d in diagnostics):
        shutil.rmtree(stage, ignore_errors=True)
        return Result(diagnostics=diagnostics)

    content = _minimal_toml(lock)
    (stage / ".pantsagon.toml").write_text(content)

    augmented = augmented_coding or "none"
    if augmented == "agents":
        (stage / "AGENTS.md").write_text("# AGENTS\n")
    elif augmented == "claude":
        (stage / "CLAUDE.md").write_text("# CLAUDE\n")
    elif augmented == "gemini":
        (stage / "GEMINI.md").write_text("# GEMINI\n")

    workspace.commit(stage)
    return Result(diagnostics=diagnostics)
