# P0 verification record

This is the historical version 0.1.0 foundation record. Current version 0.2.0 results are in
[maintenance verification](maintenance-verification.md).

Verified locally on October 12, 2026. These are single observed runs, not performance guarantees
or production-readiness claims. The machine-readable companion is
[verification-summary.json](evidence/verification-summary.json).

| Check | Environment | Observed result |
| --- | --- | --- |
| Fresh venv, pinned dependencies, non-editable package installation | Windows, Python 3.14.6 | Passed |
| `python -m pip check` | Clean Windows venv | No broken requirements |
| `ruff check .` | Windows | Passed |
| `ruff format --check .` | Windows | 16 Python files already formatted |
| `python -m pytest -q --junitxml=.task-engine/verification-tests.xml` | Clean Windows venv | 34 passed in 11.32 seconds |
| Repository inspection + test CLI demo | Clean Windows venv | SUCCEEDED, VERIFIED; 2 tool calls, 2 fixture tests |
| `docker compose build` | Docker 29.8.2, Python 3.12 Linux image | Passed |
| Full suite with project mounted read-only | Non-root Linux container, network disabled | 34 passed in 7.98 seconds |
| Bundled demo with `/data` persistence | Non-root Linux container, read-only filesystem, network disabled | SUCCEEDED, VERIFIED; 2 fixture tests |

Commands used from the project directory:

```powershell
python -m venv .venv-clean
.\.venv-clean\Scripts\python.exe -m pip install -r requirements.lock .
.\.venv-clean\Scripts\python.exe -m pip check
.\.venv-clean\Scripts\ruff.exe check .
.\.venv-clean\Scripts\ruff.exe format --check .
.\.venv-clean\Scripts\python.exe -m pytest -q --junitxml=.task-engine/verification-tests.xml
.\.venv-clean\Scripts\task-engine.exe submit examples/demo-request.json --data-dir .task-engine/clean-install --report-file .task-engine/clean-install/demo-report.json
docker compose build
docker compose run --rm engine submit examples/demo-request.json --data-dir /data --report-file /data/container-demo-report.json
```

Linux suite command (use the absolute project path in place of `PROJECT_PATH`):

```text
docker compose run --rm --entrypoint python --volume "PROJECT_PATH:/verification:ro" --workdir /verification engine -m pytest -q -p no:cacheprovider --basetemp=/data/linux-tests --junitxml=/data/linux-tests.xml tests
```

The Windows task ID was `9d385111-ab09-4e8a-be37-400e064a301a` with an observed task duration
of 1.708681 seconds. The Linux task ID was `48c52891-f2ed-4b11-80f4-5ea5bf033456` with a
duration of 0.553600 seconds. Both reports recorded zero model tokens and zero provider cost;
host compute costs were not measured.

Acceptance evidence includes invalid requests/operations, authorization denial before invocation,
invalid state transitions, bounded retries, total scheduling budget, real subprocess timeouts,
child-process cleanup, secret environment filtering, concurrent idempotency claims, durable report
retrieval, no replay of interrupted tasks, and independent inspection/JUnit verification.

Final test failures: zero. During development a child-process cleanup test found that Windows
`taskkill` was denied in the execution sandbox. The runner now uses a Job Object and a startup
gate, and the same regression passes. A manual container invocation initially omitted `--data-dir
/data` and correctly failed against its read-only root filesystem; the documented invocation passed.

Raw local evidence remains in `.task-engine/verification-tests.xml`,
`.task-engine/clean-install/demo-report.json`, and `.task-engine/container-demo-output.json`.
Linux suite JUnit is in the local Compose volume at `/data/linux-tests.xml`. Generated runtime
data and virtual environments are intentionally ignored by Git. Summary evidence is checked into
the project files, with source hashes to identify the tested implementation.

GitHub Actions is configured but has not run remotely. Python 3.11 and additional OS/version
matrix combinations await CI execution. No repository publication, cloud deployment, security
scanner result, or production usage is claimed. P0's local CLI is for trusted repositories;
the limitations in README and the threat model remain applicable.
