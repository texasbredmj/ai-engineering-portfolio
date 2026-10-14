"""Run Project 08's installed-wheel suite in the Codespaces service namespace."""
import os
import subprocess
from setup_codespaces import APP


def main():
    values = {}
    for line in (APP / '.env').read_text(encoding='utf-8').splitlines():
        if line and not line.startswith('#'):
            key, value = line.split('=', 1)
            values[key] = value.strip("'")
    postgres = subprocess.check_output(['docker', 'compose', 'ps', '-q', 'postgres'],
                                        cwd=APP, text=True).strip()
    if not postgres:
        raise SystemExit('PostgreSQL container is not running.')
    env = {**os.environ,
           'DATABASE_URL': 'postgresql://ops:' + values['POSTGRES_PASSWORD'] + '@127.0.0.1:5432/ops',
           'OPS_CREDENTIALS': values['OPS_CREDENTIALS']}
    command = ['docker', 'run', '--rm', '--user', f'{os.getuid()}:{os.getgid()}',
               '--network', 'container:' + postgres,
               '--env', 'DATABASE_URL', '--env', 'OPS_CREDENTIALS',
               '--volume', str(APP / 'tests') + ':/verification/tests:ro',
               '--volume', str(APP / 'pyproject.toml') + ':/verification/pyproject.toml:ro',
               '--volume', str(APP / '.gates') + ':/evidence',
               '--workdir', '/verification', '--entrypoint', 'python', 'lab-ops08-api',
               '-m', 'pytest', '-q', '-p', 'no:cacheprovider', '--junitxml=/evidence/tests-linux.xml']
    return subprocess.run(command, cwd=APP, env=env).returncode


if __name__ == '__main__':
    raise SystemExit(main())
