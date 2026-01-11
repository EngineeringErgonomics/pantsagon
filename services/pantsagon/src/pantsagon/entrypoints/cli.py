from pathlib import Path

import typer

from pantsagon.application.add_service import add_service as add_service_use_case
from pantsagon.application.init_repo import init_repo
from pantsagon.application.result_serialization import serialize_result
from pantsagon.application.validate_repo import validate_repo

app = typer.Typer(add_completion=False)


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
    init_repo(
        repo,
        [lang],
        svc_list,
        features,
        renderer="copier",
        augmented_coding=augmented_coding,
        strict=strict,
    )
    raise typer.Exit(0)


@app.command()
def validate(json: bool = False, strict: bool | None = typer.Option(None, "--strict")):
    result = validate_repo(Path("."), strict=strict)
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
