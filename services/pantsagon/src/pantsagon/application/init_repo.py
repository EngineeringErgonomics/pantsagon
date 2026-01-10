from pathlib import Path
import shutil
from typing import Any

from pantsagon.application.rendering import render_bundled_packs
from pantsagon.domain.diagnostics import Diagnostic, Severity
from pantsagon.domain.result import Result
from pantsagon.ports.pack_catalog import PackCatalogPort
from pantsagon.ports.policy_engine import PolicyEnginePort
from pantsagon.ports.renderer import RendererPort
from pantsagon.ports.workspace import WorkspacePort


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
    *,
    renderer_port: RendererPort | None = None,
    pack_catalog: PackCatalogPort | None = None,
    policy_engine: PolicyEnginePort | None = None,
    workspace: WorkspacePort | None = None,
    allow_hooks: bool = False,
    augmented_coding: str | None = None,
) -> Result[None]:
    lock: dict[str, Any] = {
        "tool": {"name": "pantsagon", "version": "0.1.0"},
        "settings": {
            "renderer": renderer,
            "strict": False,
            "strict_manifest": True,
            "allow_hooks": allow_hooks,
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
    augmented = augmented_coding or "none"

    diagnostics: list[Diagnostic] = []
    if any([renderer_port, pack_catalog, policy_engine, workspace]):
        if not all([renderer_port, pack_catalog, policy_engine, workspace]):
            diagnostics.append(
                Diagnostic(
                    code="INIT_PORTS_MISSING",
                    rule="init.ports",
                    severity=Severity.ERROR,
                    message="Init requires renderer, pack catalog, policy engine, and workspace ports.",
                )
            )
            return Result(diagnostics=diagnostics)

        stage = workspace.begin_transaction()
        try:
            diagnostics = render_bundled_packs(
                stage_dir=stage,
                repo_path=repo_path,
                languages=languages,
                services=services,
                features=features,
                catalog=pack_catalog,
                renderer=renderer_port,
                policy_engine=policy_engine,
                allow_hooks=allow_hooks,
            )
            if any(d.severity == Severity.ERROR for d in diagnostics):
                return Result(diagnostics=diagnostics)

            _write_baseline_files(stage, content, augmented)
            workspace.commit(stage)
            return Result(diagnostics=diagnostics)
        finally:
            if stage.exists():
                shutil.rmtree(stage, ignore_errors=True)

    _write_baseline_files(repo_path, content, augmented)
    return Result()


def _write_baseline_files(repo_path: Path, content: str, augmented: str) -> None:
    (repo_path / ".pantsagon.toml").write_text(content)
    (repo_path / "pants.toml").write_text('[GLOBAL]\npants_version = "2.30.0"\n')
    if augmented == "agents":
        (repo_path / "AGENTS.md").write_text("# AGENTS\n")
    elif augmented == "claude":
        (repo_path / "CLAUDE.md").write_text("# CLAUDE\n")
    elif augmented == "gemini":
        (repo_path / "GEMINI.md").write_text("# GEMINI\n")
