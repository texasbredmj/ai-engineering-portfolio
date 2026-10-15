import argparse
import json
from pathlib import Path

from .backend import serve
from .contracts import Request
from .experiment import run_suite
from .worker import execute


def main():
    parser = argparse.ArgumentParser(prog="recovery-lab")
    commands = parser.add_subparsers(dest="command", required=True)
    backend = commands.add_parser("backend")
    backend.add_argument("--db", type=Path, required=True)
    backend.add_argument("--host", choices=["127.0.0.1", "0.0.0.0"], default="127.0.0.1")
    backend.add_argument("--port", type=int, default=18660)
    worker = commands.add_parser("worker")
    worker.add_argument("--task-id", required=True)
    worker.add_argument("--quantity", type=int, required=True)
    worker.add_argument("--db", type=Path, required=True)
    worker.add_argument("--url", default="http://127.0.0.1:18661")
    worker.add_argument("--report", type=Path, required=True)
    worker.add_argument("--request-timeout", type=float, default=1.0)
    run = commands.add_parser("run")
    run.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "backend":
        serve(args.db, args.host, args.port)
        return 0
    if args.command == "worker":
        report = execute(
            Request(task_id=args.task_id, quantity=args.quantity),
            args.db,
            args.url,
            timeout=args.request_timeout,
        )
        args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps({"state": report["state"], "verified": report["verified"]}))
        return 0 if report["verified"] else 1
    report = run_suite(args.output)
    print(json.dumps({"verified_demo": report["verified_demo"], "metrics": report["metrics"]}))
    return 0 if report["verified_demo"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
