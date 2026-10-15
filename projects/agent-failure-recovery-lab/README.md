[Start Here — GitHub employer demo](https://github.com/texasbredmj/ai-engineering-portfolio#start-here)

# Agent Failure & Recovery Lab

Project 05 of AI Systems Engineering Lab tests what happens when authorized task execution encounters
network failures, ambiguous responses, or a worker crash. Ten repeatable experiments produce backend
receipts, durable checkpoints, error classifications, resource measurements, and recovery reports.
The lab distinguishes verified recovery, safe failure, and cases requiring human intervention.

Published under [texasbredmj](https://github.com/texasbredmj/agent-failure-recovery-lab).
[All seven implementation CI jobs passed](https://github.com/texasbredmj/agent-failure-recovery-lab/actions/runs/38501915496).
Current commit and downloaded evidence are tracked in the [portfolio index](https://github.com/texasbredmj/ai-engineering-portfolio).

## Install and demonstrate

Requires Python 3.11+ and Docker Compose. From this directory on Windows:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.lock .
docker compose up -d --build
.venv/Scripts/recovery-lab.exe run --output .lab/demo-01
.venv/Scripts/python.exe scripts/verify_observability.py
$env:LAB_STACK='1'
.venv/Scripts/python.exe -m pytest -q
```

On Linux/macOS use `.venv/bin/python` and `.venv/bin/recovery-lab`, and prefix full tests with
`LAB_STACK=1`. Without Docker, `python -m pytest -q -m 'not stack'` runs HTTP fixture/unit tests.
Use a new output directory for each experiment suite; existing evidence is never overwritten.
Run one suite at a time: experiments intentionally change the dedicated `lab` proxy's availability.
The suite restores availability and removes only the toxic it created. It never resets unrelated proxies.

Expected suite results: **8 recovered, 1 failed safely, 1 requires intervention; zero duplicate effects.**
`report.json` summarizes results. Per-scenario directories contain the worker SQLite database,
event history, worker log, worker report, and independent receipt evidence. A successful business
action requires a matching durable receipt; HTTP success or a worker assertion alone is insufficient.

```text
docker compose down
```

Stopping services retains the backend's named volume. Keep it if you want receipt evidence across
restarts. Use unique task IDs and output directories; do not reuse a key for a different quantity.
There are no paid APIs, cloud deployments, or model calls.

## Experiments

| Fault | Injection | Required observed outcome |
| --- | --- | --- |
| API timeout | Commit then delay response beyond the client deadline | Reconcile receipt; one effect |
| HTTP failures | First two execution requests return HTTP 500 before effects | Bounded retry, then verification |
| Rate limiting | First two requests return 429 with Retry-After | Respect bounded delay, then recovery |
| Malformed response | Commit then return invalid JSON | Reject response, reconcile receipt |
| Temporary service outage | Disable Toxiproxy until a transport error is recorded | Restore availability and recover |
| Worker interruption | Kill the worker after backend commit, before checkpoint completion | New process resumes the same task; one effect |
| Delayed network response | Toxiproxy adds 300ms downstream latency until a timeout | Remove the toxic and recover |
| Duplicate delivery | Deliver the same HTTP request twice and rerun the completed worker | One durable receipt/effect |
| Dependency failure | Fixture returns permanent 503, no effect | Exhaust bounded retry and fail safely |
| Permanent outage | Keep proxy disabled through all attempts | Escalate ambiguous verification to intervention |

The dependency failure is an injected upstream response, not a killed third-party dependency.
Side effects are mock ledger inserts protected by a SQLite primary key. This does not prove
exactly-once behavior for arbitrary external APIs.

## Architecture and measurements

```text
experiment controller → worker subprocess → Toxiproxy → HTTP fixture → receipt database
                     → kill/resume + durable worker checkpoints
                     → independent direct receipt checks → report
HTTP fixture metrics → Prometheus → provisioned Grafana dashboard
```

The worker validates a typed request and an allowlisted lab origin, then records legal lifecycle
transitions in SQLite. It caps execution attempts at three, persists the retry budget, uses bounded
exponential backoff with jitter, honors bounded Retry-After, and queries a receipt after every attempt.
Normal execution requests have a one-second deadline; receipt verification has an independent two-second
budget. Only timeout/latency scenarios use a deliberately short 150ms execution deadline. The worker
interruption scenario holds the response with a wider request budget so the controller can kill the
process after observing the commit. A single OS lock prevents concurrent workers using one checkpoint database; process death releases
the lock. Terminal state and its report commit together. Completed tasks return their saved report.

Reports include recovery success, retry effectiveness, scenario duration/time to recovery, completion
after interruption, classified errors, backend attempts, effect count, worker CPU time, and checkpoint
file bytes. CPU measurement covers the final worker process only; it excludes the killed process,
containers, and controller. Checkpoint bytes exclude transient WAL files. Scenario timing includes
subprocess startup and controller activity, so it is not a production latency benchmark.

Open [Prometheus](http://127.0.0.1:19090) and
[Grafana's lab dashboard](http://127.0.0.1:13000/d/lab-recovery).
Metrics expose attempts by result, committed effects, scenario outcomes, and duration histograms.
They are process-local cumulative counters and reset when the backend restarts; durable receipt
and checkpoint evidence is separate. Grafana is a local anonymous viewer for these fixtures.
The controller's `/outcome` measurements are checked against receipts in reports; metrics are not
an independent source of truth.

## Verification, CI, and limits

See [executed verification](docs/verification.md), [architecture](docs/architecture.md), and
[threat model](docs/threat-model.md). Ruff lint/format and pytest are required local checks.
GitHub Actions configures six Windows/Linux × Python 3.11/3.12/3.14 fixture jobs and one full
Docker stack job with evidence artifacts retained for 14 days. Remote results require publication
and confirmation; they are not inferred from local tests.

This is a controlled single-operator local lab. Host ports are loopback-only; control APIs have no
authentication or TLS. No unknown agent code or arbitrary commands are executed. Requests remain
bounded, but this is not an isolation boundary for hostile code. Server/storage destruction,
multi-host worker coordination, real downstream writes, and cancellation/compensation are outside
the tested scope. A permanent ambiguous outage leaves `HUMAN_REQUIRED`; rerunning a terminal task
does not silently authorize additional attempts. Human reconciliation needs a new explicit decision.

The project demonstrates failure injection, durable recovery, idempotency, ambiguity handling,
bounded retries, metrics, operational dashboards, and evidence-based reliability assessment.
