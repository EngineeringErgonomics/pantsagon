from pathlib import Path

from pantsagon.domain.result import Result
from pantsagon.domain.determinism import is_deterministic
from pantsagon.application.rendering import render_bundled_packs
from pantsagon.adapters.workspace.filesystem import FilesystemWorkspace
from pantsagon.domain.diagnostics import Severity
from pantsagon.domain.naming import BUILTIN_RESERVED_SERVICES, validate_service_name
from pantsagon.domain.strictness import apply_strictness


def _minimal_toml(lock: dict) -> str:
    tool = lock.get("tool", {})
    return f"[tool]\nname='{tool.get('name', '')}'\nversion='{tool.get('version', '')}'\n"


def init_repo(
    repo_path: Path,
    languages: list[str],
    services: list[str],
    features: list[str],
    renderer: str,
    augmented_coding: str | None = None,
    strict: bool | None = None,
) -> Result[None]:
    diagnostics = []
    for service in services:
        diagnostics.extend(validate_service_name(service, BUILTIN_RESERVED_SERVICES, set()))
    if any(d.severity == Severity.ERROR for d in diagnostics):
        return Result(diagnostics=apply_strictness(diagnostics, bool(strict)))

    lock = {
        "tool": {"name": "pantsagon", "version": "0.1.0"},
        "settings": {"renderer": renderer, "strict": bool(strict), "strict_manifest": True, "allow_hooks": False},
        "selection": {
            "languages": languages,
            "features": features,
            "services": services,
            "augmented_coding": augmented_coding or "none",
        },
        "resolved": {"packs": [], "answers": {}},
    }
    try:
        import tomli_w
        content = tomli_w.dumps(lock)
    except ModuleNotFoundError:
        content = _minimal_toml(lock)
    workspace = FilesystemWorkspace(repo_path)
    stage = workspace.begin_transaction()
    render_bundled_packs(stage, repo_path, languages, services, features, allow_hooks=False)
    (stage / ".pantsagon.toml").write_text(content)
    workspace.commit(stage)

    augmented = augmented_coding or "none"
    if augmented == "agents":
        (repo_path / "AGENTS.md").write_text("# AGENTS\n")
    elif augmented == "claude":
        (repo_path / "CLAUDE.md").write_text("# CLAUDE\n")
    elif augmented == "gemini":
        (repo_path / "GEMINI.md").write_text("# GEMINI\n")
    return Result()
