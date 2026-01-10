from dataclasses import asdict
from pathlib import Path

import typer

from pantsagon.application.add_service import add_service as add_service_use_case
from pantsagon.application.init_repo import init_repo
from pantsagon.application.validate_repo import validate_repo

app = typer.Typer(add_completion=False)


def _serialize_result(result) -> dict:
    diagnostics = []
    for d in result.diagnostics:
        payload = {
            "id": d.id,
            "code": d.code,
            "rule": d.rule,
            "severity": d.severity.value,
            "message": d.message,
        }
        if d.location is not None:
            payload["location"] = asdict(d.location)
        if d.hint is not None:
            payload["hint"] = d.hint
        if d.details is not None:
            payload["details"] = d.details
        diagnostics.append(payload)
    return {
        "result_schema_version": 1,
        "exit_code": result.exit_code,
        "diagnostics": diagnostics,
        "artifacts": result.artifacts,
    }


@app.command(hidden=True)
def _noop() -> None:
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
        typer.echo(__import__("json").dumps(_serialize_result(result)))
    raise typer.Exit(result.exit_code)


@app.command()
def add_service(
    name: str,
    lang: str = typer.Option("python"),
    strict: bool | None = typer.Option(None, "--strict"),
):
    result = add_service_use_case(Path("."), name=name, lang=lang, strict=strict)
    raise typer.Exit(result.exit_code)
