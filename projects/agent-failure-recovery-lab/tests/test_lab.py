import json
import os
import socket
import subprocess
import sys

import pytest
from pydantic import ValidationError

from recovery_lab.backend import Backend
from recovery_lab.contracts import Fault, Receipt, Request, call, local_url
from recovery_lab.experiment import run_suite, wait_until
from recovery_lab.store import Store, exclusive
from recovery_lab.worker import execute, verify


@pytest.mark.parametrize("quantity", [0, -1, 11, True, "2"])
def test_request_quantity_strict(quantity):
    with pytest.raises(ValidationError):
        Request(task_id="valid", quantity=quantity)


@pytest.mark.parametrize(
    "url",
    [
        "https://localhost",
        "http://example.com",
        "http://user@localhost",
        "http://localhost/execute",
        "http://localhost?query=x",
    ],
)
def test_remote_origins_rejected(url):
    with pytest.raises(ValueError):
        local_url(url)


def test_idempotency_and_conflict(tmp_path):
    backend = Backend(tmp_path / "backend.sqlite")
    request = Request(task_id="test", quantity=2)
    backend.configure(request, Fault(mode="none"))
    assert backend.execute(request)[0] == 200
    assert backend.execute(request)[0] == 200
    assert backend.receipt("test")["receipt"]["effect_count"] == 1
    assert backend.receipt("test")["backend_attempts"] == 2
    assert backend.execute(Request(task_id="test", quantity=3))[0] == 409
    assert backend.receipt("test")["receipt"]["quantity"] == 2


def test_checkpoint_transitions_and_bound_request(tmp_path):
    store = Store(tmp_path / "worker.sqlite")
    request = Request(task_id="test", quantity=2)
    store.create(request)
    with pytest.raises(ValueError, match="illegal"):
        store.transition("test", "SUCCEEDED")
    assert store.task("test")["state"] == "CREATED"
    store.transition("test", "VALIDATED")
    store.close()
    store = Store(tmp_path / "worker.sqlite")
    assert store.task("test")["state"] == "VALIDATED"
    with pytest.raises(ValueError, match="different"):
        store.create(Request(task_id="test", quantity=3))
    store.close()


def test_atomic_terminal_report(tmp_path):
    path = tmp_path / "worker.sqlite"
    store = Store(path)
    store.create(Request(task_id="test", quantity=2))
    for state in ["VALIDATED", "PLANNED", "AUTHORIZED", "RUNNING", "VERIFYING"]:
        store.transition("test", state)
    report = store.finish("test", "SUCCEEDED", {"verified": True})
    store.close()
    store = Store(path)
    assert store.task("test")["state"] == "SUCCEEDED"
    assert json.loads(store.task("test")["report"]) == report
    with pytest.raises(ValueError):
        store.finish("test", "RUNNING", {})
    assert store.task("test")["state"] == "SUCCEEDED"
    store.close()


def test_exclusive_lock(tmp_path):
    path = tmp_path / "worker.sqlite"
    with exclusive(path):
        command = [
            sys.executable,
            "-I",
            "-c",
            "from recovery_lab.store import exclusive; from pathlib import Path; "
            f"ctx=exclusive(Path({str(path)!r})); ctx.__enter__()",
        ]
        child = subprocess.run(command, capture_output=True, timeout=5)
        assert child.returncode != 0


@pytest.mark.parametrize(
    "receipt",
    [
        {"task_id": "wrong", "quantity": 2, "effect_count": 1},
        {"task_id": "test", "quantity": 3, "effect_count": 1},
    ],
)
def test_false_receipts_fail_verification(receipt):
    assert not verify(receipt, Request(task_id="test", quantity=2))


def test_duplicate_effect_receipt_rejected():
    with pytest.raises(ValidationError):
        Receipt(task_id="test", quantity=2, effect_count=2)


@pytest.fixture
def fixture_server(tmp_path):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    log = (tmp_path / "backend.log").open("w")
    process = subprocess.Popen(
        [
            sys.executable,
            "-I",
            "-m",
            "recovery_lab.cli",
            "backend",
            "--db",
            str(tmp_path / "backend.sqlite"),
            "--port",
            str(port),
        ],
        stdout=log,
        stderr=log,
    )
    url = f"http://127.0.0.1:{port}"
    try:
        wait_until(lambda: call(url, "/health"))
        yield url
    finally:
        process.kill()
        process.wait(timeout=5)
        log.close()


@pytest.mark.parametrize(
    "mode,state,attempts",
    [
        ("none", "SUCCEEDED", 1),
        ("http500", "SUCCEEDED", 3),
        ("rate429", "SUCCEEDED", 3),
        ("malformed", "SUCCEEDED", 1),
        ("delay", "SUCCEEDED", 1),
        ("dependency", "FAILED", 3),
    ],
)
def test_http_faults_and_recovery(tmp_path, fixture_server, mode, state, attempts):
    request = Request(task_id="test-" + mode, quantity=2)
    call(
        fixture_server,
        "/configure",
        {"request": request.model_dump(), "fault": {"mode": mode, "failures": 2}},
    )
    report = execute(
        request,
        tmp_path / "worker.sqlite",
        fixture_server,
        timeout=0.15 if mode == "delay" else 1.0,
    )
    assert report["state"] == state
    assert report["attempts"] == attempts
    if mode == "delay":
        assert any(
            e["kind"] == "error" and json.loads(e["detail"])["classification"] == "transport"
            for e in report["history"]
        )
    backend = call(fixture_server, "/receipt/" + request.task_id)
    assert bool(backend["receipt"]) == (state == "SUCCEEDED")
    assert execute(request, tmp_path / "worker.sqlite", fixture_server) == report
    if mode == "rate429":
        assert all(
            json.loads(e["detail"])["seconds"] >= 0.05
            for e in report["history"]
            if e["kind"] == "backoff"
        )


def test_unavailable_backend_escalates(tmp_path):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        url = f"http://127.0.0.1:{sock.getsockname()[1]}"
        report = execute(
            Request(task_id="unavailable", quantity=2), tmp_path / "worker.sqlite", url
        )
    assert report["state"] == "HUMAN_REQUIRED"
    assert not report["verified"] and report["attempts"] == 3


@pytest.mark.stack
@pytest.mark.skipif(os.environ.get("LAB_STACK") != "1", reason="requires local Docker fault lab")
def test_complete_fault_stack(tmp_path):
    report = run_suite(
        tmp_path / "suite",
        backend=os.environ.get("LAB_BACKEND", "http://127.0.0.1:18660"),
        proxy=os.environ.get("LAB_PROXY", "http://127.0.0.1:18661"),
        toxiproxy=os.environ.get("LAB_TOXIPROXY", "http://127.0.0.1:18474"),
    )
    assert report["verified_demo"] and report["scenario_count"] == 10, json.dumps(report, indent=2)
    assert report["metrics"]["recovered"] == 8
    assert report["metrics"]["failed_safely"] == 1
    assert report["metrics"]["human_required"] == 1
    assert report["metrics"]["duplicate_side_effects"] == 0
    crash = next(r for r in report["results"] if r["scenario"] == "worker_interruption")
    assert crash["worker_replaced"] and crash["effect_count"] == 1
    assert crash["attempts"] == 2
