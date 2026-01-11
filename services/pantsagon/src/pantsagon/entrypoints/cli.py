from pathlib import Path
import os

import typer

from pantsagon.adapters.pack_catalog.bundled import BundledPackCatalog
from pantsagon.adapters.policy.pack_validator import PackPolicyEngine
from pantsagon.adapters.renderer.copier_renderer import CopierRenderer
from pantsagon.adapters.workspace.filesystem import FilesystemWorkspace
from pantsagon.application.add_service import add_service as add_service_use_case
from pantsagon.application.init_repo import init_repo
from pantsagon.application.result_serialization import serialize_result
from pantsagon.application.validate_repo import validate_repo

app = typer.Typer(add_completion=False)


def _packs_root() -> Path:
    buildroot = os.environ.get("PANTS_BUILDROOT")
    if buildroot:
        packs_dir = Path(buildroot) / "packs"
        if packs_dir.is_dir():
            return packs_dir
    cwd = Path.cwd().resolve()
    for parent in (cwd, *cwd.parents):
        packs_dir = parent / "packs"
        if packs_dir.is_dir():
            return packs_dir
    for parent in Path(__file__).resolve().parents:
        packs_dir = parent / "packs"
        if packs_dir.is_dir():
            return packs_dir
        for child in parent.iterdir():
            if child.is_dir() and (child / "pack.yaml").is_file():
                return parent
    raise RuntimeError("Could not locate bundled packs directory")


@app.command(hidden=True)
def _noop() -> None:  # pyright: ignore[reportUnusedFunction]
    """Placeholder to keep Typer in group mode when only one command exists."""
    return None


@app.command()
def init(
    repo: Path = typer.Argument(...),
    lang: str = typer.Option(...),
    services: str = "",
    feature: list[str] = typer.Option(None),
    augmented_coding: str = typer.Option("none", "--augmented-coding"),
    strict: bool | None = typer.Option(None, "--strict"),
):
    features = feature or []
    svc_list = [s for s in services.split(",") if s]
    packs_root = _packs_root()
    catalog = BundledPackCatalog(packs_root)
    renderer_port = CopierRenderer()
    policy_engine = PackPolicyEngine()
    workspace = FilesystemWorkspace(repo)
    result = init_repo(
        repo,
        [lang],
        svc_list,
        features,
        renderer="copier",
        renderer_port=renderer_port,
        pack_catalog=catalog,
        policy_engine=policy_engine,
        workspace=workspace,
        augmented_coding=augmented_coding,
        strict=strict,
    )
    raise typer.Exit(result.exit_code)


@app.command()
def validate(json: bool = False, strict: bool | None = typer.Option(None, "--strict")):
    policy_engine = PackPolicyEngine()
    result = validate_repo(Path("."), strict=strict, policy_engine=policy_engine)
    if json:
        data = serialize_result(result, command="validate", args=[])
        import json as _json

        typer.echo(_json.dumps(data))
    raise typer.Exit(result.exit_code)


@app.command()
def add_service(
    name: str,
    lang: str = typer.Option("python"),
    strict: bool | None = typer.Option(None, "--strict"),
):
    result = add_service_use_case(Path("."), name=name, lang=lang, strict=strict)
    raise typer.Exit(result.exit_code)
