"""Loopback-only fixture control API and durable idempotent mock side effects."""

import json
import sqlite3
import threading
import time
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from pydantic import ValidationError

from .contracts import Fault, Request

REQUESTS = Counter("lab_backend_requests", "Fixture attempts", ["result"])
EFFECTS = Counter("lab_backend_effects", "Committed fixture side effects")
LATENCY = Histogram("lab_backend_request_seconds", "Fixture response latency")
OUTCOMES = Counter("lab_scenarios", "Verified scenario outcomes", ["outcome"])
RECOVERY = Histogram("lab_recovery_seconds", "Scenario duration")


class Backend:
    def __init__(self, db: Path):
        db.parent.mkdir(parents=True, exist_ok=True)
        self.path = db
        self.lock = threading.Lock()
        with self.connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS receipts(id TEXT PRIMARY KEY, quantity INTEGER);
                CREATE TABLE IF NOT EXISTS faults(id TEXT PRIMARY KEY, mode TEXT, failures INTEGER,
                    attempts INTEGER DEFAULT 0);
            """)

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.path, timeout=2)
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def configure(self, request, fault):
        with self.connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO faults VALUES(?,?,?,0)",
                (request.task_id, fault.mode, fault.failures),
            )

    def receipt(self, task_id):
        with self.connect() as conn:
            row = conn.execute("SELECT quantity FROM receipts WHERE id=?", (task_id,)).fetchone()
            attempts = conn.execute("SELECT attempts FROM faults WHERE id=?", (task_id,)).fetchone()
        return {
            "receipt": {"task_id": task_id, "quantity": row[0], "effect_count": 1} if row else None,
            "backend_attempts": attempts[0] if attempts else 0,
        }

    def execute(self, request):
        with self.lock, self.connect() as conn:
            fault = conn.execute(
                "SELECT mode,failures,attempts FROM faults WHERE id=?", (request.task_id,)
            ).fetchone()
            mode, failures, attempts = fault if fault else ("none", 0, 0)
            attempts += 1
            conn.execute("UPDATE faults SET attempts=? WHERE id=?", (attempts, request.task_id))
            if mode == "dependency" or (mode in {"http500", "rate429"} and attempts <= failures):
                REQUESTS.labels(mode).inc()
                code = 429 if mode == "rate429" else (500 if mode == "http500" else 503)
                return code, {"error": mode}, 0
            previous = conn.execute(
                "SELECT quantity FROM receipts WHERE id=?", (request.task_id,)
            ).fetchone()
            if previous and previous[0] != request.quantity:
                return 409, {"error": "idempotency conflict"}, 0
            if not previous:
                conn.execute(
                    "INSERT INTO receipts VALUES(?,?)", (request.task_id, request.quantity)
                )
                EFFECTS.inc()
            REQUESTS.labels("replay" if previous else "committed").inc()
        delay = (
            5
            if mode == "hold" and attempts == 1
            else (0.4 if mode == "delay" and attempts == 1 else 0)
        )
        body = {**request.model_dump(), "effect_count": 1}
        if mode == "malformed" and attempts <= failures:
            body = "malformed"
        return 200, body, delay


def serve(path: Path, host="127.0.0.1", port=18660):
    backend = Backend(path)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send(self, status, body, content_type="application/json"):
            data = body if isinstance(body, bytes) else json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            if status == 429:
                self.send_header("Retry-After", "0.05")
            self.end_headers()
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def do_GET(self):
            if self.path == "/health":
                self.send(200, {"ready": True})
            elif self.path == "/metrics":
                self.send(200, generate_latest(), CONTENT_TYPE_LATEST)
            elif self.path.startswith("/receipt/"):
                self.send(200, backend.receipt(self.path.removeprefix("/receipt/")))
            else:
                self.send(404, {"error": "unknown path"})

        def do_POST(self):
            started = time.monotonic()
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 4096:
                    raise ValueError("request size budget")
                body = json.loads(self.rfile.read(length))
                if self.path == "/configure":
                    request = Request.model_validate(body["request"])
                    fault = Fault.model_validate(body["fault"])
                    backend.configure(request, fault)
                    self.send(200, {"configured": True})
                elif self.path == "/execute":
                    request = Request.model_validate(body)
                    status, result, delay = backend.execute(request)
                    time.sleep(delay)
                    if result == "malformed":
                        self.send(200, b"{bad-json")
                    else:
                        self.send(status, result)
                elif self.path == "/outcome":
                    outcome = body["outcome"]
                    duration = body["duration_seconds"]
                    if (
                        outcome not in {"RECOVERED", "FAILED_SAFELY", "HUMAN_REQUIRED"}
                        or not isinstance(duration, (int, float))
                        or not 0 <= duration <= 60
                    ):
                        raise ValueError("invalid metric")
                    OUTCOMES.labels(outcome).inc()
                    RECOVERY.observe(duration)
                    self.send(200, {"recorded": True})
                else:
                    self.send(404, {"error": "unknown path"})
            except (ValueError, KeyError, TypeError, ValidationError):
                self.send(400, {"error": "invalid request"})
            finally:
                LATENCY.observe(time.monotonic() - started)

    server = ThreadingHTTPServer((host, port), Handler)
    server.daemon_threads = True
    server.serve_forever()
