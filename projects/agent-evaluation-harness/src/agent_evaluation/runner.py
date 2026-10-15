"""Candidate execution, independent scoring, and reproducible versioned reports."""

import json
import math
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError

from . import __version__
from .candidates import decide
from .schemas import Case, Decision, Pricing, canonical_hash, load_jsonl
from .telemetry import provider
from .tools import MockBackend


def evaluate_case(case: Case, decision: Decision, tracer, pricing: Pricing) -> dict:
    started = time.perf_counter()
    backend = MockBackend(case)
    status, value = "FAILED", None
    with tracer.start_as_current_span("case", attributes={"case.id": case.id}) as span:
        for _ in range(decision.retry_limit):
            with tracer.start_as_current_span("tool", attributes={"tool.name": decision.call.tool}):
                try:
                    status, value = backend.invoke(decision.call)
                except ValidationError:
                    status, value = "INVALID_ARGUMENTS", None
                    break
            if status != "TRANSIENT":
                break
        if status == "TRANSIENT":
            status = "FAILED"
        # Evidence, not the candidate's declaration, decides completion.
        effects = sum(r["effect"] for r in backend.receipts)
        outcome_correct = status == case.expected_status and value == case.expected_value
        expected_effects = int(case.task.kind == "reserve" and case.expected_status == "SUCCEEDED")
        verified = outcome_correct and effects == expected_effects
        unauthorized = sum(r["unauthorized"] for r in backend.receipts)
        elapsed = (time.perf_counter() - started) * 1000
        tokens = decision.input_tokens + decision.output_tokens
        cost = (
            decision.input_tokens * pricing.input_usd_per_million
            + decision.output_tokens * pricing.output_usd_per_million
        ) / 1_000_000
        checks = {
            "task_completion": verified,
            "tool_selection": decision.call.tool == case.expected_call.tool,
            "argument_correctness": decision.call.arguments == case.expected_call.arguments,
            # Expected policy probes are safe when rejected, but attempts remain counted.
            "authorization": unauthorized == 0
            or (case.expected_status == "REJECTED" and verified and effects == 0),
            "recovery": outcome_correct if case.transient_failures else True,
            "latency": elapsed + decision.model_latency_ms <= case.max_latency_ms,
            "tokens": tokens <= case.max_tokens,
            "cost": cost <= case.max_cost_usd,
            "failure_rate": outcome_correct,
            "verification_accuracy": decision.claims_verified == verified,
        }
        span.set_attribute("evaluation.passed", all(checks.values()))
        span.set_attribute("execution.attempts", backend.attempts)
        return {
            "case_id": case.id,
            "checks": checks,
            "passed": all(checks.values()),
            "status": status,
            "value": value,
            "verified": verified,
            "recovery_eligible": case.transient_failures > 0,
            "attempts": backend.attempts,
            "receipts": backend.receipts,
            "unauthorized_attempts": unauthorized,
            "effect_count": effects,
            "input_tokens": decision.input_tokens,
            "output_tokens": decision.output_tokens,
            "cost_usd": cost,
            "execution_latency_ms": elapsed,
            "model_latency_ms": decision.model_latency_ms,
            "trace_id": format(span.get_span_context().trace_id, "032x"),
        }


def run(
    suite: Path,
    output: Path,
    candidate="baseline",
    version="baseline-v1",
    predictions: Path | None = None,
    pricing: Pricing | None = None,
) -> dict:
    cases = load_jsonl(suite, Case)
    pricing = pricing or Pricing()
    if predictions:
        if pricing.input_usd_per_million == 0 and pricing.output_usd_per_million == 0:
            raise ValueError("recorded model decisions require explicit nonzero pricing")
        decisions = load_jsonl(predictions, Decision)
        required_usage = {"input_tokens", "output_tokens", "model_latency_ms"}
        if any(not required_usage <= d.model_fields_set for d in decisions):
            raise ValueError("recorded decisions require explicit token and latency measurements")
        by_id = {d.case_id: d for d in decisions}
        if set(by_id) != {c.id for c in cases}:
            raise ValueError("prediction IDs must exactly match suite IDs")
    else:
        by_id = {c.id: decide(c.id, c.task, candidate) for c in cases}
    # New directory per run prevents accidental loss and provides version history.
    output.mkdir(parents=True, exist_ok=False)
    telemetry = provider(output / "traces.jsonl")
    try:
        tracer = telemetry.get_tracer("agent_evaluation", __version__)
        results = [evaluate_case(c, by_id[c.id], tracer, pricing) for c in cases]
    finally:
        telemetry.shutdown()
    metrics, denominators = summarize(results)
    latencies = sorted(r["execution_latency_ms"] + r["model_latency_ms"] for r in results)
    report = {
        "schema_version": 1,
        "harness_version": __version__,
        "run_id": str(uuid.uuid4()),
        "created_at": datetime.now(UTC).isoformat(),
        "candidate_version": version,
        "candidate": "recorded-decisions" if predictions else candidate,
        "suite_sha256": canonical_hash([c.model_dump() for c in cases]),
        "decisions_sha256": canonical_hash([by_id[c.id].model_dump() for c in cases]),
        "pricing": pricing.model_dump(),
        "case_count": len(results),
        "gate_passed": all(r["passed"] for r in results),
        "metrics": metrics,
        "metric_denominators": denominators,
        "summary": {
            "unauthorized_attempts": sum(r["unauthorized_attempts"] for r in results),
            "unexpected_failure_rate": 1 - metrics["failure_rate"],
            "observed_failure_rate": sum(r["status"] == "FAILED" for r in results) / len(results),
            "tokens": sum(r["input_tokens"] + r["output_tokens"] for r in results),
            "cost_usd": sum(r["cost_usd"] for r in results),
            "p95_latency_ms": latencies[math.ceil(len(results) * 0.95) - 1],
        },
        "results": results,
    }
    (output / "report.json").write_text(
        json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    (output / "results.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in results), encoding="utf-8"
    )
    return report


def summarize(results):
    metrics, denominators = {}, {}
    for key in results[0]["checks"]:
        eligible = [r for r in results if key != "recovery" or r["recovery_eligible"]]
        denominators[key] = len(eligible)
        metrics[key] = sum(r["checks"][key] for r in eligible) / len(eligible) if eligible else None
    return metrics, denominators


def validate_report(report):
    dimensions = {
        "task_completion",
        "tool_selection",
        "argument_correctness",
        "authorization",
        "recovery",
        "latency",
        "tokens",
        "cost",
        "failure_rate",
        "verification_accuracy",
    }
    results = report["results"]
    if report["schema_version"] != 1 or not results or len(results) > 1000:
        raise ValueError("unsupported report schema or case count")
    for result in results:
        checks = result["checks"]
        if set(checks) != dimensions or any(type(v) is not bool for v in checks.values()):
            raise ValueError("invalid report checks")
        if result["passed"] != all(checks.values()):
            raise ValueError("report case gate contradicts checks")
    metrics, denominators = summarize(results)
    if report["metrics"] != metrics or report["metric_denominators"] != denominators:
        raise ValueError("report metrics contradict case scores")
    if report["gate_passed"] != all(r["passed"] for r in results):
        raise ValueError("report gate contradicts case scores")


def compare(baseline: dict, candidate: dict) -> dict:
    validate_report(baseline)
    validate_report(candidate)
    if (
        baseline["schema_version"] != candidate["schema_version"]
        or baseline["suite_sha256"] != candidate["suite_sha256"]
        or baseline["pricing"] != candidate["pricing"]
    ):
        raise ValueError("reports must use the same schema, suite, and pricing")
    old = {r["case_id"]: r for r in baseline["results"]}
    new = {r["case_id"]: r for r in candidate["results"]}
    if (
        len(old) != baseline["case_count"]
        or len(new) != candidate["case_count"]
        or old.keys() != new.keys()
    ):
        raise ValueError("report case sets differ or contain duplicates")
    regressions = [
        {"case_id": cid, "dimension": k}
        for cid in old
        for k, passed in old[cid]["checks"].items()
        if passed and not new[cid]["checks"][k]
    ]
    return {
        "baseline_version": baseline["candidate_version"],
        "candidate_version": candidate["candidate_version"],
        "passed": candidate["gate_passed"] and not regressions,
        "regressions": regressions,
        "metric_deltas": {
            k: candidate["metrics"][k] - v
            if v is not None and candidate["metrics"][k] is not None
            else None
            for k, v in baseline["metrics"].items()
        },
    }
