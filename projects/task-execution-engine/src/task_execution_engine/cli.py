import json
from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError

from .engine import Engine
from .models import Request
from .runner import TOOLS
from .store import Store

app = typer.Typer(help="Run authorized repository tasks and verify their outcomes.")


@app.command()
def submit(
    request_file: Path,
    data_dir: Annotated[Path, typer.Option()] = Path(".task-engine"),
    report_file: Annotated[Path | None, typer.Option()] = None,
):
    """Submit a JSON request. Exit 0 only when completion is verified."""
    try:
        request = Request.model_validate_json(request_file.read_text(encoding="utf-8"))
        report = Engine(Store(data_dir)).submit(request)
        serialized = json.dumps(report, indent=2)
        if report_file:
            report_file.parent.mkdir(parents=True, exist_ok=True)
            report_file.write_text(serialized + "\n", encoding="utf-8")
        typer.echo(serialized)
    except (OSError, ValueError, ValidationError) as exc:
        typer.echo(json.dumps({"error": str(exc), "classification": type(exc).__name__}))
        raise typer.Exit(2) from exc
    raise typer.Exit(0 if report["verified_completion"] else 1)


@app.command()
def show(task_id: str, data_dir: Annotated[Path, typer.Option()] = Path(".task-engine")):
    """Read a durable task report, including its ordered audit trail."""
    try:
        typer.echo(json.dumps(Store(data_dir).get(task_id), indent=2))
    except KeyError as exc:
        typer.echo(json.dumps({"error": "unknown task", "task_id": task_id}))
        raise typer.Exit(2) from exc


@app.command()
def history(data_dir: Annotated[Path, typer.Option()] = Path(".task-engine")):
    """List persisted tasks."""
    typer.echo(json.dumps(Store(data_dir).history(), indent=2))


@app.command()
def tools():
    """Describe the fixed allowlisted tools and their permissions."""
    typer.echo(json.dumps(TOOLS, indent=2))
