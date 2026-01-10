import typer
from pathlib import Path

from pantsagon.adapters.pack_catalog.bundled import BundledPackCatalog
from pantsagon.adapters.policy.pack_validator import PackPolicyEngine
from pantsagon.adapters.renderer.copier_renderer import CopierRenderer
from pantsagon.adapters.workspace.filesystem import FilesystemWorkspace
from pantsagon.application.init_repo import init_repo

app = typer.Typer(add_completion=False)


def _repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "packs").is_dir():
            return parent
    raise RuntimeError("Could not locate repo root containing packs/")


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
):
    features = feature or []
    svc_list = [s for s in services.split(",") if s]
    repo_root = _repo_root()
    catalog = BundledPackCatalog(repo_root / "packs")
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
    )
    raise typer.Exit(result.exit_code)


@app.command()
def validate(json: bool = False):
    from pantsagon.application.validate_repo import validate_repo
    from pantsagon.application.result_serialization import serialize_result

    result = validate_repo(Path("."))
    if json:
        data = serialize_result(result, command="validate", args=[])
        import json as _json

        typer.echo(_json.dumps(data))
    raise typer.Exit(result.exit_code)


@app.command()
def add_service(name: str, lang: str = typer.Option("python")):
    from pantsagon.application.add_service import add_service as _add

    result = _add(Path("."), name=name, lang=lang)
    raise typer.Exit(result.exit_code)
