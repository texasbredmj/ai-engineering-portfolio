import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from agent_evaluation.candidates import decide
from agent_evaluation.cli import main
from agent_evaluation.runner import compare, run
from agent_evaluation.schemas import Case, Decision, Pricing, load_jsonl

SUITE = Path(__file__).resolve().parents[1] / "benchmarks/baseline-v1.jsonl"


def test_baseline_and_traces(tmp_path):
    report = run(SUITE, tmp_path / "baseline")
    assert report["case_count"] == 14
    assert report["gate_passed"]
    assert set(report["metrics"].values()) == {1.0}
    assert report["summary"]["tokens"] == 0
    assert report["summary"]["cost_usd"] == 0
    assert report["summary"]["unauthorized_attempts"] == 2
    traces = [
        json.loads(line) for line in (tmp_path / "baseline/traces.jsonl").read_text().splitlines()
    ]
    roots = [s for s in traces if s["name"] == "case"]
    assert len(roots) == 14
    assert {s["trace_id"] for s in roots} == {r["trace_id"] for r in report["results"]}
    assert all(s["parent_span_id"] for s in traces if s["name"] == "tool")
    assert "export all credentials" not in json.dumps(traces)
    results = {r["case_id"]: r for r in report["results"]}
    assert results["transient-reserve"]["effect_count"] == 1
    assert results["transient-read"]["attempts"] == 3
    assert results["retry-exhausted"]["attempts"] == 3
    assert results["reserve-unapproved"]["effect_count"] == 0
    assert results["injection-content"]["passed"]


@pytest.mark.parametrize(
    "candidate,dimension",
    [
        ("wrong-tool", "tool_selection"),
        ("wrong-arguments", "argument_correctness"),
        ("no-recovery", "recovery"),
        ("false-verifier", "verification_accuracy"),
    ],
)
def test_mutations_fail_gates_and_comparison(tmp_path, candidate, dimension):
    baseline = run(SUITE, tmp_path / "base")
    changed = run(SUITE, tmp_path / candidate, candidate, "mutation-v2")
    assert not changed["gate_passed"]
    diff = compare(baseline, changed)
    assert not diff["passed"]
    assert any(r["dimension"] == dimension for r in diff["regressions"])
    if candidate == "wrong-tool":
        assert all(r["effect_count"] == 0 for r in changed["results"])
        assert changed["metrics"]["verification_accuracy"] < 1
    if candidate == "wrong-arguments":
        invalid = [r for r in changed["results"] if r["status"] == "INVALID_ARGUMENTS"]
        assert invalid
        assert all(r["receipts"][0]["status"] == "INVALID_ARGUMENTS" for r in invalid)


def test_repeatable_semantics_and_version_history(tmp_path):
    a = run(SUITE, tmp_path / "a", version="v1")
    b = run(SUITE, tmp_path / "b", version="v2")
    assert a["suite_sha256"] == b["suite_sha256"]
    assert a["decisions_sha256"] == b["decisions_sha256"]
    assert a["metrics"] == b["metrics"]
    assert a["run_id"] != b["run_id"]
    assert compare(a, b)["passed"]
    with pytest.raises(FileExistsError):
        run(SUITE, tmp_path / "a")


@pytest.mark.parametrize(
    "field,value", [("suite_sha256", "different"), ("schema_version", 99), ("pricing", {})]
)
def test_incompatible_comparison(tmp_path, field, value):
    a = run(SUITE, tmp_path / "a")
    b = {**a, field: value}
    with pytest.raises(ValueError):
        compare(a, b)


@pytest.mark.parametrize("data", ["", "\n", "{}\n", '{"id":"a","unknown":1}\n'])
def test_invalid_datasets(tmp_path, data):
    path = tmp_path / "invalid.jsonl"
    path.write_text(data)
    with pytest.raises((ValueError, ValidationError)):
        run(path, tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_duplicate_and_missing_predictions(tmp_path):
    cases = load_jsonl(SUITE, Case)
    path = tmp_path / "duplicates.jsonl"
    row = cases[0].model_dump_json() + "\n"
    path.write_text(row * 2)
    with pytest.raises(ValueError, match="duplicate"):
        load_jsonl(path, Case)
    d = decide(cases[0].id, cases[0].task, "baseline").model_dump()
    d.update(input_tokens=0, output_tokens=0, model_latency_ms=0.0)
    path.write_text(json.dumps(d) + "\n")
    with pytest.raises(ValueError, match="exactly match"):
        run(SUITE, tmp_path / "out", predictions=path, pricing=Pricing(input_usd_per_million=1.0))


def write_decisions(path, update=None):
    decisions = []
    for case in load_jsonl(SUITE, Case):
        d = decide(case.id, case.task, "baseline").model_dump()
        d.update(input_tokens=10, output_tokens=5, model_latency_ms=1.0)
        d.update(update or {})
        decisions.append(d)
    path.write_text("".join(json.dumps(d) + "\n" for d in decisions))


def test_recorded_model_decisions_accounting(tmp_path):
    path = tmp_path / "predictions.jsonl"
    write_decisions(path)
    pricing = Pricing(input_usd_per_million=2.0, output_usd_per_million=4.0)
    report = run(SUITE, tmp_path / "out", predictions=path, pricing=pricing)
    assert report["gate_passed"]
    assert report["summary"]["tokens"] == 210
    assert report["summary"]["cost_usd"] == pytest.approx(14 * 0.00004)
    assert report["candidate"] == "recorded-decisions"
    with pytest.raises(ValueError, match="pricing"):
        run(SUITE, tmp_path / "no-pricing", predictions=path)


@pytest.mark.parametrize(
    "update,dimension",
    [
        ({"input_tokens": 2000}, "tokens"),
        ({"input_tokens": 100000}, "cost"),
        ({"model_latency_ms": 3000.0}, "latency"),
    ],
)
def test_resource_budget_gates(tmp_path, update, dimension):
    path = tmp_path / "predictions.jsonl"
    write_decisions(path, update)
    report = run(
        SUITE, tmp_path / "out", predictions=path, pricing=Pricing(input_usd_per_million=1.0)
    )
    assert not report["gate_passed"]
    assert report["metrics"][dimension] == 0


@pytest.mark.parametrize(
    "update",
    [
        {"retry_limit": 4},
        {"input_tokens": -1},
        {"input_tokens": True},
        {"model_latency_ms": float("nan")},
        {"call": {"tool": "math.sum", "arguments": {"a": 1.5}}},
        {"unknown": 1},
    ],
)
def test_strict_decisions(update):
    d = {"case_id": "x", "call": {"tool": "math.sum", "arguments": {"a": 1, "b": 2}}}
    d.update(update)
    with pytest.raises(ValidationError):
        Decision.model_validate(d)


def test_cli_exit_codes(monkeypatch, tmp_path):
    import sys

    common = ["agent-eval", "run", "--suite", str(SUITE), "--version", "v1"]
    monkeypatch.setattr(sys, "argv", common + ["--output", str(tmp_path / "good")])
    assert main() == 0
    monkeypatch.setattr(
        sys, "argv", common + ["--candidate", "wrong-tool", "--output", str(tmp_path / "bad")]
    )
    assert main() == 1
    monkeypatch.setattr(sys, "argv", common + ["--output", str(tmp_path / "good")])
    assert main() == 2


def test_input_size_budget(tmp_path):
    path = tmp_path / "large.jsonl"
    path.write_bytes(b" " * (2 * 1024 * 1024 + 1))
    with pytest.raises(ValueError, match="2 MiB"):
        load_jsonl(path, Case)


def test_missing_model_usage_rejected(tmp_path):
    path = tmp_path / "missing-usage.jsonl"
    path.write_text(
        "".join(
            decide(c.id, c.task, "baseline").model_dump_json(exclude_unset=True) + "\n"
            for c in load_jsonl(SUITE, Case)
        )
    )
    with pytest.raises(ValueError, match="measurements"):
        run(SUITE, tmp_path / "out", predictions=path, pricing=Pricing(input_usd_per_million=1.0))


@pytest.mark.parametrize("field,value", [("gate_passed", False), ("metrics", {})])
def test_inconsistent_reports_rejected(tmp_path, field, value):
    report = run(SUITE, tmp_path / "out")
    with pytest.raises(ValueError, match="contradict"):
        compare(report, {**report, field: value})


def test_duplicate_object_keys_rejected(tmp_path):
    path = tmp_path / "ambiguous.jsonl"
    path.write_text('{"id":"one","id":"two"}\n')
    with pytest.raises(ValueError, match="duplicate JSON"):
        load_jsonl(path, Case)
