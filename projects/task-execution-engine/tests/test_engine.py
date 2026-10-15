import json
import time
from pathlib import Path

import pytest

from task_execution_engine.engine import Engine, verify
from task_execution_engine.models import Request, Result
from task_execution_engine.runner import command
from task_execution_engine.store import Store, now


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "pyproject.toml").write_text('[project]\nname="fixture"\nversion="0.1.0"\n')
    (root / "tests").mkdir()
    (root / "tests" / "test_ok.py").write_text("def test_ok():\n    assert 2 + 2 == 4\n")
    return root


def req(repo, **overrides):
    data = {
        "repository": str(repo),
        "operations": ["inspect", "test"],
        "authorized_operations": ["inspect", "test"],
        "idempotency_key": "integration",
    }
    data.update(overrides)
    return Request.model_validate(data)


def result(operation="inspect", code=0, stdout="{}", timed_out=False):
    return Result(
        operation=operation,
        attempt=1,
        argv=["fixed-tool"],
        started_at=now(),
        finished_at=now(),
        duration_seconds=0.01,
        exit_code=code,
        timed_out=timed_out,
        stdout=stdout,
        stderr="",
    )


class FakeRunner:
    def __init__(self, outputs):
        self.outputs = iter(outputs)
        self.calls = 0

    def run(self, *args):
        self.calls += 1
        return next(self.outputs)


def test_real_workflow_and_duplicate_no_reexecution(repo, tmp_path):
    store = Store(tmp_path / "data")
    report = Engine(store).submit(req(repo))
    assert report["state"] == "SUCCEEDED", report
    assert report["execution_success"] and report["verified_completion"]
    assert report["verification"][1]["tests"] == 1
    assert report["metrics"]["tool_calls"] == 2
    assert Path(report["verification"][1]["artifact"]).is_file()
    runner = FakeRunner([])
    cached = Engine(Store(tmp_path / "data"), runner).submit(req(repo))
    assert cached == json.loads(json.dumps(report))
    assert runner.calls == 0
    assert cached["audit"][-1]["data"]["to"] == "SUCCEEDED"


def test_unauthorized_operations_never_run(repo, tmp_path):
    runner = FakeRunner([])
    report = Engine(Store(tmp_path / "data"), runner).submit(
        req(repo, authorized_operations=["inspect"])
    )
    assert report["state"] == "FAILED"
    assert report["error"]["classification"] == "PermissionError"
    assert runner.calls == 0
    assert not report["authorization"]["approved"]


def test_invalid_repository_never_runs(tmp_path):
    runner = FakeRunner([])
    report = Engine(Store(tmp_path / "data"), runner).submit(req(tmp_path))
    assert report["state"] == "FAILED"
    assert runner.calls == 0


def test_allowlist_cannot_build_shell_command(repo, tmp_path):
    with pytest.raises(ValueError, match="allowlisted"):
        command("powershell", repo, tmp_path)


def test_exit_zero_is_not_verified_completion(repo, tmp_path):
    runner = FakeRunner([result(stdout='{"fabricated":true}')])
    report = Engine(Store(tmp_path / "data"), runner).submit(req(repo, operations=["inspect"]))
    assert report["execution_success"]
    assert not report["verified_completion"]
    assert report["state"] == "FAILED"


@pytest.mark.parametrize(
    "xml",
    [
        "<broken",
        '<testsuites><testsuite tests="0"/></testsuites>',
        "<testsuite><testcase><failure/></testcase></testsuite>",
        "<testsuite><testcase><skipped/></testcase></testsuite>",
        '<testsuite errors="1"><testcase/></testsuite>',
    ],
)
def test_junit_failure_or_empty_evidence_rejected(repo, tmp_path, xml):
    (tmp_path / "junit.xml").write_text(xml)
    assert not verify("test", repo, tmp_path, result(operation="test"))["verified"]


def test_missing_junit_rejected(repo, tmp_path):
    assert not verify("test", repo, tmp_path, result(operation="test"))["verified"]


def test_bounded_retries_exhausted(repo, tmp_path):
    runner = FakeRunner([result(code=1)] * 3)
    report = Engine(Store(tmp_path / "data"), runner).submit(
        req(repo, operations=["inspect"], max_attempts=3)
    )
    assert report["state"] == "FAILED"
    assert runner.calls == 3
    assert sum(e["data"].get("to") == "RETRYING" for e in report["audit"]) == 2


def test_retry_recovers_then_verifies(repo, tmp_path):
    out = json.dumps({"repository": str(repo), "pyproject_present": True, "tests_present": True})
    runner = FakeRunner([result(code=1), result(stdout=out)])
    report = Engine(Store(tmp_path / "data"), runner).submit(
        req(repo, operations=["inspect"], max_attempts=2)
    )
    assert report["state"] == "SUCCEEDED"
    assert report["execution_success"]
    assert runner.calls == 2


def test_interrupted_task_is_not_replayed(repo, tmp_path):
    store = Store(tmp_path / "data")
    task_id, _ = store.create(req(repo))
    runner = FakeRunner([])
    report = Engine(store, runner).submit(req(repo))
    assert report["task_id"] == task_id
    assert not report["verified_completion"]
    assert runner.calls == 0


def test_real_timeout(repo, tmp_path):
    (repo / "tests" / "test_ok.py").write_text(
        "import time\ndef test_slow():\n    time.sleep(20)\n"
    )
    report = Engine(Store(tmp_path / "data")).submit(
        req(repo, operations=["test"], timeout_seconds=0.3)
    )
    assert report["state"] == "FAILED"
    assert report["results"][0]["timed_out"]
    assert report["metrics"]["duration_seconds"] < 10


def test_failing_tests_not_verified(repo, tmp_path):
    (repo / "tests" / "test_ok.py").write_text("def test_bad():\n    assert False\n")
    report = Engine(Store(tmp_path / "data")).submit(req(repo))
    assert report["state"] == "FAILED"
    assert not report["execution_success"]
    assert not report["verified_completion"]
    assert report["completion_status"] == "PARTIAL"


def test_subprocess_does_not_inherit_secret(repo, tmp_path, monkeypatch):
    monkeypatch.setenv("ENGINE_TEST_SECRET", "sensitive-fixture")
    (repo / "tests" / "test_ok.py").write_text(
        "import os\ndef test_environment():\n    assert 'ENGINE_TEST_SECRET' not in os.environ\n"
    )
    report = Engine(Store(tmp_path / "data")).submit(req(repo))
    assert report["verified_completion"], report


def test_timeout_stops_child_process(repo, tmp_path):
    heartbeat = repo / "heartbeat.txt"
    child_code = (
        "from pathlib import Path; import time; "
        "p=Path('heartbeat.txt'); "
        "[(p.write_text(str(i)), time.sleep(0.1)) for i in range(200)]"
    )
    (repo / "tests" / "test_ok.py").write_text(
        "import subprocess, sys, time\n"
        "def test_child():\n"
        f"    subprocess.Popen([sys.executable, '-c', {child_code!r}])\n"
        "    time.sleep(20)\n"
    )
    report = Engine(Store(tmp_path / "data")).submit(
        req(repo, operations=["test"], timeout_seconds=2.0)
    )
    assert report["results"][0]["timed_out"]
    assert heartbeat.exists(), "child must have started for the cleanup test to be meaningful"
    content = heartbeat.read_text()
    time.sleep(0.5)
    assert heartbeat.read_text() == content, "child process continued after timeout"


def test_execution_budget_prevents_further_calls(repo, tmp_path, monkeypatch):
    from task_execution_engine import engine

    ticks = iter([0.0, 2.0, 2.1])
    monkeypatch.setattr(engine.time, "monotonic", lambda: next(ticks))
    runner = FakeRunner([])
    report = Engine(Store(tmp_path / "data"), runner).submit(
        req(repo, execution_budget_seconds=1.0)
    )
    assert report["error"]["classification"] == "TimeoutError"
    assert runner.calls == 0


def test_keyboard_interrupt_persists_cancelled(repo, tmp_path):
    class InterruptedRunner:
        def run(self, *args):
            raise KeyboardInterrupt

    report = Engine(Store(tmp_path / "data"), InterruptedRunner()).submit(req(repo))
    assert report["state"] == "CANCELLED"
    assert not report["verified_completion"]
