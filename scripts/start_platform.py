"""Single start path for Codespaces and clean Linux CI. Secrets are never printed."""
import argparse
import json
import os
import secrets
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def initialize():
    path = ROOT / '.platform/.env'
    path.parent.mkdir(exist_ok=True)
    if path.exists():
        return
    password = secrets.token_urlsafe(32)
    rows = [{'name': role, 'role': role, 'project': 'engineering-lab', 'token': secrets.token_urlsafe(32)}
            for role in ('viewer','operator','approver')]
    values = {'POSTGRES_PASSWORD': password, 'POSTGRES_PWD': password,
        'DATABASE_URL': 'postgresql://ops:' + password + '@postgres:5432/ops',
        'APP_DB_URL': 'postgresql://ops:' + password + '@postgres:5432/orchestrator',
        'OPS_CREDENTIALS': json.dumps(rows, separators=(',',':')),
        'ORCHESTRATOR_APPROVAL_KEY': secrets.token_urlsafe(32),
        'GATEWAY_OPERATOR_TOKEN': secrets.token_urlsafe(32), 'GATEWAY_ADMIN_TOKEN': secrets.token_urlsafe(32),
        'GATEWAY_API_KEY': secrets.token_urlsafe(32), 'GATEWAY_UPSTREAM_TOKEN': secrets.token_urlsafe(32),
        'TEMPORAL_ADDRESS': 'temporal:7233', 'TOOL_GATEWAY_URL': 'http://tool-gateway:8080',
        'GATEWAY_UPSTREAM_URL': 'http://bridge:8080', 'MODEL_GATEWAY_URL': 'http://model-gateway:8080',
        'GATEWAY_ROOT': '/portfolio/projects/task-execution-engine/examples/demo-repository',
        'GATEWAY_DATA_DIR': '/portfolio/.platform/gateway', 'REDIS_URL': 'redis://redis:6379/0',
        'PROVIDER_ORIGIN': 'http://providers:8080', 'OPS_PLATFORM': '1'}
    with path.open('x', encoding='utf-8') as handle:
        for key, value in values.items():
            handle.write(key + "='" + value + "'\n")
    if os.name != 'nt':
        path.chmod(0o600)
    # Backward-compatible local scripts read only these generated demo credentials.
    app_env = ROOT / 'projects/agent-operations-control-center/.env'
    with app_env.open('x', encoding='utf-8') as handle:
        handle.write('POSTGRES_PASSWORD=' + password + '\nOPS_CREDENTIALS=\'' + values['OPS_CREDENTIALS'] + "'\n")


def credentials():
    lines = (ROOT / '.platform/.env').read_text().splitlines()
    return {key: value.strip("'") for key,value in (line.split('=',1) for line in lines)}


def access_guide():
    rows=json.loads(credentials()['OPS_CREDENTIALS'])
    text='# Your private employer demo access\n\nThese generated tokens belong only to this Codespace. Keep the forwarded port private. Never commit this file.\n\n'
    for row in rows:
        text+='## '+row['role'].title()+'\n\n`'+row['token']+'`\n\n'
    text+='Open port 18780 in the Ports panel. Use `/showcase/` for the walkthrough and `/` for the dashboard. Start as operator; sign out to switch roles.\n'
    (ROOT/'.platform/DEMO-ACCESS.md').write_text(text)


def compose(*args):
    subprocess.run(['docker','compose',*args], cwd=ROOT, check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--init-only', action='store_true')
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    initialize()
    access_guide()
    if args.init_only:
        return
    compose('up','-d','--build','--wait')
    token = next(row['token'] for row in json.loads(credentials()['OPS_CREDENTIALS']) if row['role']=='viewer')
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        try:
            request = urllib.request.Request('http://127.0.0.1:18780/api/overview', headers={'Authorization':'Bearer '+token})
            with urllib.request.urlopen(request, timeout=3) as response:
                result = json.load(response)
            if any(agent['id']=='temporal-dispatcher' and agent['online'] for agent in result['agents']):
                break
        except (OSError,ValueError):
            pass
        time.sleep(1)
    else:
        raise SystemExit('Platform readiness failed. Inspect docker compose logs --tail 60 locally.')
    if args.verify:
        subprocess.run([sys.executable,'scripts/verify_platform.py'],cwd=ROOT,check=True)
    print('Ready: open forwarded port 18780 and /showcase/ for the employer walkthrough.')
    print('Open .platform/DEMO-ACCESS.md in the editor for role tokens. Keep port visibility private. No paid model endpoints are used.')


if __name__ == '__main__':
    main()
