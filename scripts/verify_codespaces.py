"""Run real checks and write a redacted result, preserving failures as failures."""
import hashlib
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

from setup_codespaces import APP, COMMIT, ROOT


def main():
    if not (APP / '.env').exists():
        raise SystemExit('Run python scripts/setup_codespaces.py first.')
    python = str(APP / '.venv' / 'bin' / 'python')
    gates = APP / '.gates'
    gates.mkdir(exist_ok=True)
    commands = [
        ['docker', 'compose', 'up', '-d', '--build', '--wait'],
        [python, 'scripts/test_local.py', '-q', '--junitxml=.gates/tests-codespaces.xml'],
        [sys.executable, str(ROOT / 'scripts' / 'verify_codespaces_wheel.py')],
        [python, 'scripts/demo.py'],
        [python, 'scripts/verify_restart.py'],
        ['docker', 'compose', '--profile', 'verification', 'run', '--build', '--rm', 'browser'],
    ]
    report = {
        'checked_at': datetime.now(timezone.utc).isoformat(),
        'environment': 'codespaces' if os.environ.get('CODESPACES') == 'true' else 'other',
        'expected_app_commit': COMMIT,
        'app_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=APP, text=True).strip(),
        'portfolio_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'compose_override_sha256': hashlib.sha256((APP / 'docker-compose.override.yml').read_bytes()).hexdigest(),
        'commands': [], 'runtime_checks_passed': False,
        'forwarded_browser_verified': False,
        'limitations': ['Forwarded URL and private port visibility require a separate browser check.',
                        'Fixture runtime; no live models or production identity.'],
    }
    status = 1
    try:
        assert report['app_commit'] == COMMIT, 'Unexpected application commit'
        for command in commands:
            result = subprocess.run(command, cwd=APP)
            report['commands'].append({'command': [x.replace(str(APP), '<app>') for x in command],
                                       'exit_code': result.returncode})
            if result.returncode:
                raise RuntimeError('Verification command failed; see terminal locally.')
        suites = ET.parse(gates / 'tests-codespaces.xml').getroot().iter('testsuite')
        counts = {k: 0 for k in ('tests', 'failures', 'errors', 'skipped')}
        for suite in suites:
            for key in counts:
                counts[key] += int(suite.get(key, 0))
        assert counts == {'tests': 35, 'failures': 0, 'errors': 0, 'skipped': 0}, counts
        wheel_counts = {k: 0 for k in counts}
        for suite in ET.parse(gates / 'tests-linux.xml').getroot().iter('testsuite'):
            for key in wheel_counts:
                wheel_counts[key] += int(suite.get(key, 0))
        assert wheel_counts == counts, wheel_counts
        demo = json.loads((gates / 'http-demo.json').read_text())
        browser = json.loads((gates / 'browser-check.json').read_text())
        restart = json.loads((gates / 'restart-check.json').read_text())
        assert demo['verified_demo'] and demo['scenario_count'] == 8
        assert browser['verified_browser'] and browser['scenario_count'] == 8
        assert not browser['uncaught_page_errors']
        assert restart['all_records_preserved'] and restart['duplicate_effects'] == 0
        report.update(runtime_checks_passed=True, tests=counts,
                      installed_wheel_tests=wheel_counts,
                      http_scenarios=8, browser_scenarios=8, restart_verified=True)
        report['artifacts'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in gates.iterdir() if p.suffix in ('.json', '.xml', '.png')}
        status = 0
    except (AssertionError, OSError, RuntimeError, ValueError) as error:
        report['failure_type'] = type(error).__name__
    finally:
        destination = ROOT / '.demo' / 'verification.json'
        destination.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({'runtime_checks_passed': report['runtime_checks_passed'],
                          'report': '.demo/verification.json',
                          'forwarded_browser_verified': False}))
    return status


if __name__ == '__main__':
    sys.exit(main())
