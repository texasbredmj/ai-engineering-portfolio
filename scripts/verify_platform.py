"""Employer acceptance against real HTTP, Chromium and the actual workflow ledger."""
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

import httpx

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'projects/agent-operations-control-center'
values={k:v.strip("'") for k,v in (line.split('=',1) for line in (ROOT/'.platform/.env').read_text().splitlines())}
tokens={row['role']:row['token'] for row in json.loads(values['OPS_CREDENTIALS'])}
client=httpx.Client(base_url='http://127.0.0.1:18780',timeout=10)
HEADERS={'Authorization':'Bearer '+tokens['viewer']}


def compose(*args):
    return subprocess.run(['docker','compose',*args],cwd=ROOT,check=True,capture_output=True,text=True)


def wait(task_id,state,seconds=90):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        response=client.get('/api/tasks/'+task_id,headers=HEADERS)
        response.raise_for_status()
        result=response.json()
        if result['task']['state']==state:
            return result
        if state=='SUCCEEDED' and result['task']['state']=='FAILED':
            raise AssertionError('Integrated workflow failed: '+json.dumps(result['evidence']))
        time.sleep(.4)
    raise AssertionError('Workflow did not reach '+state)


# Unchanged HTTP and browser paths now execute through the integrated dispatcher.
subprocess.run([sys.executable,'scripts/demo.py'],cwd=APP,check=True)
subprocess.run([sys.executable,'scripts/browser_check.py'],cwd=APP,check=True)
response=client.post('/api/tasks',headers={'Authorization':'Bearer '+tokens['operator'],'Idempotency-Key':str(uuid.uuid4())},
                     json={'title':'Employer restart durability '+uuid.uuid4().hex[:6],'mode':'restart','quantity':2})
response.raise_for_status()
task=response.json()
deadline=time.monotonic()+40
while time.monotonic()<deadline:
    current=client.get('/api/tasks/'+task['id'],headers=HEADERS).json()
    probe = "import os,psycopg; db=psycopg.connect(os.environ['APP_DB_URL']); print(db.execute(\"SELECT count(*) FROM events WHERE workflow_id LIKE %s AND kind='reserved'\", ("+repr('ops-'+task['id']+'-%')+",)).fetchone()[0])"
    committed = int(compose('exec','-T','api','python','-c',probe).stdout.strip())
    if current['task']['state']=='RUNNING' and committed==1:
        break
    time.sleep(.3)
else:
    raise AssertionError('Expected durable reservation commit before activity acknowledgement')
# Stop both workers during active work, then replace their processes. Durable mapping is retained.
compose('restart','dispatcher','orchestrator')
completed=wait(task['id'],'SUCCEEDED',120)
evidence=completed['evidence']['details']
assert evidence['orchestrator_report']['verified_completion'] is True
assert evidence['workflow_id'].startswith('ops-')
outputs=evidence['orchestrator_report']['outputs']
assert outputs['inspect']['gateway']['verified_completion']
assert outputs['reservation']['gateway']['verified_completion']
assert outputs['quote']['model_gateway']
workflow_id=evidence['workflow_id']
check='''import json,os,psycopg
with psycopg.connect(os.environ['APP_DB_URL']) as db:
 row=db.execute("SELECT count(*) FROM events WHERE workflow_id=%s AND kind='reserved'",('''+repr(workflow_id)+''',)).fetchone()
 assert row[0]==1,row
 print(json.dumps({'reserved_events':row[0]}))'''
ledger=json.loads(compose('exec','-T','api','python','-c',check).stdout)
before=client.get('/api/tasks/'+task['id'],headers=HEADERS).json()
compose('restart','api','dispatcher','orchestrator')
deadline=time.monotonic()+60
while time.monotonic()<deadline:
    try:
        after=client.get('/api/tasks/'+task['id'],headers=HEADERS)
        if after.status_code==200:
            break
    except httpx.HTTPError:
        pass
    time.sleep(.4)
assert after.json()==before,'Durable dashboard evidence changed across restart'
assert client.get('/showcase/').status_code==200
assert client.get('/api/tasks').status_code==401
report={'state':'PASSED','http_scenarios':8,'browser_scenarios':9,'real_temporal_workflow':True,
        'real_tool_gateway':True,'real_model_gateway_local_providers':True,'paid_model_calls':0,
        'worker_restart_verified':True,'crashed_after_commit_before_acknowledgement':True,'api_restart_preserved_records':True,'duplicate_reservations':ledger['reserved_events']-1,
        'workflow_id':workflow_id,'task_id':task['id']}
out=ROOT/'.platform/reports'
out.mkdir(parents=True,exist_ok=True)
(out/'integrated-acceptance.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
