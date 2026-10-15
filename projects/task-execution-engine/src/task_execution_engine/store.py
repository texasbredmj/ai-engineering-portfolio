import hashlib
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .models import TRANSITIONS, Request, State


def now() -> str:
    return datetime.now(UTC).isoformat()


class Store:
    def __init__(self, directory: Path):
        self.directory = directory.resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.database = self.directory / "tasks.sqlite3"
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY, idem TEXT UNIQUE NOT NULL,
                    fingerprint TEXT NOT NULL, request TEXT NOT NULL,
                    state TEXT NOT NULL, report TEXT, created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS audit (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL REFERENCES tasks(id),
                    timestamp TEXT NOT NULL, event TEXT NOT NULL, data TEXT NOT NULL);
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.database, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    def create(self, request: Request) -> tuple[str, bool]:
        serialized = json.dumps(request.canonical(), sort_keys=True)
        fingerprint = hashlib.sha256(serialized.encode()).hexdigest()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute(
                "SELECT * FROM tasks WHERE idem=?", (request.idempotency_key,)
            ).fetchone()
            if existing:
                if existing["fingerprint"] != fingerprint:
                    raise ValueError("idempotency key already belongs to a different request")
                return existing["id"], False
            task_id, timestamp = str(uuid.uuid4()), now()
            db.execute(
                "INSERT INTO tasks VALUES (?,?,?,?,?,?,?,?)",
                (
                    task_id,
                    request.idempotency_key,
                    fingerprint,
                    serialized,
                    State.CREATED,
                    None,
                    timestamp,
                    timestamp,
                ),
            )
            self._event(db, task_id, "created", {"state": State.CREATED})
            return task_id, True

    def _event(self, db, task_id, event, data):
        db.execute(
            "INSERT INTO audit(task_id,timestamp,event,data) VALUES (?,?,?,?)",
            (task_id, now(), event, json.dumps(data)),
        )

    def event(self, task_id: str, event: str, data: dict[str, Any]) -> None:
        with self.connect() as db:
            self._event(db, task_id, event, data)

    def transition(self, task_id: str, target: State) -> None:
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT state FROM tasks WHERE id=?", (task_id,)).fetchone()
            if row is None:
                raise KeyError(task_id)
            source = State(row["state"])
            if target not in TRANSITIONS[source]:
                raise ValueError(f"illegal transition: {source} -> {target}")
            db.execute(
                "UPDATE tasks SET state=?, updated_at=? WHERE id=?", (target, now(), task_id)
            )
            self._event(db, task_id, "transition", {"from": source, "to": target})

    def finish(self, task_id: str, target: State, report: dict[str, Any]) -> dict[str, Any]:
        # Terminal state and evidence commit together: readers never see success without a report.
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT state FROM tasks WHERE id=?", (task_id,)).fetchone()
            source = State(row["state"])
            if target not in TRANSITIONS[source]:
                raise ValueError(f"illegal transition: {source} -> {target}")
            self._event(db, task_id, "transition", {"from": source, "to": target})
            report["state"] = target
            report["finished_at"] = now()
            report["audit"] = self._audit(db, task_id)
            db.execute(
                "UPDATE tasks SET state=?, report=?, updated_at=? WHERE id=?",
                (target, json.dumps(report), now(), task_id),
            )
        return report

    def _audit(self, db, task_id):
        rows = db.execute(
            "SELECT * FROM audit WHERE task_id=? ORDER BY sequence", (task_id,)
        ).fetchall()
        return [{**dict(row), "data": json.loads(row["data"])} for row in rows]

    def get(self, task_id: str) -> dict[str, Any]:
        with self.connect() as db:
            row = db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
            if row is None:
                raise KeyError(task_id)
            result = dict(row)
            result["request"] = json.loads(result["request"])
            result["report"] = json.loads(result["report"]) if result["report"] else None
            result["audit"] = self._audit(db, task_id)
            return result

    def history(self) -> list[dict[str, Any]]:
        with self.connect() as db:
            return [
                dict(row)
                for row in db.execute(
                    "SELECT id,state,created_at,updated_at FROM tasks ORDER BY created_at"
                )
            ]
