"""Nine real subprocess/HTTP experiments plus permanent outage escalation."""

import json
import subprocess
import sys
import time
import uuid
from pathlib import Path

from .contracts import Request, call, local_url
from .store import Store

SCENARIOS = (
    "api_timeout",
    "http_failures",
    "rate_limit",
    "malformed_response",
    "temporary_outage",
    "worker_interruption",
    "delayed_response",
    "duplicate_delivery",
    "dependency_failure",
    "permanent_outage",
)


def wait_until(predicate, budget=15):
    until = time.monotonic() + budget
    while time.monotonic() < until:
        try:
            result = predicate()
            if result:
                return result
        except (OSError, ValueError):
            pass
        time.sleep(0.02)
    raise TimeoutError("bounded experiment condition not reached")


def has_error(db, task_id):
    if not db.exists():
        return False
    store = Store(db)
    try:
        return any(e["kind"] == "error" for e in store.history(task_id))
    finally:
        store.close()


def run_suite(
    output: Path,
    backend="http://127.0.0.1:18660",
    proxy="http://127.0.0.1:18661",
    toxiproxy="http://127.0.0.1:18474",
    upstream="backend:8080",
    listen="0.0.0.0:8666",
):
    for origin in (backend, proxy, toxiproxy):
        local_url(origin)
    # Only these fixed lab addresses may be configured as proxy destinations.
    if upstream not in {"backend:8080", "127.0.0.1:18660"} or listen not in {
        "0.0.0.0:8666",
        "127.0.0.1:18661",
    }:
        raise ValueError("unapproved proxy destination")
    output.mkdir(parents=True, exist_ok=False)
    wait_until(lambda: call(backend, "/health"))
    wait_until(lambda: call(toxiproxy, "/version"))
    existing = call(toxiproxy, "/proxies")
    if "lab" not in existing:
        call(toxiproxy, "/proxies", {"name": "lab", "listen": listen, "upstream": upstream})
    elif existing["lab"]["upstream"] != upstream or existing["lab"]["listen"] not in (
        {listen, "[::]:8666"} if listen == "0.0.0.0:8666" else {listen}
    ):
        raise ValueError("existing lab proxy configuration differs; refusing to change it")
    results = []
    for scenario in SCENARIOS:
        task = Request(task_id="lab-" + str(uuid.uuid4()), quantity=2)
        directory = output / scenario
        directory.mkdir()
        db = directory / "worker.sqlite"
        report_path = directory / "worker-report.json"
        command = [
            sys.executable,
            "-I",
            "-m",
            "recovery_lab.cli",
            "worker",
            "--task-id",
            task.task_id,
            "--quantity",
            "2",
            "--db",
            str(db),
            "--url",
            proxy,
            "--report",
            str(report_path),
        ]
        # Narrow deadlines belong only to deliberate timeout faults. Give normal service
        # operations and independent verification enough budget on shared CI runners.
        request_timeout = (
            0.15
            if scenario in {"api_timeout", "delayed_response"}
            else (10.0 if scenario == "worker_interruption" else 1.0)
        )
        command.extend(["--request-timeout", str(request_timeout)])
        mode = {
            "api_timeout": "delay",
            "http_failures": "http500",
            "rate_limit": "rate429",
            "malformed_response": "malformed",
            "worker_interruption": "hold",
            "dependency_failure": "dependency",
        }.get(scenario, "none")
        call(
            backend,
            "/configure",
            {"request": task.model_dump(), "fault": {"mode": mode, "failures": 2}},
        )
        # Reset only this lab's proxy, never global Toxiproxy reset or other proxies.
        call(toxiproxy, "/proxies/lab", {"enabled": True})
        if call(toxiproxy, "/proxies/lab")["toxics"]:
            raise ValueError("unexpected preexisting lab toxics; refusing to remove them")
        if scenario in {"temporary_outage", "permanent_outage"}:
            call(toxiproxy, "/proxies/lab", {"enabled": False})
        if scenario == "delayed_response":
            call(
                toxiproxy,
                "/proxies/lab/toxics",
                {
                    "name": "lab-latency",
                    "type": "latency",
                    "stream": "downstream",
                    "toxicity": 1.0,
                    "attributes": {"latency": 300, "jitter": 0},
                },
            )
        started = time.monotonic()
        replaced = False
        process = None
        log_handle = (directory / "worker.log").open("w", encoding="utf-8")
        try:
            process = subprocess.Popen(command, stdout=log_handle, stderr=subprocess.STDOUT)
            if scenario == "worker_interruption":
                wait_until(lambda task=task: call(backend, "/receipt/" + task.task_id)["receipt"])
                process.kill()
                process.wait(timeout=5)
                process = subprocess.Popen(command, stdout=log_handle, stderr=subprocess.STDOUT)
                replaced = True
            elif scenario == "temporary_outage":
                wait_until(lambda db=db, task=task: has_error(db, task.task_id))
                call(toxiproxy, "/proxies/lab", {"enabled": True})
            elif scenario == "delayed_response":
                wait_until(lambda db=db, task=task: has_error(db, task.task_id))
                # DELETE only the toxic created by this experiment.
                call(toxiproxy, "/proxies/lab/toxics/lab-latency", method="DELETE")
            process.wait(timeout=30)
            if process.returncode not in {0, 1}:
                raise RuntimeError(
                    f"worker failed unexpectedly; inspect {directory / 'worker.log'}"
                )
            report = json.loads(report_path.read_text(encoding="utf-8"))
            if scenario == "duplicate_delivery":
                # Actual duplicate HTTP delivery bypasses the completed worker cache.
                call(proxy, "/execute", task.model_dump())
                subprocess.run(
                    command, check=True, timeout=5, stdout=log_handle, stderr=subprocess.STDOUT
                )
            independent = call(backend, "/receipt/" + task.task_id)
            receipt = independent["receipt"]
            effect_count = receipt["effect_count"] if receipt else 0
            outcome = {
                "SUCCEEDED": "RECOVERED",
                "FAILED": "FAILED_SAFELY",
                "HUMAN_REQUIRED": "HUMAN_REQUIRED",
            }[report["state"]]
            expected = {
                "dependency_failure": "FAILED_SAFELY",
                "permanent_outage": "HUMAN_REQUIRED",
            }.get(scenario, "RECOVERED")
            passed = (
                outcome == expected
                and report["attempts"] <= 3
                and (
                    effect_count == 1
                    and receipt["quantity"] == task.quantity
                    and report["verified"]
                    if outcome == "RECOVERED"
                    else effect_count == 0 and not report["verified"]
                )
            )
            errors = [
                json.loads(e["detail"])["classification"]
                for e in report["history"]
                if e["kind"] == "error"
            ]
            if scenario not in {"duplicate_delivery"}:
                passed = passed and (
                    replaced if scenario == "worker_interruption" else bool(errors)
                )
            elapsed = time.monotonic() - started
            row = {
                "scenario": scenario,
                "task_id": task.task_id,
                "outcome": outcome,
                "passed": passed,
                "attempts": report["attempts"],
                "backend_attempts": independent["backend_attempts"],
                "effect_count": effect_count,
                "worker_replaced": replaced,
                "duration_seconds": elapsed,
                "time_to_recovery_seconds": elapsed if outcome == "RECOVERED" else None,
                "worker_cpu_seconds": report["cpu_seconds"],
                "checkpoint_bytes": db.stat().st_size,
                "errors": errors,
                "verification": independent,
                "worker_state": report["state"],
            }
            call(backend, "/outcome", {"outcome": outcome, "duration_seconds": elapsed})
            results.append(row)
            (directory / "result.json").write_text(json.dumps(row, indent=2), encoding="utf-8")
        finally:
            if process and process.poll() is None:
                process.kill()
                process.wait(timeout=5)
            log_handle.close()
            if scenario == "delayed_response":
                # On failure leave evidence; always restore availability, remove only our toxic.
                toxics = call(toxiproxy, "/proxies/lab")["toxics"]
                if any(t["name"] == "lab-latency" for t in toxics):
                    call(toxiproxy, "/proxies/lab/toxics/lab-latency", method="DELETE")
            call(toxiproxy, "/proxies/lab", {"enabled": True})
    summary = {
        "schema_version": 1,
        "verified_demo": all(r["passed"] for r in results),
        "scenario_count": len(results),
        "results": results,
        "metrics": {
            "recovered": sum(r["outcome"] == "RECOVERED" for r in results),
            "failed_safely": sum(r["outcome"] == "FAILED_SAFELY" for r in results),
            "human_required": sum(r["outcome"] == "HUMAN_REQUIRED" for r in results),
            "duplicate_side_effects": sum(max(0, r["effect_count"] - 1) for r in results),
            "retries": sum(r["attempts"] - 1 for r in results),
            "recovery_success_rate": sum(
                r["outcome"] == "RECOVERED" and r["passed"] for r in results
            )
            / 8,
            "retry_effectiveness": (
                sum(r["outcome"] == "RECOVERED" and r["attempts"] > 1 for r in results)
                / sum(r["attempts"] > 1 for r in results)
            ),
        },
    }
    (output / "report.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
