"""Demonstrate checks, authorized correction, and independent final verification on a copy."""

import argparse
import json
import shutil
import uuid
from pathlib import Path

from task_execution_engine.engine import Engine
from task_execution_engine.models import Request
from task_execution_engine.store import Store


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path(".task-engine/demos"))
    args = parser.parse_args()
    directory = args.output_dir.resolve() / str(uuid.uuid4())
    fixture = Path(__file__).resolve().parents[1] / "examples/demo-repository"
    root = directory / "repository"
    shutil.copytree(fixture, root, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    (root / "tests/test_arithmetic.py").write_text(
        "def test_invoice_total( ):\n assert sum([125,250,75])==450\n\n"
        "def test_discount( ):\n assert 200*90//100==180\n",
        encoding="utf-8",
    )
    store = Store(directory / "data")
    operations = ["inspect", "format_fix", "format_check", "lint", "test"]
    engine = Engine(store)
    check = Request(
        repository=str(root),
        operations=["inspect", "format_check", "lint", "test"],
        authorized_operations=["inspect", "format_check", "lint", "test"],
        idempotency_key="baseline",
    )
    baseline = engine.submit(check)
    correction = Request(
        repository=str(root),
        operations=operations,
        authorized_operations=operations,
        idempotency_key="approved-correction",
    )
    final = engine.submit(correction)
    for name, report in (("baseline", baseline), ("maintenance", final)):
        (directory / f"{name}-report.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
    success = (
        baseline["state"] == "FAILED"
        and final["verified_completion"]
        and bool(final.get("corrections", {}).get("changed_files"))
        and engine.submit(correction) == final
    )
    print(
        json.dumps(
            {
                "demo_verified": success,
                "baseline_state": baseline["state"],
                "final_state": final["state"],
                "task_id": final["task_id"],
                "report": str(directory / "maintenance-report.json"),
                "patch": final.get("corrections", {}).get("patch"),
                "tool_calls": final["metrics"]["tool_calls"],
            },
            indent=2,
        )
    )
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
