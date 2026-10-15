"""Open the private guide when an editor is attached; headless CI has no editor."""
import shutil
import subprocess
from pathlib import Path

guide=Path(__file__).resolve().parents[1]/'.platform/DEMO-ACCESS.md'
editor=shutil.which('code')
opened=False
if editor and guide.exists():
    try:
        result=subprocess.run([editor,str(guide)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=10)
        opened=result.returncode==0
    except (OSError,subprocess.TimeoutExpired):
        pass
if not opened:
    print('Open .platform/DEMO-ACCESS.md in the editor for your private demo role tokens.')
