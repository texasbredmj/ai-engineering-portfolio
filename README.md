# AI Systems Engineering Lab

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
| [01 â€” Task Execution Engine](https://github.com/texasbredmj/task-execution-engine) | Private; access required | CLI, strict requests, SQLite lifecycle/audit, bounded fixed commands, idempotency, approved formatting corrections, patch capture, independent verification | Published; [7/7 CI jobs passed](https://github.com/texasbredmj/task-execution-engine/actions/runs/38367464942) |
| [02 â€” AI Tool Coordination Gateway](https://github.com/texasbredmj/ai-tool-coordination-gateway) | Public | Typed registry/discovery, four adapters, backend permissions, separate approval, concurrency/rate budgets, durable no-replay claims, independent receipt verification | Published; [7/7 CI jobs passed](https://github.com/texasbredmj/ai-tool-coordination-gateway/actions/runs/38367470323) |

[Machine-readable checkpoint evidence](evidence/phase1.json) records the exact published commits,
workflow run URLs, all fourteen successful job conclusions, twelve evidence artifacts, and sampled remote JUnit results.

## Architecture

```text
Goal â†’ input validation â†’ planning â†’ policy and authorization â†’ bounded execution
     â†’ result collection â†’ independent verification â†’ report + audit + metrics
```

The first project establishes deterministic task execution. The second exposes controlled tools
behind an authorized API. Later projects extend durability, evaluation, recovery, model routing,
delivery gates, and operations visibility. Least privilege, retry eligibility, explicit side effects,
resource budgets, and verification evidence remain central across the portfolio.

## Technology and demonstrations

Phase 1 uses Python, Pydantic, Typer, SQLite, Ruff, Pytest, FastAPI, HTTPX, Uvicorn, Docker, and
GitHub Actions. Local tests use fixtures and mocked upstream APIs; no paid cloud or model service
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
| 1 â€” Foundations | 01 Task Execution Engine; 02 AI Tool Coordination Gateway | Published; remote CI verified on Windows/Linux, Python 3.11/3.12/3.14, plus Docker |
| 2 â€” Orchestration and evaluation | 03 Autonomous Workflow Orchestrator; 04 Agent Evaluation Harness | Planned; Phase 1 checkpoint passed, Project 03 may begin next |
| 3 â€” Reliability and model routing | 05 Agent Failure & Recovery Lab; 06 Multi-Provider Model Gateway | Planned |
| 4 â€” Delivery and operations | 07 AI-Native CI/CD Quality Gates; 08 Agent Operations Control Center | Planned |

Planned projects are not advertised as completed repositories. Benchmark numbers, cloud deployment,
production usage, and remote CI success are reported only when supported by confirmed evidence.
