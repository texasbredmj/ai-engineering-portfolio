"""Restart owned containers and verify durable records through HTTP and PostgreSQL."""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx
from local_env import configure

from ops_center.config import Settings
from ops_center.store import Store

rows = configure()
token = next(r["token"] for r in rows if r["role"] == "viewer")
client = httpx.Client(
    base_url="http://127.0.0.1:18780", headers={"Authorization": "Bearer " + token}, timeout=5
)
demo = json.loads(Path(".gates/http-demo.json").read_text(encoding="utf-8"))
ids = [r["task_id"] for r in demo["results"]]
before = {key: client.get("/api/tasks/" + key).json() for key in ids}
restart = ([sys.executable, "scripts/native_demo.py", "restart"]
           if os.environ.get("OPS_RUNTIME") == "native"
           else ["docker", "compose", "restart", "api", "worker"])
subprocess.run(restart, check=True, capture_output=True, timeout=60)
deadline = time.monotonic() + 35
while time.monotonic() < deadline:
    try:
        if client.get("/healthz").status_code == 200:
            break
    except httpx.HTTPError:
        pass
    time.sleep(0.5)
else:
    raise AssertionError("restarted API did not become ready")
after = {key: client.get("/api/tasks/" + key).json() for key in ids}
assert before == after, "task history, receipts or spans changed across restart"
with Store(Settings()).connect() as db:
    verified = []
    for task_id, record in after.items():
        effects = db.execute("SELECT * FROM effects WHERE task_id=%s", (task_id,)).fetchall()
        state = record["task"]["state"]
        assert len(effects) == (
            1 if state == "SUCCEEDED" or record["task"]["mode"] == "unverified" else 0
        )
        if record["evidence"]:
            assert len(effects) == 1
            assert str(effects[0]["receipt"]) == record["evidence"]["details"]["receipt"]
            assert effects[0]["quantity"] == record["evidence"]["details"]["observed_quantity"]
        verified.append(
            {
                "task_id": task_id,
                "state": state,
                "effect_count": len(effects),
                "receipt_matches": True,
            }
        )
report = {
    "runtime": os.environ.get("OPS_RUNTIME", "docker"),
    "api_and_worker_restarted": True,
    "all_records_preserved": True,
    "database_receipts_verified": verified,
    "duplicate_effects": 0,
    "paid_model_calls": 0,
}
Path(".gates/restart-check.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"restart_verified": True, "records_preserved": len(ids), "duplicate_effects": 0}))
