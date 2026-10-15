"""Install the same host-side project environment exercised by clean Linux CI."""
import subprocess
import sys
from pathlib import Path

root=Path(__file__).resolve().parents[1]
python=root/'.venv/bin/python'
subprocess.run([sys.executable,'-m','venv',str(root/'.venv')],check=True)
subprocess.run([str(python),'-m','pip','install','-r','platform-requirements.lock','playwright==1.64.0'],cwd=root,check=True)
packages=[str(path) for path in sorted((root/'projects').iterdir()) if (path/'pyproject.toml').is_file()]
subprocess.run([str(python),'-m','pip','install','--no-deps',*packages],cwd=root,check=True)
subprocess.run([str(python),'-m','playwright','install','--with-deps','chromium'],cwd=root,check=True)
print('All eight host-side project packages and the browser verification runtime are installed.')
