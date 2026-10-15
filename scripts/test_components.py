"""Run isolated component contract suites without claiming unrun service checks."""
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
projects=json.loads((ROOT/'projects/source-manifest.json').read_text())
markers={3:'not integration',5:'not stack',6:'not integration',7:'not containers'}
out=ROOT/'.platform/contracts'
out.mkdir(parents=True,exist_ok=True)
for project in projects:
    if project['id']==8:
        continue  # The complete PostgreSQL suite runs inside the actual platform container.
    command=[sys.executable,'-m','pytest','-q','--tb=short','--basetemp='+str(out/('tmp-'+str(project['id'])+'-'+str(time.time_ns()))),'--junitxml='+str(out/(str(project['id'])+'.xml'))]
    if project['id'] in markers:
        command += ['-m',markers[project['id']]]
    subprocess.run(command,cwd=ROOT/project['path'],check=True)
print('All seven portable component suites passed; service demonstrations are checked separately.')
