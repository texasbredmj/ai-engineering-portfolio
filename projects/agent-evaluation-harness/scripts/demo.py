"""Executable acceptance check: valid baseline passes and deliberate mutations fail."""

import json
import uuid
from pathlib import Path

from agent_evaluation.runner import compare, run


def main():
    root = Path(__file__).resolve().parents[1]
    output = root / ".evaluation" / f"demo-{uuid.uuid4()}"
    suite = root / "benchmarks/baseline-v1.jsonl"
    baseline = run(suite, output / "baseline", version="baseline-v1")
    assert baseline["gate_passed"]
    results = []
    for candidate in ("wrong-tool", "wrong-arguments", "no-recovery", "false-verifier"):
        changed = run(suite, output / candidate, candidate, f"{candidate}-v2")
        comparison = compare(baseline, changed)
        assert not changed["gate_passed"] and not comparison["passed"]
        results.append(comparison)
    (output / "comparison.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "verified_demo": True,
                "cases": baseline["case_count"],
                "mutation_candidates_rejected": len(results),
                "evidence": str(output),
            }
        )
    )


if __name__ == "__main__":
    main()
