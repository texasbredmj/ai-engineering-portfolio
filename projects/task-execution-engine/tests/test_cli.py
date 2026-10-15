import json
from pathlib import Path

from typer.testing import CliRunner

from task_execution_engine.cli import app

runner = CliRunner()


def test_cli_help_and_registry():
    assert runner.invoke(app, ["--help"]).exit_code == 0
    response = runner.invoke(app, ["tools"])
    assert response.exit_code == 0
    assert set(json.loads(response.stdout)) == {
        "inspect",
        "format_fix",
        "format_check",
        "lint",
        "test",
    }


def test_cli_invalid_task(tmp_path):
    request = tmp_path / "bad.json"
    request.write_text('{"command":"rm"}')
    response = runner.invoke(app, ["submit", str(request), "--data-dir", str(tmp_path / "data")])
    assert response.exit_code == 2
    assert json.loads(response.stdout)["classification"] == "ValidationError"


def test_cli_demo_and_persisted_report(tmp_path):
    root = Path(__file__).resolve().parents[1]
    request = tmp_path / "request.json"
    request.write_text(
        json.dumps(
            {
                "repository": str(root / "examples" / "demo-repository"),
                "operations": ["inspect", "test"],
                "authorized_operations": ["inspect", "test"],
                "idempotency_key": "cli-demo",
            }
        )
    )
    data = tmp_path / "data"
    output = tmp_path / "report.json"
    response = runner.invoke(
        app, ["submit", str(request), "--data-dir", str(data), "--report-file", str(output)]
    )
    assert response.exit_code == 0, response.stdout
    report = json.loads(output.read_text())
    assert report["verified_completion"]
    shown = runner.invoke(app, ["show", report["task_id"], "--data-dir", str(data)])
    assert shown.exit_code == 0
    assert json.loads(shown.stdout)["report"] == report
    history = runner.invoke(app, ["history", "--data-dir", str(data)])
    assert json.loads(history.stdout)[0]["id"] == report["task_id"]


def test_cli_unknown_task(tmp_path):
    response = runner.invoke(app, ["show", "unknown", "--data-dir", str(tmp_path)])
    assert response.exit_code == 2
