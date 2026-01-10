import typer
from pathlib import Path

from pantsagon.application.init_repo import init_repo

app = typer.Typer(add_completion=False)


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
):
    features = feature or []
    svc_list = [s for s in services.split(",") if s]
    init_repo(repo, [lang], svc_list, features, renderer="copier")
    raise typer.Exit(0)
