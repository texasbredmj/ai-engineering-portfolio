"""Durable worker checkpoint and event history; one OS lock per worker database."""

import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

from .contracts import Request

LEGAL = {
    "CREATED": {"VALIDATED"},
    "VALIDATED": {"PLANNED"},
    "PLANNED": {"AUTHORIZED"},
    "AUTHORIZED": {"RUNNING"},
    "RUNNING": {"RETRYING", "VERIFYING", "FAILED", "HUMAN_REQUIRED"},
    "RETRYING": {"RUNNING", "VERIFYING", "FAILED", "HUMAN_REQUIRED"},
    "VERIFYING": {"SUCCEEDED", "RETRYING", "FAILED", "HUMAN_REQUIRED"},
    "SUCCEEDED": set(),
    "FAILED": set(),
    "HUMAN_REQUIRED": set(),
}


@contextmanager
def exclusive(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.with_suffix(".lock").open("a+b") as handle:
        handle.seek(0)
        if handle.read(1) == b"":
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        if __import__("os").name == "nt":
            import msvcrt

            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            handle.seek(0)
            if __import__("os").name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


class Store:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, timeout=2, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY, quantity INTEGER, state TEXT,
                attempts INTEGER DEFAULT 0, started REAL, report TEXT);
            CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, task_id TEXT, at REAL,
                kind TEXT, detail TEXT);
        """)

    def create(self, request: Request):
        self.db.execute(
            "INSERT OR IGNORE INTO tasks(id,quantity,state,started) VALUES(?,?,?,?)",
            (request.task_id, request.quantity, "CREATED", time.time()),
        )
        if self.task(request.task_id)["quantity"] != request.quantity:
            raise ValueError("idempotency key is bound to a different request")

    def task(self, task_id):
        row = self.db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        if row is None:
            raise ValueError("unknown task")
        return dict(row)

    def event(self, task_id, kind, detail):
        self.db.execute(
            "INSERT INTO events(task_id,at,kind,detail) VALUES(?,?,?,?)",
            (task_id, time.time(), kind, json.dumps(detail)),
        )

    def transition(self, task_id, state):
        self.db.execute("BEGIN IMMEDIATE")
        try:
            previous = self.task(task_id)["state"]
            if state not in LEGAL[previous]:
                raise ValueError(f"illegal transition {previous} -> {state}")
            self.db.execute("UPDATE tasks SET state=? WHERE id=?", (state, task_id))
            self.event(task_id, "state", {"from": previous, "to": state})
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def attempt(self, task_id):
        self.db.execute(
            "UPDATE tasks SET attempts=attempts+1 WHERE id=? AND attempts<3", (task_id,)
        )
        self.event(task_id, "attempt", {"number": self.task(task_id)["attempts"]})

    def history(self, task_id):
        return [
            dict(r)
            for r in self.db.execute(
                "SELECT at,kind,detail FROM events WHERE task_id=? ORDER BY id", (task_id,)
            )
        ]

    def finish(self, task_id, state, report):
        self.db.execute("BEGIN IMMEDIATE")
        try:
            previous = self.task(task_id)["state"]
            if state not in LEGAL[previous]:
                raise ValueError("illegal final transition")
            self.db.execute("UPDATE tasks SET state=? WHERE id=?", (state, task_id))
            self.event(task_id, "state", {"from": previous, "to": state})
            report = {**report, "state": state, "history": self.history(task_id)}
            self.db.execute("UPDATE tasks SET report=? WHERE id=?", (json.dumps(report), task_id))
            self.db.execute("COMMIT")
            return report
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def close(self):
        self.db.close()
