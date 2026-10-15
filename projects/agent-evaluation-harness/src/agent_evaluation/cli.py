"""CLI exit codes: 0 passed, 1 gate failed, 2 invalid input."""

import argparse
import json
from pathlib import Path

from pydantic import ValidationError

from .candidates import CANDIDATES
from .runner import compare, run
from .schemas import Pricing


def main():
    parser = argparse.ArgumentParser(prog="agent-eval")
    commands = parser.add_subparsers(dest="command", required=True)
    evaluate = commands.add_parser("run")
    evaluate.add_argument("--suite", type=Path, required=True)
    evaluate.add_argument("--output", type=Path, required=True)
    evaluate.add_argument("--candidate", choices=CANDIDATES, default="baseline")
    evaluate.add_argument("--version", required=True)
    evaluate.add_argument("--predictions", type=Path)
    evaluate.add_argument("--input-price", type=float, default=0)
    evaluate.add_argument("--output-price", type=float, default=0)
    comparison = commands.add_parser("compare")
    comparison.add_argument("baseline", type=Path)
    comparison.add_argument("candidate", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "run":
            report = run(
                args.suite,
                args.output,
                args.candidate,
                args.version,
                args.predictions,
                Pricing(
                    input_usd_per_million=args.input_price, output_usd_per_million=args.output_price
                ),
            )
            result = {
                "passed": report["gate_passed"],
                "case_count": report["case_count"],
                "metrics": report["metrics"],
                "report": str(args.output / "report.json"),
            }
        else:
            result = compare(
                json.loads(args.baseline.read_text(encoding="utf-8")),
                json.loads(args.candidate.read_text(encoding="utf-8")),
            )
        print(json.dumps(result))
        return 0 if result["passed"] else 1
    except (ValueError, OSError, KeyError, TypeError, ValidationError) as exc:
        print(json.dumps({"error": str(exc)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
