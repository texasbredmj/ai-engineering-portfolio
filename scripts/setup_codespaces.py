"""Prepare the pinned real application without printing generated credentials."""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / '.demo' / 'agent-operations-control-center'
COMMIT = '2147f79a6c2bc5ca89e0134f137ed5ee5e411f17'
SOURCE = 'https://github.com/texasbredmj/agent-operations-control-center.git'


def run(*args, cwd=APP):
    subprocess.run(args, cwd=cwd, check=True)


def main():
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
    run('docker', 'compose', 'up', '-d', '--build', '--wait')
    if not (APP / '.gates' / 'http-demo.json').exists():
        run(python, 'scripts/demo.py')
    print('Application ready on port 18780. Use the Ports panel; keep visibility Private.')
    print('Generated credentials: .demo/agent-operations-control-center/.env (open privately).')
    print('Run python scripts/verify_codespaces.py for backend, restart and browser checks.')


if __name__ == '__main__':
    main()
