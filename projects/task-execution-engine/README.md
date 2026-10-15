[Start Here — GitHub employer demo](https://github.com/texasbredmj/ai-engineering-portfolio#start-here)

# Task Execution Engine

A deterministic repository maintenance runner that separates command execution from verified
task completion. This is Project 01 of a task completion engineering portfolio: a P0 foundation
and deterministic repository maintenance workflow,
with no LLM calls or paid services.

## Problem and architecture

Automation can exit successfully without completing its goal. This CLI validates an explicit
request, checks operation authorization, runs fixed tools, checks independent evidence, and
persists the result and audit trail in SQLite. Every task has a UUID correlation ID.

```text
JSON request → validation → plan → authorization → fixed subprocess tools
              → evidence verification → terminal state + report + ordered audit
```

Inspection is read-only. Tests execute repository Python and require explicit authorization.
The executor accepts only `inspect`, `format_fix`, `format_check`, `lint`, and `test`;
it has no free-form command or argument field.
See [architecture](docs/architecture.md) and [threat model](docs/threat-model.md).

## Installation

Python 3.11+ and a trusted target repository with `pyproject.toml` are required.
From this project directory:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock .
.\.venv\Scripts\task-engine.exe --help
```

On Linux/macOS use `.venv/bin/python` and `.venv/bin/task-engine` instead.
The installation includes pytest and Ruff because the adapters use the same interpreter.
`requirements.lock` pins the tested runtime and development dependencies; it is a version snapshot,
not a hash-verified supply-chain lock. Review and regenerate it when updating dependencies.

## Reproducible demonstration

Run from this project directory (relative repository paths resolve against the caller's working
directory, not the request file). The supplied fixture has two deterministic passing tests.
The JSON example runs inspection, read-only formatting checks, lint checks, and tests, in order.

```powershell
.\.venv\Scripts\task-engine.exe submit examples/demo-request.json --report-file .task-engine/demo-report.json
.\.venv\Scripts\task-engine.exe history
.\.venv\Scripts\task-engine.exe show TASK_UUID
.\.venv\Scripts\task-engine.exe tools
```

Success exits 0 and reports `state: SUCCEEDED`, `execution_success: true`, and
`verified_completion: true`. The report contains requested operations, authorization, timestamps,
tool argument vectors, exit codes, captured output, JUnit evidence, duration, and ordered audit.
Failures/unverified results exit 1; malformed requests and idempotency conflicts exit 2.

Repeat the same request to read the persisted report without executing tools again. Change the
idempotency key to intentionally run a new task. A key reused for different input is rejected.
Reports and JUnit artifacts live under `.task-engine/`; `--data-dir` chooses another location.
The SQLite report is canonical; `--report-file` exports a copy.

## Authorized correction demonstration

```powershell
.\.venv\Scripts\python.exe scripts/demo_maintenance.py
```

This script copies the bundled fixture into a fresh `.task-engine/demos/UUID/repository`,
introduces a known formatting problem, runs read-only checks to detect it, then submits a second
request explicitly authorizing `format_fix`. The original fixture is preserved. The workflow
applies formatting, captures a unified patch and before/after hashes, verifies Python AST
equivalence, and reruns formatting checks, lint, and tests. It also confirms duplicate submission
returns the existing report. The summary links the baseline report, final report, and patch.

For your own trusted repository, the correction request must use this order:

```json
{
  "repository": "/absolute/path/to/trusted/repository",
  "operations": ["inspect", "format_fix", "format_check", "lint", "test"],
  "authorized_operations": ["inspect", "format_fix", "format_check", "lint", "test"],
  "idempotency_key": "approved-maintenance-001",
  "max_attempts": 1
}
```

Only explicitly authorized formatting changes are allowed; lint fixes are never applied.
`format_fix` requires all three subsequent checks and cannot retry. Read-only requests may omit
operations but must preserve the relative order. Lint errors and failing tests remain failures.

Maintenance scope is at most 200 UTF-8 `.py` files totaling 10 MiB. Virtual environments, Git,
build outputs, runtime data, dependency trees, and caches are excluded. File/directory links and
hardlinked sources in scope are rejected. Ruff runs with isolated configuration, Python 3.11
syntax targeting, and a 100-character formatting line length. Lint selects `E4,E7,E9,F`.
Repository-provided Ruff configuration cannot override this policy. Files under arbitrarily named
virtual environments are not automatically excluded; use conventional `.venv*` names.

Source snapshots contain original code. Protect the artifact directory as you would the repository.
Formatting is not transactional: timeout, cancellation, or later failed verification can leave
changes in place. The original snapshot and captured patch provide recovery evidence; there is no
automatic rollback or automatic retry of corrections.

To operate on another trusted repository, copy the JSON and change `repository`. Set only the
operations you authorize in `authorized_operations`. Missing permissions fail before any tool
executes. The `test` adapter runs the repository's `tests` directory, disables plugin autoload,
clears pytest `addopts`, and stores its JUnit artifact outside the target.

## Tests and static checks

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\ruff.exe format --check .
```

Tests exercise real subprocess workflows and timeouts, CLI behavior, malformed input,
permission denial, state transitions, concurrent duplicate submissions, restart persistence,
retry exhaustion/recovery, and rejection of absent, failing, empty, or skipped-only evidence.
GitHub Actions runs deterministic checks on Windows/Linux and Python 3.11/3.12/3.14,
plus an isolated Docker demonstration. Remote CI status is not claimed until it runs.

## Docker

```text
docker compose build
docker compose run --rm engine
docker compose run --rm --entrypoint python engine scripts/demo_maintenance.py --output-dir /data/demos
```

Compose uses a non-root user, read-only root filesystem, no network, a bounded temporary
filesystem, resource limits, and persistent `/data`. The bundled demo is available inside the
image. To test another repository, mount it read-only and supply a JSON request with its container
path. The data volume must remain writable by the image user. Docker isolation is a separate
execution environment; local CLI execution is not sandboxed.

## Failure handling and limits

- Per-tool deadlines terminate the subprocess tree; total scheduling budget limits further calls.
- Inspection can retry up to three times with bounded backoff and jitter; tests cannot retry
  because arbitrary test code may have side effects.
- SQLite atomically claims idempotency keys and commits final states with reports. An interrupted
  process leaves a durable nonterminal record; duplicate submissions never blindly replay it.
- Ctrl+C attempts process cleanup and persists cancellation. Forced termination retains prior
  audit events but may leave a running record that requires operator investigation.
- Inspection verifies metadata independently; tests require exit 0 and a fresh, nonempty JUnit
  artifact with no failures/errors and at least one non-skipped test.

This implementation does not provide interactive approval, remote task
cancellation, crash resumption, distributed workers, tracing export, or LLM planning. Local
authorization is the trusted operator's request declaration, not a multi-user identity service.
JUnit is evidence from trusted tests, not proof against a malicious repository. Secrets are not
passed through the subprocess environment, but local processes still have the user's filesystem
permissions. Output returned in reports is capped at 64 KiB per stream; temporary output files
are not disk-budgeted. A target test can write files, access the network, forge evidence, or
spawn detached processes. Use a separately hardened environment for untrusted code.

## Evidence and next milestone

See [maintenance verification](docs/maintenance-verification.md) and the historical
[P0 verification record](docs/verification.md) for checks actually executed in this environment.
No production usage, deployment, remote CI success, or benchmark numbers are assumed.

The P0 foundation came first, followed by the complete deterministic maintenance demonstration.
The next project in the master prompt is **Project 02 — AI Tool Coordination Gateway**, starting
with typed tool registration/discovery and backend permission enforcement. See
[development order](docs/development-order.md). LLM planning is optional future work after
deterministic acceptance tests pass.

Demonstrated skills: typed Python interfaces, CLI design, SQLite transactions, state machines,
authorization boundaries, subprocess lifecycle control, idempotency, verification, testing, and CI.
