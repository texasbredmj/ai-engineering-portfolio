"""Run the unchanged PostgreSQL/API/worker stack on Windows without Docker.

Use an existing PostgreSQL binaries directory; no Windows service is installed.
Only recorded, matching child processes are stopped. Runtime files stay ignored.
"""
import argparse
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import psutil
import psycopg
from local_env import configure, local_env

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / ".runtime"
STATE = RUNTIME / "processes.json"


def owned(row):
    try:
        process = psutil.Process(row["pid"])
        return process if abs(process.create_time() - row["created"]) < 0.01 else None
    except psutil.NoSuchProcess:
        return None


def stop_apps(state):
    for name in ("showcase", "api", "worker"):
        process = owned(state.get(name, {"pid": -1, "created": 0})) if name in state else None
        if process:
            process.terminate()
            try:
                process.wait(10)
            except psutil.TimeoutExpired:
                process.kill()
                process.wait(5)
        state.pop(name, None)
    STATE.write_text(json.dumps(state), encoding="utf-8")


def launch(name, command, env, state):
    with (RUNTIME / (name + ".log")).open("ab") as log:
        child = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log, stderr=log,
                                 creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    state[name] = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
    STATE.write_text(json.dumps(state), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["start", "restart", "stop", "status"])
    parser.add_argument("--postgres-bin", type=Path)
    args = parser.parse_args()
    if os.name != "nt":
        parser.error("Use scripts/start_demo.py on Linux/Codespaces.")
    RUNTIME.mkdir(exist_ok=True)
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    if args.action == "status":
        print(json.dumps({key: bool(owned(row)) for key, row in state.items() if key in ("api", "worker")}))
        return
    pg = args.postgres_bin or Path(state.get("postgres_bin", ""))
    if not (pg / "pg_ctl.exe").is_file():
        parser.error("Supply --postgres-bin pointing to the extracted PostgreSQL bin directory.")
    pg = pg.resolve()
    state["postgres_bin"] = str(pg)
    data = RUNTIME / "postgres-data"
    if args.action in ("restart", "stop"):
        stop_apps(state)
    if args.action == "stop":
        subprocess.run([str(pg / "pg_ctl.exe"), "-D", str(data), "stop", "-m", "fast"], check=True)
        print("Stopped this demo. Database and credentials preserved.")
        return
    if not (ROOT / ".env").exists():
        subprocess.run([sys.executable, "scripts/init_local.py"], cwd=ROOT, check=True)
    values = local_env()
    if not (data / "PG_VERSION").exists():
        pw = RUNTIME / "init-password"
        pw.write_text(values["POSTGRES_PASSWORD"], encoding="utf-8")
        try:
            subprocess.run([str(pg / "initdb.exe"), "-D", str(data), "-U", "ops", "--pwfile=" + str(pw),
                            "--auth=scram-sha-256", "--encoding=UTF8", "--locale=C"], check=True)
        finally:
            pw.unlink(missing_ok=True)
    status = subprocess.run([str(pg / "pg_ctl.exe"), "-D", str(data), "status"], capture_output=True)
    if status.returncode:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 15438))
        launch("postgres", [str(pg / "postgres.exe"), "-D", str(data), "-h", "127.0.0.1", "-p", "15438"], dict(os.environ), state)
    configure()
    deadline = time.monotonic() + 30
    while True:
        try:
            with psycopg.connect(os.environ["DATABASE_URL"].rsplit("/", 1)[0] + "/postgres", connect_timeout=2):
                break
        except psycopg.OperationalError:
            if time.monotonic() >= deadline:
                raise SystemExit("PostgreSQL startup failed; inspect .runtime/postgres.log.")
            time.sleep(0.5)
    with psycopg.connect(os.environ["DATABASE_URL"].rsplit("/", 1)[0] + "/postgres", autocommit=True) as db:
        if not db.execute("SELECT 1 FROM pg_database WHERE datname='ops'").fetchone():
            db.execute("CREATE DATABASE ops")
    if not (ROOT / "frontend/dist/index.html").exists():
        raise SystemExit("Build the frontend first: npm ci --ignore-scripts && npm run build")
    showcase = ROOT.parent / "site" if (ROOT.parent / "site").is_dir() else ROOT.parent / "ai-engineering-portfolio/site"
    env = dict(os.environ, OPS_STATIC=str(ROOT / "frontend/dist"), OPS_SHOWCASE=str(showcase),
               PYTHONPATH=str(ROOT / "src"), PYTHONUNBUFFERED="1")
    for name, command in (
        ("api", [sys.executable, "-m", "uvicorn", "ops_center.api:create_app", "--factory", "--host", "127.0.0.1", "--port", "18780"]),
        ("worker", [sys.executable, "-m", "ops_center.worker"]),
    ):
        if name not in state or not owned(state[name]):
            if name == "api":
                with socket.socket() as probe:
                    probe.bind(("127.0.0.1", 18780))
            launch(name, command, env, state)
    deadline = time.monotonic() + 35
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen("http://127.0.0.1:18780/healthz", timeout=2) as response:
                if response.status == 200:
                    print("Ready: http://127.0.0.1:18780. Read role tokens from the ignored .env locally.")
                    return
        except OSError:
            time.sleep(0.5)
    raise SystemExit("Startup failed. Inspect .runtime/api.log and .runtime/worker.log locally.")


if __name__ == "__main__":
    main()
