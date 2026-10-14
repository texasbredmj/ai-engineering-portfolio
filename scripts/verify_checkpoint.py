"""Validate the portfolio's claims without making external requests."""
import json
import re
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    evidence = json.loads((root / "evidence/phase1.json").read_text(encoding="utf-8"))
    expected = {"task-execution-engine": 50, "ai-tool-coordination-gateway": 30}
    assert {p["name"] for p in evidence["projects"]} == set(expected)
    for project in evidence["projects"]:
        assert project["local_tests_passed"] >= expected[project["name"]]
        assert project["local_tests_failed"] == 0
        assert re.fullmatch(r"[0-9a-f]{40}", project["published_sha"])
        assert project["repository_url"] == f"https://github.com/texasbredmj/{project['name']}"
        if evidence["checkpoint_complete"]:
            ci = project["remote_ci"]
            assert ci["head_sha"] == project["published_sha"]
            assert ci["status"] == "completed" and ci["conclusion"] == "success"
            assert len(ci["jobs"]) == 7
            assert all(job["conclusion"] == "success" for job in ci["jobs"])
            assert ci["url"].startswith(project["repository_url"] + "/actions/runs/")
            assert project["published"] is True
    assert evidence["project03_allowed"] == evidence["checkpoint_complete"]
    project03_path = root / "evidence/project03.json"
    if project03_path.exists():
        project = json.loads(project03_path.read_text(encoding="utf-8"))
        assert project["name"] == "autonomous-workflow-orchestrator"
        assert project["published"] and project["checkpoint_complete"]
        assert re.fullmatch(r"[0-9a-f]{40}", project["published_sha"])
        assert project["repository_url"] == "https://github.com/texasbredmj/autonomous-workflow-orchestrator"
        ci = project["remote_ci"]
        assert ci["head_sha"] == project["published_sha"]
        assert ci["status"] == "completed" and ci["conclusion"] == "success"
        assert len(ci["jobs"]) == 7 and all(j["conclusion"] == "success" for j in ci["jobs"])
        assert ci["url"].startswith(project["repository_url"] + "/actions/runs/")
        junit = ci["artifact_verification"]["junit"]
        assert junit["tests"] == 16
        assert all(junit[k] == 0 for k in ("failures", "errors", "skipped"))
        scenarios = ci["artifact_verification"]["durability"]["scenarios"]
        expected_scenarios = {
            "worker_crash_after_commit", "bounded_retry_and_branch_skip",
            "verification_failure_compensates", "cancel_after_reservation_compensates",
            "unauthorized_then_rejected_approval", "durable_scheduled_start",
            "retry_exhaustion_no_effect", "approval_timeout_no_effect",
        }
        assert {s["scenario"] for s in scenarios} == expected_scenarios
        assert len(scenarios) == 8 and all(s["passed"] for s in scenarios)
        crash = next(s for s in scenarios if s["scenario"] == "worker_crash_after_commit")
        assert crash["worker_replaced"] and crash["reservation_count"] == 1
        assert crash["activity_attempt"] >= 2
    project04_path = root / "evidence/project04.json"
    if project04_path.exists():
        project = json.loads(project04_path.read_text(encoding="utf-8"))
        assert project["name"] == "agent-evaluation-harness"
        assert project["published"] and project["checkpoint_complete"]
        assert re.fullmatch(r"[0-9a-f]{40}", project["published_sha"])
        assert project["repository_url"] == "https://github.com/texasbredmj/agent-evaluation-harness"
        ci = project["remote_ci"]
        assert ci["head_sha"] == project["published_sha"]
        assert ci["status"] == "completed" and ci["conclusion"] == "success"
        assert len(ci["jobs"]) == 7 and all(j["conclusion"] == "success" for j in ci["jobs"])
        assert ci["url"].startswith(project["repository_url"] + "/actions/runs/")
        samples = ci["artifact_verification"]
        assert len(samples) == 6
        for sample in samples:
            junit = sample["junit"]
            assert junit["tests"] == 30
            assert all(junit[k] == 0 for k in ("failures", "errors", "skipped"))
            benchmark = sample["benchmark"]
            assert benchmark["case_count"] == 14 and benchmark["baseline_gate_passed"]
            assert len(benchmark["metrics"]) == 10
            assert all(v == 1.0 for v in benchmark["metrics"].values())
            mutations = benchmark["regressions_rejected"]
            assert len(mutations) == 4
            assert all(not m["passed"] and m["regression_count"] > 0 for m in mutations)
    project05_path = root / "evidence/project05.json"
    if project05_path.exists():
        project = json.loads(project05_path.read_text(encoding="utf-8"))
        assert project["name"] == "agent-failure-recovery-lab"
        assert project["published"] and project["checkpoint_complete"]
        assert re.fullmatch(r"[0-9a-f]{40}", project["published_sha"])
        assert project["repository_url"] == "https://github.com/texasbredmj/agent-failure-recovery-lab"
        ci = project["remote_ci"]
        assert ci["head_sha"] == project["published_sha"]
        assert ci["status"] == "completed" and ci["conclusion"] == "success"
        assert len(ci["jobs"]) == 7 and all(j["conclusion"] == "success" for j in ci["jobs"])
        assert ci["url"].startswith(project["repository_url"] + "/actions/runs/")
        sample = ci["artifact_verification"]
        junit = sample["junit"]
        assert junit["tests"] == 25
        assert all(junit[k] == 0 for k in ("failures", "errors", "skipped"))
        fault_report = sample["fault_report"]
        assert fault_report["verified_demo"] and fault_report["scenario_count"] == 10
        results = fault_report["results"]
        expected_scenarios = {"api_timeout", "http_failures", "rate_limit", "malformed_response",
                              "temporary_outage", "worker_interruption", "delayed_response",
                              "duplicate_delivery", "dependency_failure", "permanent_outage"}
        assert len(results) == 10 and {r["scenario"] for r in results} == expected_scenarios
        assert all(r["passed"] and 1 <= r["attempts"] <= 3 for r in results)
        assert sum(r["outcome"] == "RECOVERED" for r in results) == 8
        assert sum(r["outcome"] == "FAILED_SAFELY" for r in results) == 1
        assert sum(r["outcome"] == "HUMAN_REQUIRED" for r in results) == 1
        for result in results:
            assert result["effect_count"] == (1 if result["outcome"] == "RECOVERED" else 0)
        crash = next(r for r in results if r["scenario"] == "worker_interruption")
        assert crash["worker_replaced"] and crash["attempts"] == 2
        duplicate = next(r for r in results if r["scenario"] == "duplicate_delivery")
        assert duplicate["backend_attempts"] == 2
        checkpoints = sample["checkpoints_verified"]
        assert len(checkpoints) == 10
        assert {c["scenario"] for c in checkpoints} == expected_scenarios
        assert all(c["matches_worker_report"] for c in checkpoints)
        assert sample["observability"]["prometheus_queried"]
        assert sample["observability"]["grafana_provisioned_dashboard"]
        assert sample["observability"]["dashboard_panels"] == 5
    project06_path = root / "evidence/project06.json"
    if project06_path.exists():
        project = json.loads(project06_path.read_text(encoding="utf-8"))
        assert project["name"] == "multi-provider-model-gateway"
        assert project["published"] and project["checkpoint_complete"]
        assert re.fullmatch(r"[0-9a-f]{40}", project["published_sha"])
        assert project["repository_url"] == "https://github.com/texasbredmj/multi-provider-model-gateway"
        ci = project["remote_ci"]
        assert ci["head_sha"] == project["published_sha"]
        assert ci["status"] == "completed" and ci["conclusion"] == "success"
        assert len(ci["jobs"]) == 7 and all(j["conclusion"] == "success" for j in ci["jobs"])
        assert ci["url"].startswith(project["repository_url"] + "/actions/runs/")
        sample = ci["artifact_verification"]
        junit = sample["junit"]
        assert junit["tests"] == 43
        assert all(junit[k] == 0 for k in ("failures", "errors", "skipped"))
        demo = sample["http_demo"]
        assert demo["verified_demo"] and demo["scenario_count"] == 9 and demo["paid_api_calls"] == 0
        expected = {"text", "structured", "tools", "fallback", "timeout", "unsupported",
                    "budget", "stream", "partial-stream"}
        assert len(demo["results"]) == 9 and {r["scenario"] for r in demo["results"]} == expected
        assert all(r["passed"] for r in demo["results"])
        by_name = {r["scenario"]: r for r in demo["results"]}
        text = by_name["text"]["response"]
        assert text["usage"] == {"input_tokens": 2, "output_tokens": 4}
        assert text["accounted_nusd"] == 10000
        fallback = by_name["fallback"]["response"]
        assert fallback["model"] == "beta-text" and len(fallback["attempts"]) == 2
        assert fallback["attempts"][0]["error"] == "rate_limited"
        timeout = by_name["timeout"]["response"]
        assert timeout["attempts"][0]["error"] == "timeout"
        assert timeout["attempts"][0]["accounting"] == "unknown_usage_reserved_maximum"
        for name, terminal in (("stream", "done"), ("partial-stream", "error")):
            events = by_name[name]["events"]
            assert events.count("event: delta") == 2 and "event: " + terminal in events
            values = [json.loads(line[6:]) for line in events.splitlines() if line.startswith("data: ")]
            final = values[-1]
            assert final["state"] == ("SUCCEEDED" if terminal == "done" else "UNVERIFIED")
            assert len(final["attempts"]) == 1
        assert all(sample["restart"][key] for key in (
            "gateway_restarted", "cached_response_preserved", "usage_unchanged_on_replay",
            "redis_persisted_identity"))
    project07_path = root / "evidence/project07.json"
    if project07_path.exists():
        project = json.loads(project07_path.read_text(encoding="utf-8"))
        assert project["name"] == "ai-native-cicd-gates"
        assert project["published"] and project["checkpoint_complete"]
        assert not project["private"]
        assert re.fullmatch(r"[0-9a-f]{40}", project["published_sha"])
        assert project["repository_url"] == "https://github.com/texasbredmj/ai-native-cicd-gates"
        ci = project["remote_ci"]
        assert ci["head_sha"] == project["published_sha"]
        assert ci["status"] == "completed" and ci["conclusion"] == "success"
        assert len(ci["jobs"]) == 7 and all(j["conclusion"] == "success" for j in ci["jobs"])
        assert ci["url"].startswith(project["repository_url"] + "/actions/runs/")
        sample = ci["artifact_verification"]
        assert re.fullmatch(r"[0-9a-f]{64}", sample["sha256"])
        assert sample["junit"] == {"tests": 31, "failures": 0, "errors": 0, "skipped": 0}
        expected_gates = {"unit_tests", "integration_tests", "schema_validation",
                          "dependency_security", "secret_scan", "gitleaks_scan", "container_build",
                          "evaluation_regression", "task_completion", "latency", "cost",
                          "policy_violations"}
        assert sample["baseline"]["state"] == "PASSED"
        assert set(sample["baseline"]["gates"]) == expected_gates
        assert all(state == "PASSED" for state in sample["baseline"]["gates"].values())
        assert sample["baseline"]["completed_cases"] == 3
        demo = sample["demo"]
        assert demo["verified_demo"] and demo["valid_candidate_passed"]
        assert demo["regressions_rejected"] == 11 and demo["live_model_calls"] == 0
        results = demo["results"]
        assert len(results) == 12
        assert {r["mutation"] for r in results} == {"none", "unit", "integration", "schema",
              "dependency", "secret", "container", "regression", "completion", "latency", "cost", "policy"}
        assert all(r["exit_code"] == (0 if r["mutation"] == "none" else 1) for r in results)
        assert sample["all_mutations_independently_verified"]
        assert sample["both_secret_scanners_rejected_synthetic_token"]
        assert sample["all_traces_linked"] and sample["gitleaks_evidence_redacted"]
        proof = project["remote_regression_proof"]
        assert proof["head_sha"] == project["published_sha"]
        assert proof["status"] == "completed" and proof["conclusion"] == "failure"
        assert proof["expected_failure_verified"] and proof["defect"] == "completion"
        assert proof["url"].startswith(project["repository_url"] + "/actions/runs/")
        assert proof["failed_step"] == "Required gate must fail here"
        rejected = proof["artifact_verification"]
        assert re.fullmatch(r"[0-9a-f]{64}", rejected["sha256"])
        assert rejected["state"] == "FAILED" and not rejected["gate_passed"]
        assert set(rejected["gates"]) == expected_gates
        assert {k for k, v in rejected["gates"].items() if v == "FAILED"} == {
            "task_completion", "evaluation_regression"}
        assert rejected["incorrect_value_rejected_despite_success_claim"]
    print(json.dumps({"evidence_valid": True, "checkpoint_complete": evidence["checkpoint_complete"]}))


if __name__ == "__main__":
    main()
