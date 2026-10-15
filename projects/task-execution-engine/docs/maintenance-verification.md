# Project 01 maintenance verification

Executed October 12, 2026, after the [P0 foundation verification](verification.md).
This record covers package version 0.2.0. Results are observed local runs, not deployment or
production claims. See [machine-readable evidence](evidence/maintenance-summary.json).

| Check | Result |
| --- | --- |
| Non-editable package rebuilt and installed in the verification venv | Passed, version 0.2.0 |
| Windows Python 3.14.6 full suite | 50 passed in 23.87 seconds |
| Linux Python 3.12 container full suite | 50 passed in 13.57 seconds |
| Ruff lint and formatting checks | Passed |
| `pip check` | No broken requirements |
| Updated Docker image build | Passed |
| Read-only inspect → format_check → lint → test CLI request | SUCCEEDED, 4 verified operations |
| Windows correction demonstration | Initial FAILED → final SUCCEEDED, 5 verified operations |
| Non-root, network-disabled Linux correction demonstration | Initial FAILED → final SUCCEEDED |
| Duplicate submission after correction | Existing report returned without replay |

Commands run from this project directory:

```powershell
.\.venv-clean\Scripts\python.exe -m pip install --no-deps .
.\.venv-clean\Scripts\python.exe -m pytest -q --junitxml=.task-engine/maintenance-tests.xml
.\.venv-clean\Scripts\python.exe scripts/demo_maintenance.py
.\.venv-clean\Scripts\task-engine.exe submit examples/demo-request.json --data-dir .task-engine/maintenance-readonly --report-file .task-engine/maintenance-readonly-report.json
.\.venv-clean\Scripts\ruff.exe check .
.\.venv-clean\Scripts\ruff.exe format --check .
.\.venv-clean\Scripts\python.exe -m pip check
docker compose build
docker compose run --rm --entrypoint python engine scripts/demo_maintenance.py --output-dir /data/demos
```

The Linux suite additionally mounted the project read-only at `/verification`, disabled pytest
cache, and used `/data/maintenance-linux-tests` for temporary files. JUnit evidence was written
to `/data/maintenance-linux-tests.xml` and copied into local `.task-engine/` for the summary.

The Windows correction task ID was `b9a0e2ea-1d49-4aa5-8054-5fc5b2500b99`.
The Linux correction task ID was `bd4bd303-f760-443b-9ad7-f2a38cc41e87`.
Each demonstration captured one changed fixture file, a patch, source hashes, and semantic
preservation evidence. The script executes a baseline check before correction and verifies
duplicate submission afterward. Final test failures: zero.

New acceptance tests cover authorization denial without file changes, read-only failure detection,
lint failures, required workflow order and subsequent checks, mutation retry rejection, excluded
environments, hardlinks, file/byte limits, semantic changes, tampered patches, post-check edits,
missing evidence, and patch capture after a reported timeout. Existing P0 tests remain included.

Source hashes in the machine-readable summary identify tested source/configuration files. Local
runtime evidence is ignored by Git. GitHub Actions includes both demos but has not run remotely.
No repository publication or external deployment occurred. Interactive approval, transactional
rollback, crash resumption, distributed workers, and LLM planning remain outside this milestone.

The next project in the master prompt is **Project 02 — AI Tool Coordination Gateway**. Its first
executable milestone should implement typed registration/discovery, backend authorization,
one deterministic adapter, and API acceptance tests, then expand to the remaining gateway scope.
