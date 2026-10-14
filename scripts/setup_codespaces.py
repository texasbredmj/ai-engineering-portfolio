"""Prepare the pinned real application without printing generated credentials."""
import argparse
import fcntl
import shutil
import subprocess
import sys
from pathlib import Path
from contextlib import contextmanager

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / '.demo' / 'agent-operations-control-center'
COMMIT = '2147f79a6c2bc5ca89e0134f137ed5ee5e411f17'
SOURCE = 'https://github.com/texasbredmj/agent-operations-control-center.git'


def run(*args, cwd=APP):
    subprocess.run(args, cwd=cwd, check=True)


@contextmanager
def demo_lock():
    directory = ROOT / '.demo'
    directory.mkdir(exist_ok=True)
    with (directory / 'lifecycle.lock').open('a') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def setup():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--start-only', action='store_true')
    args = parser.parse_args()
    if args.start_only and not (APP / '.venv' / 'bin' / 'python').exists():
        print('Initial setup has not finished. Post-create setup will start the application.')
        return
    if not APP.exists():
        APP.parent.mkdir(parents=True, exist_ok=True)
        run('git', 'clone', SOURCE, str(APP), cwd=ROOT)
        run('git', 'checkout', '--detach', COMMIT)
    actual = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=APP, text=True).strip()
    if actual != COMMIT:
        raise SystemExit('Demo checkout differs from the reviewed commit; refusing to replace it.')
    python = str(APP / '.venv' / 'bin' / 'python')
    if not args.start_only:
        run(sys.executable, '-m', 'venv', '.venv')
        run(python, '-m', 'pip', 'install', '-r', 'requirements.lock', '.')
    if not (APP / '.env').exists():
        run(python, 'scripts/init_local.py')
    shutil.copyfile(ROOT / '.devcontainer' / 'compose.codespaces.yml',
                    APP / 'docker-compose.override.yml')
    (APP / '.env').chmod(0o600)
    (APP / '.gates').mkdir(exist_ok=True)
    try:
        run('docker', 'compose', 'up', '-d', '--build', '--wait')
    except subprocess.CalledProcessError:
        # Keep diagnostics on the persistent workspace when Codespaces enters recovery.
        # Do not collect Compose's resolved configuration: it contains credentials.
        logs = subprocess.run(
            ['docker', 'compose', 'logs', '--no-color', '--tail', '100', 'postgres'],
            cwd=APP, capture_output=True, text=True,
        )
        diagnostic = ROOT / '.demo' / 'postgres-startup.log'
        diagnostic.write_text(logs.stdout + logs.stderr, encoding='utf-8')
        diagnostic.chmod(0o600)
        print('Startup failed. Inspect .demo/postgres-startup.log privately; do not publish raw logs.')
        raise
    if not (APP / '.gates' / 'http-demo.json').exists():
        run(python, 'scripts/demo.py')
    print('Application ready on port 18780. Use the Ports panel; keep visibility Private.')
    print('Generated credentials: .demo/agent-operations-control-center/.env (open privately).')
    print('Run python scripts/verify_codespaces.py for backend, restart and browser checks.')


def main():
    with demo_lock():
        setup()


if __name__ == '__main__':
    main()
