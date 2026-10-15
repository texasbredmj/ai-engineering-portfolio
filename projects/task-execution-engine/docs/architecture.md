# Architecture and decisions

`models.py` defines strict requests and legal transitions. `store.py` persists task requests,
state, canonical reports, and ordered JSON audit events. `runner.py` maps operation names to
fixed argument vectors and captures bounded report output. `engine.py` controls execution,
authorization, retry budgets, and verification. `cli.py` is the operator interface.

SQLite uses short connections, explicit immediate write transactions, foreign keys, and a
10-second lock wait. A unique idempotency key and canonical request fingerprint prevent concurrent
duplicates and conflicting reuse. Terminal state, report, and final audit event commit atomically.
The one owner that inserted a task may execute it; duplicate submitters only inspect it.

Normal lifecycle:

```text
CREATED → VALIDATED → PLANNED → AUTHORIZED → RUNNING → VERIFYING → SUCCEEDED
RUNNING → RETRYING → RUNNING
```

Each nonterminal state permits FAILED or CANCELLED. PLANNED can enter WAITING_APPROVAL;
the latter is reserved for a later human approval interface. All terminal states reject further
transitions. Persistence supports history across restarts, not automatic interrupted-task recovery.

The tool registry exposes version, schemas, permissions, timeout, retry eligibility, idempotency,
side effects, approval requirements, and execution budgets. All five adapters are implemented
locally; none accepts arbitrary command text. Request values narrow per-tool deadlines.
Each test run gets a unique task artifact directory, preventing accidental stale JUnit reuse.

Verification requires independent filesystem comparison for inspection and successful subprocess
execution plus valid JUnit evidence for tests. Historical retry failures remain in the report;
the final attempt determines execution success. Failed verification produces FAILED even when
the command exits zero. Metrics record wall-clock duration, tool calls, zero model tokens, and
zero provider cost; they do not claim CPU measurement or cost of host resources.

Tradeoffs: subprocess execution offers a small predictable control surface but is not a sandbox.
SQLite provides local atomicity without deployment services. Pytest as a runtime dependency makes
the test adapter reproducible. Separate PostgreSQL/workflow orchestration belongs to later projects.

## Deterministic maintenance workflow

Requests preserve the relative order `inspect → format_fix → format_check → lint → test`.
Formatting corrections require explicit authorization plus all three subsequent checks. No
mutation or test operation is retried. Read-only maintenance operations can use bounded retries.

`maintenance.py` scopes at most 200 UTF-8 Python files and 10 MiB, rejecting source links and
hardlinks. Snapshots preserve original contents and SHA-256 hashes before each operation.
The wrapper rechecks those hashes immediately before invoking fixed isolated Ruff commands.
Formatting ignores target-provided configuration and uses a 100-character line length and
Python 3.11 target. Lint uses `E4,E7,E9,F` and never applies corrections.

After formatting, the parent captures changes, unified diff, scope equality, and AST equality.
It records this evidence even when the runner reports a timeout. Final verification checks
evidence against the current source hashes, patch digest, formatting diff, lint diagnostics, and
JUnit output. A missing artifact or post-check source change fails verification. The full source
snapshots remain available if a timeout leaves partially applied edits. There is no transaction
across repository file writes, and no automatic rollback.

`scripts/demo_maintenance.py` uses a new fixture copy per invocation, records the initial failed
formatting check, submits an explicitly authorized correction, and verifies all five operations
and duplicate-submission behavior. The original fixture is never modified by this demonstration.
