import hashlib
import json
import random
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from .maintenance import collect_changes, hashes, save_snapshot, snapshot
from .models import Request, Result, State
from .runner import Runner
from .store import Store


def validate_repository(path: str) -> Path:
    root = Path(path).resolve(strict=True)
    if not root.is_dir() or not (root / "pyproject.toml").is_file():
        raise ValueError("repository must be a directory containing pyproject.toml")
    tests = root / "tests"
    if tests.exists() and (tests.is_symlink() or not tests.resolve().is_relative_to(root)):
        raise ValueError("tests directory must remain inside repository")
    return root


def verify(operation: str, repository: Path, artifact_dir: Path, result: Result) -> dict[str, Any]:
    evidence = {"operation": operation, "verified": False}
    if result.exit_code != 0 or result.timed_out or result.error:
        return {**evidence, "reason": "execution did not succeed"}
    if operation == "inspect":
        try:
            actual = json.loads(result.stdout)
            expected = {
                "repository": str(repository),
                "pyproject_present": True,
                "tests_present": (repository / "tests").is_dir(),
            }
            valid = actual == expected and (repository / "pyproject.toml").is_file()
            return {**evidence, "verified": valid, "expected": expected, "observed": actual}
        except (ValueError, TypeError):
            return {**evidence, "reason": "invalid inspection output"}
    if operation in {"format_fix", "format_check", "lint"}:
        try:
            proof = json.loads(
                (artifact_dir / f"{operation}-evidence.json").read_text(encoding="utf-8")
            )
            current = hashes(snapshot(repository))
            valid = proof["operation"] == operation and proof["exit_code"] == 0
            valid = valid and proof["after_hashes"] == current and bool(current)
            if operation == "format_fix":
                changes = json.loads(
                    (artifact_dir / "format-changes.json").read_text(encoding="utf-8")
                )
                valid = valid and changes["scope_valid"] and changes["after_hashes"] == current
                valid = valid and changes["semantic_preserved"]
                valid = valid and changes["before_hashes"] == proof["before_hashes"]
                valid = (
                    valid
                    and hashlib.sha256((artifact_dir / "format.patch").read_bytes()).hexdigest()
                    == changes["patch_sha256"]
                )
            else:
                valid = valid and proof["before_hashes"] == current
                if operation == "lint":
                    valid = valid and proof["diagnostics"] == []
                else:
                    valid = valid and (artifact_dir / "format_check-stdout.txt").read_bytes() == b""
            return {
                **evidence,
                "verified": valid,
                "checked_files": len(current),
                "artifact": str(artifact_dir / f"{operation}-evidence.json"),
            }
        except (OSError, ValueError, KeyError, TypeError) as exc:
            return {**evidence, "reason": f"invalid maintenance evidence: {exc}"}
    if operation != "test":
        return {**evidence, "reason": "unknown verification operation"}
    artifact = artifact_dir / "junit.xml"
    try:
        if artifact.stat().st_size > 10 * 1024 * 1024:
            raise ValueError("JUnit artifact exceeds verification limit")
        root = ET.parse(artifact).getroot()
        cases = list(root.iter("testcase"))
        failed = sum(
            1
            for case in cases
            if case.find("failure") is not None or case.find("error") is not None
        )
        skipped = sum(1 for case in cases if case.find("skipped") is not None)
        suites = list(root.iter("testsuite"))
        suite_errors = sum(int(suite.get("errors", "0")) for suite in suites)
        suite_failures = sum(int(suite.get("failures", "0")) for suite in suites)
        valid = len(cases) > skipped and failed == 0 and suite_errors == suite_failures == 0
        return {
            **evidence,
            "verified": valid,
            "tests": len(cases),
            "skipped": skipped,
            "failures": failed,
            "suite_errors": suite_errors,
            "artifact": str(artifact),
        }
    except (OSError, ValueError, ET.ParseError) as exc:
        return {**evidence, "reason": f"invalid or missing JUnit evidence: {exc}"}


class Engine:
    def __init__(self, store: Store, runner: Runner | None = None):
        self.store = store
        self.runner = runner or Runner()

    def submit(self, request: Request) -> dict[str, Any]:
        task_id, created = self.store.create(request)
        if not created:
            record = self.store.get(task_id)
            return record["report"] or {
                "task_id": task_id,
                "state": record["state"],
                "verified_completion": False,
                "reason": "existing task in progress or interrupted; no automatic replay",
                "audit": record["audit"],
            }
        record = self.store.get(task_id)
        report = {
            "schema_version": "1.0",
            "task_id": task_id,
            "correlation_id": task_id,
            "request": request.canonical(),
            "started_at": record["created_at"],
            "authorization": {"approved": False},
            "results": [],
            "verification": [],
            "execution_success": False,
            "verified_completion": False,
            "metrics": {"tool_calls": 0, "cost_usd": 0, "tokens": 0},
        }
        started = time.monotonic()
        try:
            repository = validate_repository(request.repository)
            if "test" in request.operations and not (repository / "tests").is_dir():
                raise ValueError("test operation requires a tests directory")
            self.store.transition(task_id, State.VALIDATED)
            self.store.transition(task_id, State.PLANNED)
            missing = set(request.operations) - set(request.authorized_operations)
            if missing:
                raise PermissionError(
                    f"operations require explicit authorization: {sorted(missing)}"
                )
            report["authorization"] = {
                "approved": True,
                "operations": request.authorized_operations,
            }
            self.store.event(task_id, "authorization", report["authorization"])
            self.store.transition(task_id, State.AUTHORIZED)
            self.store.transition(task_id, State.RUNNING)
            artifacts = self.store.directory / "artifacts" / task_id
            artifacts.mkdir(parents=True, exist_ok=False)
            final_results = {}
            for operation in request.operations:
                before = None
                if operation in {"format_fix", "format_check", "lint"}:
                    before = save_snapshot(repository, artifacts, operation)
                    self.store.event(
                        task_id,
                        "source_snapshot",
                        {
                            "operation": operation,
                            "files": len(before["files"]),
                            "bytes": before["total_bytes"],
                        },
                    )
                for attempt in range(1, request.max_attempts + 1):
                    remaining = request.execution_budget_seconds - (time.monotonic() - started)
                    if remaining <= 0:
                        raise TimeoutError("task execution budget exhausted")
                    self.store.event(
                        task_id, "tool_started", {"operation": operation, "attempt": attempt}
                    )
                    try:
                        result = self.runner.run(
                            operation,
                            repository,
                            artifacts,
                            min(request.timeout_seconds, remaining),
                            attempt,
                        )
                    finally:
                        if operation == "format_fix":
                            report["corrections"] = collect_changes(repository, artifacts, before)
                            self.store.event(task_id, "correction_patch", report["corrections"])
                    report["results"].append(result.model_dump())
                    report["metrics"]["tool_calls"] += 1
                    self.store.event(task_id, "tool_finished", result.model_dump())
                    if result.exit_code == 0 and not result.timed_out and not result.error:
                        break
                    if attempt < request.max_attempts:
                        self.store.transition(task_id, State.RETRYING)
                        delay = min(
                            0.1 * 2 ** (attempt - 1) + random.uniform(0, 0.05),
                            max(0, request.execution_budget_seconds - (time.monotonic() - started)),
                        )
                        time.sleep(delay)
                        self.store.transition(task_id, State.RUNNING)
                final_results[operation] = result
            self.store.transition(task_id, State.VERIFYING)
            report["verification"] = [
                verify(op, repository, artifacts, final_results[op]) for op in request.operations
            ]
            # Historical failed attempts do not override a successfully verified final attempt.
            report["execution_success"] = all(
                r.exit_code == 0 and not r.timed_out and not r.error for r in final_results.values()
            )
            report["verified_completion"] = all(v["verified"] for v in report["verification"])
            self.store.event(task_id, "verification", {"evidence": report["verification"]})
            final = State.SUCCEEDED if report["verified_completion"] else State.FAILED
        except (Exception, KeyboardInterrupt) as exc:
            report["error"] = {"classification": type(exc).__name__, "message": str(exc)}
            self.store.event(task_id, "error", report["error"])
            final = State.CANCELLED if isinstance(exc, KeyboardInterrupt) else State.FAILED
        report["metrics"]["duration_seconds"] = time.monotonic() - started
        completed = sum(v["verified"] for v in report["verification"])
        report["verified_operations"] = completed
        report["completion_status"] = (
            "VERIFIED"
            if report["verified_completion"]
            else "CANCELLED"
            if final == State.CANCELLED
            else "PARTIAL"
            if completed
            else "UNVERIFIED"
            if report["execution_success"]
            else "FAILED_EXECUTION"
        )
        return self.store.finish(task_id, final, report)
