# AI Systems Engineering Lab

## Start Here

**One GitHub entry point for the working employer demonstration and all eight projects.**

[Launch the employer demo in GitHub Codespaces](https://codespaces.new/texasbredmj/ai-engineering-portfolio?quickstart=1)

1. Launch a new Codespace using the button above. First setup builds the service images and can take several minutes. Check your GitHub Codespaces allowance before creating it.
2. Wait for the terminal to say **Ready**. The startup process generates credentials and starts the complete platform automatically.
3. Open `.platform/DEMO-ACCESS.md` in the editor for your generated operator, approver and viewer tokens. This file is private to your Codespace and must never be committed.
4. Open **port 18780** in the Ports panel. Keep its visibility **Private**. Append `/showcase/` to its URL for the portfolio walkthrough; the dashboard is at `/`.
5. Follow the five actions: create and independently verify; approve/reject; retry; investigate a mismatch; inspect history and traces. Sign out to change roles.
6. Stop your Codespace when finished.

There are no Windows or Linux download links. The GitHub Codespace is the supported employer launch path.

## What runs

Project 08's dashboard dispatches actual Project 03 Temporal workflows. They call Project 02's tool gateway for inspection and an approved inventory reservation, and Project 06's model gateway using local mock provider APIs. Independent PostgreSQL ledger verification decides completion. Failed verification triggers compensation; no paid model endpoint is called.

Projects 01, 04, 05 and 07 provide maintenance execution, evaluation, failure recovery and release checks. Every project's source and demonstration are bundled here, including the employer snapshot of Project 01. No separate repository access is required.

| Project | Role | Try it in the Codespace terminal |
| --- | --- | --- |
| [01 Task Execution Engine](projects/task-execution-engine) | Repository maintenance with verified correction | `python scripts/project_demo.py 1` |
| [02 Tool Coordination Gateway](projects/ai-tool-coordination-gateway) | Typed, authorized tools and independent verification | `python scripts/project_demo.py 2` |
| [03 Workflow Orchestrator](projects/autonomous-workflow-orchestrator) | Durable workflows, approvals, recovery and compensation | `python scripts/project_demo.py 3` |
| [04 Evaluation Harness](projects/agent-evaluation-harness) | Baseline evaluation and rejection of faulty candidates | `python scripts/project_demo.py 4` |
| [05 Failure & Recovery Lab](projects/agent-failure-recovery-lab) | Controlled faults and receipt-based recovery | `python scripts/project_demo.py 5` |
| [06 Model Gateway](projects/multi-provider-model-gateway) | Local model routing, budgets, streaming and replay | `python scripts/project_demo.py 6` |
| [07 CI/CD Quality Gates](projects/ai-native-cicd-gates) | Valid release and deliberately rejected regressions | `python scripts/project_demo.py 7` |
| [08 Operations Dashboard](projects/agent-operations-control-center) | Real integrated employer walkthrough | `python scripts/project_demo.py 8` |

To run every demonstration, use `python scripts/project_demo.py all`. These checks may build additional isolated test services. Their redacted summaries appear in the dashboard's **Project evidence** view.

## Evidence and architecture

[Integrated architecture](docs/INTEGRATED-ARCHITECTURE.md) · [Employer instructions](docs/EMPLOYER-TEST.md) · [Delivery checks](https://github.com/texasbredmj/ai-engineering-portfolio/actions/workflows/integrated-platform.yml) · [Original source commits](projects/source-manifest.json) · [Preserved project CI evidence](evidence/)

Verified in a fresh GitHub Codespace and clean GitHub Actions environments: all eight demonstrations, 202 portable component tests, four integration adapter/accounting tests, 36 PostgreSQL backend tests, eight HTTP scenarios and nine Chromium scenarios passed. Crash recovery preserved work with zero duplicate reservations. See [integration results](evidence/integration.json) and [fresh Codespace evidence](evidence/codespaces-integration.json).

This is a deterministic engineering fixture with generated role tokens and local providers. Production managed identity, hostile-code isolation and general external API exactly-once guarantees are outside its scope.
