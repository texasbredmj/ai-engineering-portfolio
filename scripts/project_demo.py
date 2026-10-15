"""Run a real project demonstration and publish its redacted exit/result evidence."""
import argparse
import json
import os
import secrets
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECTS = json.loads((ROOT / 'projects/source-manifest.json').read_text())


def run(number):
    project = PROJECTS[number-1]
    path = ROOT / project['path']
    output = ROOT / '.platform/reports'
    output.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    keyfile = ROOT / '.platform/.env'
    if keyfile.exists():
        env.update({key:value.strip("'") for key,value in (line.split('=',1) for line in keyfile.read_text().splitlines())})
    # Host processes use loopback ports; Compose-internal commands retain service addresses.
    if not Path('/.dockerenv').exists():
        env.update(TEMPORAL_ADDRESS='127.0.0.1:17233')
    commands = []
    if number == 1:
        commands = [[sys.executable,'scripts/demo_maintenance.py']]
    elif number == 2:
        commands = [[sys.executable,'scripts/demo.py'], [sys.executable,'scripts/smoke_server.py']]
    elif number == 3:
        commands = [['docker','compose','-f',str(ROOT/'compose.yaml'),'exec','-T','-w','/portfolio/.platform','api',
                     'python','-m','workflow_orchestrator.demo']]
    elif number == 4:
        commands = [[sys.executable,'scripts/demo.py']]
    elif number == 5:
        commands = [['docker','compose','up','-d','--build','backend','toxiproxy'],
                    [sys.executable,'-m','recovery_lab.cli','run','--output','.lab/employer-'+str(time.time_ns())]]
    elif number == 6:
        secret = path/'.env'
        if not secret.exists():
            secret.write_text('GATEWAY_API_KEY='+env['GATEWAY_API_KEY']+'\n')
        commands = [['docker','compose','up','-d','--build'],[sys.executable,'scripts/demo.py'],
                    [sys.executable,'scripts/verify_restart.py']]
    elif number == 7:
        commands = [[sys.executable,'scripts/demo.py'],[sys.executable,'scripts/check_tool_audit.py']]
    else:
        path = ROOT
        commands = [[sys.executable,'scripts/verify_platform.py']]
    results = []
    try:
        for command in commands:
            started = time.monotonic()
            # Retain no unreviewed subprocess logs in the public evidence endpoint.
            value = subprocess.run(command,cwd=path,env=env,capture_output=True,text=True,timeout=1200)
            summaries = []
            for line in value.stdout.splitlines():
                try:
                    item = json.loads(line)
                    if isinstance(item,dict):
                        summaries.append(item)
                except ValueError:
                    pass
            results.append({'command':command[1:] if command[0]==sys.executable else command,
                            'exit_code':value.returncode,'elapsed_seconds':round(time.monotonic()-started,3),
                            'summaries':summaries})
            if value.returncode:
                print('Project '+str(number)+' command failed; inspect the local command separately.',file=sys.stderr)
                raise RuntimeError('demonstration failed')
        report = {'state':'PASSED','project':number,'verified_at_utc':datetime.now(timezone.utc).isoformat(),'checks':results}
    except Exception as error:
        report = {'state':'FAILED','project':number,'error':type(error).__name__,'checks':results}
        raise
    finally:
        (output/(str(number)+'.json')).write_text(json.dumps(report,indent=2)+'\n')
        subprocess.run(['docker','compose','-f',str(ROOT/'compose.yaml'),'cp',str(output/(str(number)+'.json')),
                        'api:/portfolio/.platform/reports/'+str(number)+'.json'],cwd=ROOT,check=True)
    print(json.dumps({'project':number,'state':report['state']}))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('project',choices=[str(i) for i in range(1,9)]+['all'])
    args=parser.parse_args()
    for number in range(1,9) if args.project=='all' else [int(args.project)]:
        run(number)
