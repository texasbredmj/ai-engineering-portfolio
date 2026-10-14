# AI Systems Engineering Lab

**[Start Here — launch the guided demo in GitHub Codespaces](https://github.com/codespaces/new?repo=texasbredmj/ai-engineering-portfolio&ref=showcase%2Fcodespaces-verification)**

Fresh Codespace application checks passed: 35 host tests, the same 35 tests against the installed wheel, eight HTTP scenarios, eight Chromium scenarios and restart preservation with zero duplicate effects. Authenticated task creation, receipt inspection, mismatch investigation and traces also passed through the private forwarded URL. **Automatic portfolio-devcontainer startup is still being verified.**

[Startup and five guided exercises](docs/CODESPACES-VERIFICATION.md) · [Raw execution evidence and hashes](evidence/codespaces-app-2026-10-14.json) · [Forwarded browser check](evidence/codespaces-forwarded-ui.json).

An engineering portfolio focused on AI systems that complete authorized tasks, coordinate tools,
recover from failures, and independently verify outcomes. Projects use deterministic baselines
before introducing model-driven planning. Completion requires observable evidence rather than
an agent's assertion.

The specialization spans AI automation, integration, task orchestration, evaluation, and reliability.
Each technical project is independently installable, testable, and demonstrable; repositories share
engineering conventions without depending on one another at runtime.

## Phase 1 delivery checkpoint

**Phase 1 delivery is verified: both repositories are pushed and their required remote CI is green.**
Confirmed local checks on October 13, 2026: 50 tests passed for Project 01 and 30 for Project 02,
with lint, formatting, dependency checks, and both deterministic demos passing. Remote JUnit artifacts independently confirm 50 and 30 passing tests, with zero failures. Both
projects passed six OS/Python matrix jobs and one Docker job. These counts describe fixture suites;
they are not production performance claims.

| Project | Repository visibility | Implemented capabilities | Current delivery status |
| --- | --- | --- | --- |
| [01 — Task Execution Engine](https://github.com/texasbredmj/task-execution-engine) | Private; access required | CLI, strict requests, SQLite lifecycle/audit, bounded fixed commands, idempotency, approved formatting corrections, patch capture, independent verification | Published; [7/7 CI jobs passed](https://github.com/texasbredmj/task-execution-engine/actions/runs/38367464942) |
| [02 — AI Tool Coordination Gateway](https://github.com/texasbredmj/ai-tool-coordination-gateway) | Public | Typed registry/discovery, four adapters, backend permissions, separate approval, concurrency/rate budgets, durable no-replay claims, independent receipt verification | Published; [7/7 CI jobs passed](https://github.com/texasbredmj/ai-tool-coordination-gateway/actions/runs/38367470323) |

[Machine-readable checkpoint evidence](evidence/phase1.json) records the exact published commits,
workflow run URLs, all fourteen successful job conclusions, twelve evidence artifacts, and sampled remote JUnit results.

## Project 03 delivery checkpoint

[03 — Autonomous Workflow Orchestrator](https://github.com/texasbredmj/autonomous-workflow-orchestrator)
is published as a public repository. [All seven remote CI jobs passed](https://github.com/texasbredmj/autonomous-workflow-orchestrator/actions/runs/38466787806)
against commit `2adc05287b98bb4e6969af19124a99d8bfd73035` on October 13, 2026.
Six policy jobs cover Windows/Linux and Python 3.11/3.12/3.14. The durability job starts real
Temporal and PostgreSQL services, runs all 16 tests with zero failures, errors, or skips, and builds
the worker container. Downloaded evidence confirms all eight recovery/authorization scenarios,
including a worker process crash after database commit: the replacement worker retries the activity
and verifies exactly one reservation.

Capabilities include durable scheduling, parallel activities, conditional branching, signed approvals,
bounded retries, cancellation, compensation, and independent outcome verification. Local Windows and
Linux suites also passed all 16 tests. These are controlled fixture results, not production availability
or arbitrary external API exactly-once guarantees.

[Project 03 evidence](evidence/project03.json) preserves the commit, job conclusions, artifact checksum,
JUnit counts, and scenario results. Raw GitHub artifacts have a 14-day retention period.
Projects 03 and 04 are now published with verified remote CI. Phase 2 delivery is complete.

## Project 04 delivery checkpoint

[04 — Agent Evaluation Harness](https://github.com/texasbredmj/agent-evaluation-harness) is published
as a public repository. [All seven remote CI jobs passed](https://github.com/texasbredmj/agent-evaluation-harness/actions/runs/38491909891)
against commit `2f6483442fda112a98e6e322d82f10c89838899d` on October 13, 2026.
Six downloaded Windows/Linux × Python 3.11/3.12/3.14 artifacts each independently confirm 30 tests
with zero failures, errors, or skips, a passing 14-case baseline across ten evaluation dimensions,
and rejection of all four deliberately faulty candidates. The seventh job builds the container and
runs the baseline with networking disabled. Suite and decision hashes match across all six artifacts.

Capabilities include strict JSONL contracts, policy-controlled mock tools, independent outcome scoring,
resource budgets, token/cost accounting, OpenTelemetry traces, and paired version regression gates.
Recorded model decisions can be evaluated offline with explicit measurements and pricing. The baseline
uses zero model tokens and two deliberately denied policy probes; those attempts are recorded and have
no effects. These are controlled fixture results, not live model or production performance claims.

[Project 04 evidence](evidence/project04.json) preserves the exact commit, all job conclusions, six
artifact checksums, parsed JUnit counts, benchmark scores, and regression results. Local clean Windows
and Linux installations also each passed 30 tests. Raw GitHub artifacts are retained for 14 days.
**Phase 2 delivery is verified. Project 05 is published with verified remote CI; Project 06 is published with verified remote CI. Phase 3 delivery is complete.**

## Project 05 delivery checkpoint

[05 — Agent Failure & Recovery Lab](https://github.com/texasbredmj/agent-failure-recovery-lab) is
published as a public repository. [All seven remote CI jobs passed](https://github.com/texasbredmj/agent-failure-recovery-lab/actions/runs/38503053018)
against commit `404ab9590e16e0f6279cb9d5dff952759c3623bb` on October 13, 2026. Six fixture jobs cover Windows/Linux and
Python 3.11/3.12/3.14. The seventh builds and runs the complete Docker/Toxiproxy/Prometheus/Grafana lab.
Downloaded JUnit evidence confirms 25 passing tests, zero failures/errors/skips, and all ten scenarios:
**eight recovered, one failed safely, one required intervention, zero duplicate side effects**.

Real worker interruption after backend commit recovered with a replacement process and exactly one
mock effect. Duplicate HTTP delivery also retained one effect. Each of ten downloaded SQLite
checkpoints was read and matched against its worker JSON report. HTTP failures, rate limits,
malformed responses, delayed network responses, temporary/permanent outages, and dependency failure
produce classified evidence. Prometheus scraping and the provisioned five-panel Grafana dashboard
were verified through their APIs. Clean local Windows and Linux suites each also passed 25 tests.

[Project 05 evidence](evidence/project05.json) preserves the exact commit, all job conclusions,
artifact checksum, JUnit counts, complete scenario results, checkpoint checks, and observability evidence.
These are controlled local fixtures; unique mock ledger inserts do not prove exactly-once arbitrary
external API effects or production reliability. Raw GitHub artifacts are retained for 14 days.
Project 05 delivery is verified; Project 06 is published with verified remote CI. Phase 3 delivery is complete.

## Project 06 delivery checkpoint

[06 — Multi-Provider Model Gateway](https://github.com/texasbredmj/multi-provider-model-gateway) is
published as a public repository. [All seven remote CI jobs passed](https://github.com/texasbredmj/multi-provider-model-gateway/actions/runs/38520600333)
against commit `22cfd787c8953f42596ce55ebcdb1b95ef9afdf4` on October 14, 2026. Six policy jobs cover Windows/Linux and
Python 3.11/3.12/3.14. The seventh builds the Docker stack and verifies actual Redis, HTTP, streaming,
and gateway restart behavior. Downloaded JUnit confirms **43 passing tests, zero failures/errors/skips**.

Nine real HTTP scenarios confirm text, fixed structured/tool schemas, authorized fallback, timeout
accounting, unsupported capability and budget rejection, successful streaming, and incomplete-stream
handling. A partial stream ends unverified, retains a conservative cost reservation, and does not switch
providers after emitting output. A real gateway container restart preserved the cached response and
left usage unchanged on replay. Local clean Windows and Linux suites each also passed all 43 tests.

Redis coordinates request identity, atomic concurrency/rate limits, cost reservations, and replay-safe
settlement. The two mock providers have incompatible API formats and declared capability/context
limits. Prices/token counters are fixture inputs; **no paid endpoint was called**. This evidence does
not claim live-vendor compatibility or verified invoices. [Project 06 evidence](evidence/project06.json)
preserves the exact commit, job conclusions, artifact checksum, test counts, full HTTP demo, and restart
checks. Raw GitHub artifacts are retained for 14 days.

**Phase 3 delivery is verified. Project 07 is published with verified remote CI.**

## Project 07 delivery checkpoint

[07 — AI-Native CI/CD Quality Gates](https://github.com/texasbredmj/ai-native-cicd-gates) is published
as a public repository. [All seven remote CI jobs passed](https://github.com/texasbredmj/ai-native-cicd-gates/actions/runs/38523537588)
against commit `7de27a44bccf67aa0f9ccfec21411d8dcc396665` on October 14, 2026. Six policy jobs cover
Windows/Linux and Python 3.11/3.12/3.14. The full Linux delivery job's downloaded JUnit confirms
**31 passing tests, zero failures/errors/skips**. The valid candidate passed all twelve gates;
all eleven deliberately broken candidates exited with failure at their intended gates.

A [separate intentional regression proof](https://github.com/texasbredmj/ai-native-cicd-gates/actions/runs/38523557595)
**failed as required**, at the unwrapped required-gate step with exit code 1. Its downloaded report
shows an incorrect value rejected despite a success claim: task completion and evaluation regression
failed while the other ten gates passed. This expected red run verifies actual CI rejection and is
distinct from the successful normal delivery workflow.

The reusable composite action and CLI check tests, strict schemas, dependency snapshots, native and
Gitleaks secret scans, actual Docker build/run, evaluated task outcomes, latency, fixture cost and policy.
Both secret scanners rejected the synthetic token and emitted redacted evidence. Fourteen downloaded
report/trace pairs were checked for matching OpenTelemetry trace IDs and gate states. Actual pip-audit
snapshots cover the tool's 40 pinned dependencies and the candidate's one dependency, with zero findings
at the recorded scan time; reviewed snapshots expire after 30 days.

Clean local Windows checks also passed all 31 tests. A clean Linux wheel installation passed 30
portable tests with the Docker-only test deselected. No live model or paid endpoint was called.
[Project 07 evidence](evidence/project07.json) preserves the exact commit, job conclusions, both artifact
checksums, parsed JUnit, measurements, regression results and expected-failure proof. Raw GitHub
artifacts are retained for 14 days. [Local evidence](evidence/project07-local.json) retains local results.
These are controlled fixtures, not production SLOs, hostile-code containment or external tool/billing
attestation. **Projects 07 and 08 are published with verified remote CI. Phase 4 delivery is complete.**

## Project 08 delivery checkpoint

[08 — Agent Operations Control Center](https://github.com/texasbredmj/agent-operations-control-center)
is published as a public repository. [All seven remote CI jobs passed](https://github.com/texasbredmj/agent-operations-control-center/actions/runs/38527430319)
against commit `2147f79a6c2bc5ca89e0134f137ed5ee5e411f17` on October 14, 2026. Six policy jobs cover
Windows/Linux and Python 3.11/3.12/3.14. Downloaded JUnit from the full-stack job independently confirms
**35 tests passed on the host and 35 against the installed Linux wheel**, each with zero failures,
errors or skips. These are two runs of the same suite, not 70 unique tests.

Its React dashboard, FastAPI API, PostgreSQL worker and persisted OpenTelemetry spans provide all
eleven required operational views and task inspection, approval/rejection, cancellation, eligible
retry and independent verification evidence. Backend role/project authorization protects every
operational endpoint; direct unauthorized requests are rejected independently of the UI.

Downloaded evidence confirms eight real HTTP scenarios and eight Chromium scenarios. Browser checks
exercise all required views and controls, receipt/history/tool/span inspection, viewer restrictions,
desktop/mobile layout and memory-only login, with zero uncaught page errors. Remote desktop and
mobile screenshots were inspected. API and worker restart preserved all eight HTTP-demo records,
history, evidence and spans. Each associated database receipt was checked, with no duplicate effects.
The deliberately incorrect receipt remains failed despite the tool's success claim and cannot retry.

Clean local Windows and Linux installations also each passed all 35 tests. Local Python and npm
audits found no known vulnerabilities at the recorded scan time. No paid model endpoint was called.
[Project 08 evidence](evidence/project08.json) preserves the exact commit, seven job conclusions,
artifact checksum, parsed JUnit, HTTP/browser outcomes, screenshot checksums and restart/receipt results.
[Local evidence](evidence/project08-local.json) retains the local checks. Raw GitHub artifacts are
retained for 14 days. This is an independent fixture runtime, not a live integration with earlier
projects, a production identity system or an external API exactly-once guarantee.

**Phase 4 delivery is verified. All eight portfolio projects are published with confirmed remote CI.**

## Architecture

```text
Goal → input validation → planning → policy and authorization → bounded execution
     → result collection → independent verification → report + audit + metrics
```

The first project establishes deterministic task execution. The second exposes controlled tools
behind an authorized API. Later projects extend durability, evaluation, recovery, model routing,
delivery gates, and operations visibility. Least privilege, retry eligibility, explicit side effects,
resource budgets, and verification evidence remain central across the portfolio.

## Technology and demonstrations

Phase 1 uses Python, Pydantic, Typer, SQLite, Ruff, Pytest, FastAPI, HTTPX, Uvicorn, Docker, and
GitHub Actions. Phase 2 adds Temporal, PostgreSQL, durable workflow recovery, JSONL evaluation, and
OpenTelemetry traces. Local tests use fixtures and mocked upstream APIs; no paid cloud or model service
is required.

After cloning an accessible project, follow its README to create a virtual environment and install
the pinned requirements plus the local package. From the project directory, run:

```text
# Project 01: detect a formatting failure, authorize a correction, verify all subsequent checks
python scripts/demo_maintenance.py

# Project 02: discover tools, block an unapproved write, approve it, verify one ticket creation
python scripts/demo.py

# Project 02: start a real localhost API with ephemeral credentials, verify authorization, stop it
python scripts/smoke_server.py
```

Project READMEs also document isolated Docker demos, failure handling, API/CLI usage, and known
limitations. Local execution does not imply hostile-code containment or public-service readiness.

## Development roadmap

| Phase | Projects | Status |
| --- | --- | --- |
| 1 — Foundations | 01 Task Execution Engine; 02 AI Tool Coordination Gateway | Published; remote CI verified on Windows/Linux, Python 3.11/3.12/3.14, plus Docker |
| 2 — Orchestration and evaluation | 03 Autonomous Workflow Orchestrator; 04 Agent Evaluation Harness | Both published; remote CI, durability recovery, and evaluation regression evidence verified |
| 3 — Reliability and model routing | 05 Agent Failure & Recovery Lab; 06 Multi-Provider Model Gateway | Both published; remote CI, fault recovery, model routing, Redis budgets, and streaming evidence verified |
| 4 — Delivery and operations | 07 AI-Native CI/CD Quality Gates; 08 Agent Operations Control Center | Both published; required remote CI, regression rejection, authorized dashboard controls and PostgreSQL/Chromium evidence verified |

Planned projects are not advertised as completed repositories. Benchmark numbers, cloud deployment,
production usage, and remote CI success are reported only when supported by confirmed evidence.
