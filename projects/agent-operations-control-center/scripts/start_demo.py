"""Idempotent Docker startup for local use and Codespaces. Never print credentials."""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if not (ROOT / ".env").exists():
        subprocess.run([sys.executable, "scripts/init_local.py"], cwd=ROOT, check=True)
    subprocess.run(["docker", "compose", "up", "-d", "--build", "--wait"], cwd=ROOT, check=True)
    if not (ROOT / ".gates/http-demo.json").exists():
        subprocess.run([sys.executable, "scripts/demo.py"], cwd=ROOT, check=True)
    if args.verify:
        subprocess.run([sys.executable, "scripts/test_local.py", "-q", "--junitxml=.gates/tests-host.xml"], cwd=ROOT, check=True)
        subprocess.run([sys.executable, "scripts/verify_restart.py"], cwd=ROOT, check=True)
        subprocess.run(["docker", "compose", "--profile", "verification", "run", "--build", "--rm", "browser"], cwd=ROOT, check=True)
    print("Ready: http://127.0.0.1:18780. In Codespaces use port 18780 in the Ports panel.")
    print("Open .env locally for operator, approver and viewer tokens. Keep the forwarded port private.")


if __name__ == "__main__":
    main()
