# Guided hands-on demo

Use Agent Operations Control Center to create real fixture tasks and inspect their database receipts. Allow five minutes for the walkthrough after setup; installation and image builds take additional time.

## Start the application

**Primary path: [Open in GitHub Codespaces](https://github.com/codespaces/new?repo=texasbredmj/ai-engineering-portfolio&ref=showcase%2Fcodespaces-verification).** Follow [Codespaces startup and verification](CODESPACES-VERIFICATION.md). Fresh unattended startup and both lifecycle hooks passed on October 14, 2026 at portfolio commit `90ae4dc4c640e4ea337c4612bf5f0ca3fb67bfd2`. The 35-test suite passed on the host and installed wheel, along with eight HTTP scenarios, eight Chromium scenarios, restart preservation with zero duplicate effects, and authenticated task/receipt/trace inspection through the private forwarded URL. [Raw reports and hashes](../evidence/codespaces-operational/manifest.json).

The following commands are the original local startup alternative; the Codespaces setup applies its network override automatically.

Requirements: Git, Python 3.11 or newer, and a running Docker engine with Docker Compose. Use a fresh clone. The commands below use Linux or macOS paths; on Windows replace .venv/bin/python with .venv/Scripts/python. An existing checkout with .env should reuse its generated credentials rather than rerun initialization.

```sh
git clone https://github.com/texasbredmj/agent-operations-control-center.git
cd agent-operations-control-center
git checkout 2147f79a6c2bc5ca89e0134f137ed5ee5e411f17
python -m venv .venv
.venv/bin/python -m pip install -r requirements.lock .
.venv/bin/python scripts/init_local.py
docker compose up -d --build --wait
.venv/bin/python scripts/demo.py
```

Expected: the HTTP demo prints verified_demo=true, scenarios=8 and paid_model_calls=0. Its redacted results are in .gates/http-demo.json. It leaves a pending approval. Rerunning appends scenarios and does not reset the database; the fixture has a 1,000-task limit.

Open http://127.0.0.1:18780. Read the ignored .env file in your editor and copy the generated operator, approver or viewer token as needed. Initialization generates distinct tokens and does not print them. Never paste .env into evidence, screenshots or commits. Login is held only in tab memory; reload or Sign out clears it.

## Five-minute walkthrough

### 1 Create a task and inspect its receipt

About 60 seconds. Sign in as operator. Choose + New task, give it the title Employer normal reservation, choose Inventory reservation, and set Units to reserve to 2. Submit and select the task under Completed tasks when it finishes. In Evidence, inspect the independent verification details and observed quantity.

Expected: SUCCEEDED with verified=true and observed_quantity=2. The tool success claim alone is not the pass condition. Skill: execution and independent verification.

### 2 Approve or reject a pending action

About 75 seconds. As operator create Employer controlled reservation with workflow Reservation requiring approval and quantity 2. Record the task ID. It should remain PENDING_APPROVAL. Sign out, sign in as approver, and find that ID under Pending approvals. Approve it with a reason such as Reviewed the requested two-unit allocation and confirm. To try rejection, create a separate approval task and reject it as approver.

Expected: an approved task reaches SUCCEEDED with a verified receipt; a rejected task reaches REJECTED without an effect. Operator and viewer cannot approve. The setup HTTP demo also checks direct unauthorized approval requests return 403. Skill: backend authorization and human oversight.

### 3 Retry a temporary failure

About 60 seconds. Sign in as operator and create Employer temporary failure using Temporary failure → eligible retry. After it reaches FAILED, inspect it, choose Retry, supply a reason and confirm.

Expected: SUCCEEDED on attempt 2 with a verified receipt. Retry eligibility and attempt limits are enforced by the backend. A permanent failure is not retryable. Skill: recovery and bounded retries.

### 4 Investigate a receipt mismatch

About 60 seconds. Create Employer receipt mismatch using Receipt mismatch → investigation and quantity 2. Open the failed task and compare Tools with Evidence.

Expected: the tool claims completion, but independent verification is false because observed quantity differs. State remains FAILED and retry is ineligible. Do not interpret the claim as success. Skill: evaluation and false-success detection.

### 5 Inspect history, traces and metrics

About 45 seconds. Open one of your tasks and compare Workflow, Tools and Traces. Inspect Execution traces and Reliability metrics, then Resource usage and Cost reports.

Expected: task history, tool activity and spans are inspectable with a matching task trace ID. Metrics describe this fixture's lifetime activity. Token and model cost counters are zero because there are no paid model calls. Shared worker CPU/memory are infrastructure counters. Skill: observability and operations.

## Verification and troubleshooting

The UI refreshes every 2.5 seconds. If state does not change, inspect docker compose ps and docker compose logs --tail 80 api worker locally. Review logs for sensitive material before sharing them. Refresh stale task details before retrying a control action; stale versions return 409. A login error requires the correct environment-generated token and running API.

For independent checks run:

```sh
.venv/bin/python scripts/test_local.py -q --junitxml=.gates/tests-host.xml
.venv/bin/python scripts/verify_restart.py
docker compose --profile verification run --build --rm browser
docker compose down
```

Expected backend suite: 35 tests. The restart check follows the seeded HTTP demo. Stopping preserves the named database volume. The browser runner is a verification service, not the deployed frontend.

## Evidence and boundaries

[Recorded remote CI](https://github.com/texasbredmj/agent-operations-control-center/actions/runs/38527430319) and [preserved evidence](../evidence/project08.json) describe commit 2147f79a6c2bc5ca89e0134f137ed5ee5e411f17. They report two runs of the same 35-test suite, eight HTTP scenarios, eight Chromium scenarios and restart checks. This follow-up independently reran the application checks in a fresh Codespace. [Forwarded browser evidence](../evidence/codespaces-forwarded-ui.json) records authenticated creation, receipt inspection, mismatch investigation and traces through the private HTTPS URL.

This is a deterministic PostgreSQL ledger fixture, independently runnable from Projects 01–07. It does not call a live model, implement production identity or guarantee exactly-once effects against arbitrary external APIs. [Fresh application evidence](../evidence/codespaces-app-2026-10-14.json) and the [raw reports](https://github.com/texasbredmj/agent-operations-control-center/tree/verification/codespaces-2026-10-14/docs/evidence/codespaces-2026-10-14) are separate from the earlier recorded CI. The launch link selects the verification branch, not main.
