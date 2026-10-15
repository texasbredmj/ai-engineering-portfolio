import os
from pathlib import Path

import pytest
from pydantic import ValidationError

from task_execution_engine.engine import Engine, verify
from task_execution_engine.maintenance import collect_changes, snapshot
from task_execution_engine.models import Request, Result
from task_execution_engine.store import Store, now

OPERATIONS = ["inspect", "format_fix", "format_check", "lint", "test"]


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "pyproject.toml").write_text('[project]\nname="fixture"\nversion="0.1.0"\n')
    (root / "tests").mkdir()
    (root / "tests" / "test_ok.py").write_text(
        "def test_ok( ):\n assert sum([1,2,3])==6\n", encoding="utf-8"
    )
    return root


def request(root, **overrides):
    data = {
        "repository": str(root),
        "operations": OPERATIONS,
        "authorized_operations": OPERATIONS,
        "idempotency_key": "maintenance",
    }
    data.update(overrides)
    return Request.model_validate(data)


def test_full_correction_and_verification(repo, tmp_path):
    store = Store(tmp_path / "data")
    report = Engine(store).submit(request(repo))
    assert report["state"] == "SUCCEEDED", report
    assert report["verified_operations"] == 5
    assert [r["operation"] for r in report["results"]] == OPERATIONS
    changes = report["corrections"]
    assert changes["scope_valid"] and changes["semantic_preserved"]
    assert [item["path"] for item in changes["changed_files"]] == ["tests/test_ok.py"]
    patch = Path(changes["patch"]).read_text()
    assert "-def test_ok( ):" in patch and "+def test_ok():" in patch
    assert (repo / "tests/test_ok.py").read_text() == (
        "def test_ok():\n    assert sum([1, 2, 3]) == 6\n"
    )
    assert Engine(Store(tmp_path / "data")).submit(request(repo)) == report
    assert any(e["event"] == "correction_patch" for e in report["audit"])


def test_unapproved_correction_never_changes_source(repo, tmp_path):
    before = snapshot(repo)
    report = Engine(Store(tmp_path / "data")).submit(
        request(repo, authorized_operations=["inspect", "format_check", "lint", "test"])
    )
    assert report["error"]["classification"] == "PermissionError"
    assert report["results"] == []
    assert snapshot(repo) == before


def test_readonly_checks_detect_formatting_without_changes(repo, tmp_path):
    before = snapshot(repo)
    report = Engine(Store(tmp_path / "data")).submit(
        request(repo, operations=["inspect", "format_check", "lint", "test"])
    )
    assert report["state"] == "FAILED"
    assert report["results"][1]["exit_code"] == 1
    assert snapshot(repo) == before
    assert report["verification"][-1]["verified"]


def test_lint_failure_cannot_be_corrected_by_formatting(repo, tmp_path):
    (repo / "tests/test_ok.py").write_text("def test_ok():\n    assert missing == 3\n")
    report = Engine(Store(tmp_path / "data")).submit(request(repo))
    assert report["state"] == "FAILED"
    lint = next(r for r in report["results"] if r["operation"] == "lint")
    assert lint["exit_code"] == 1
    assert "F821" in lint["stdout"]
    assert not report["verified_completion"]


@pytest.mark.parametrize(
    "operations, attempts",
    [
        (["format_fix"], 1),
        (["inspect", "format_fix", "format_check", "test"], 1),
        (["test", "inspect"], 1),
        (OPERATIONS, 2),
    ],
)
def test_order_and_reverification_required(repo, operations, attempts):
    with pytest.raises(ValidationError):
        request(repo, operations=operations, max_attempts=attempts)


def test_excluded_virtual_environment_not_modified(repo):
    excluded = repo / ".venv-private"
    excluded.mkdir()
    (excluded / "untrusted.py").write_text("not valid Python")
    assert set(snapshot(repo)["files"]) == {"tests/test_ok.py"}


def test_hardlinked_source_rejected(repo, tmp_path):
    outside = tmp_path / "external.py"
    outside.write_text("print('external')")
    os.link(outside, repo / "shared.py")
    with pytest.raises(ValueError, match="hardlinked"):
        snapshot(repo)


def test_file_count_budget(repo, monkeypatch):
    from task_execution_engine import maintenance

    monkeypatch.setattr(maintenance, "MAX_FILES", 0)
    with pytest.raises(ValueError, match="files"):
        snapshot(repo)


def test_size_budget(repo, monkeypatch):
    from task_execution_engine import maintenance

    monkeypatch.setattr(maintenance, "MAX_BYTES", 10)
    with pytest.raises(ValueError, match="10 MiB"):
        snapshot(repo)


def test_changed_semantics_not_verified_as_safe(repo, tmp_path):
    before = snapshot(repo)
    (repo / "tests/test_ok.py").write_text("def test_ok():\n    assert 1 == 2\n")
    changes = collect_changes(repo, tmp_path, before)
    assert not changes["semantic_preserved"]


def test_tampered_patch_or_source_rejected(repo, tmp_path):
    report = Engine(Store(tmp_path / "data")).submit(request(repo))
    assert report["verified_completion"], report
    artifacts = Path(report["corrections"]["patch"]).parent
    result = Result(
        operation="format_fix",
        attempt=1,
        argv=[],
        started_at=now(),
        finished_at=now(),
        duration_seconds=0,
        exit_code=0,
        timed_out=False,
        stdout="",
        stderr="",
    )
    (artifacts / "format.patch").write_text("tampered")
    assert not verify("format_fix", repo, artifacts, result)["verified"]
    (repo / "tests/test_ok.py").write_text("# edited after checks\n")
    assert not verify("format_check", repo, artifacts, result)["verified"]


def test_zero_exit_without_maintenance_evidence_rejected(repo, tmp_path):
    result = Result(
        operation="lint",
        attempt=1,
        argv=[],
        started_at=now(),
        finished_at=now(),
        duration_seconds=0,
        exit_code=0,
        timed_out=False,
        stdout="[]",
        stderr="",
    )
    assert not verify("lint", repo, tmp_path, result)["verified"]


def test_timeout_still_records_changes(repo, tmp_path):
    class TimedOutFormatter:
        def run(self, operation, root, artifacts, timeout, attempt):
            if operation == "format_fix":
                (root / "tests/test_ok.py").write_text("def test_ok():\n    assert 1 == 1\n")
            return Result(
                operation=operation,
                attempt=attempt,
                argv=[],
                started_at=now(),
                finished_at=now(),
                duration_seconds=0,
                exit_code=-1,
                timed_out=True,
                stdout="",
                stderr="",
            )

    report = Engine(Store(tmp_path / "data"), TimedOutFormatter()).submit(request(repo))
    assert report["state"] == "FAILED"
    assert report["corrections"]["changed_files"]
    assert Path(report["corrections"]["patch"]).is_file()
    assert not report["verified_completion"]
