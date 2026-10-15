# Employer walkthrough

Start at [the GitHub portfolio](https://github.com/texasbredmj/ai-engineering-portfolio#start-here) and launch a new Codespace. Wait for **Ready**. Open `.platform/DEMO-ACCESS.md` in its editor, then use private forwarded port 18780. The showcase is `/showcase/`; the working dashboard is `/`.

## Five actions

1. **Create and verify:** sign in as operator. Create an Inventory reservation with quantity 2. Select it under Completed tasks and inspect Evidence. Expect a verified receipt, matching observed quantity and a real `ops-...` workflow ID. Under Tools inspect the file gateway, model gateway and inventory gateway reports.
2. **Approve or reject:** create Reservation requiring approval as operator. It remains PENDING_APPROVAL. Sign out and sign in as approver. Approve with a reason; expect verified completion. Create a second task to try rejection; expect REJECTED without a reservation.
3. **Retry:** as operator create Temporary failure. Wait for FAILED, inspect and retry with a reason. Expect success on dashboard attempt 2. The prior Temporal execution failed before reservation; the explicit retry runs a new bounded attempt.
4. **Investigate mismatch:** create Receipt mismatch with quantity 2. The deliberately corrupted fixture ledger stores 3; independent verification fails and the orchestrator compensates it. Expect FAILED, observed_quantity=3 and no retry control. Compare Tools with Evidence; a tool execution claim is not verified completion.
5. **Inspect operations:** as viewer inspect Workflow, Tools, Traces, Reliability metrics, Resource usage, Cost reports and Project evidence. Viewer cannot create, approve or retry. Model provider traffic is local; paid model calls are zero. Model gateway reports retain hypothetical token and cost accounting.

## Independent demonstrations

In the Codespace terminal run `python scripts/project_demo.py all`, or choose a project number 1–8. These are real demonstrations, not recorded videos. Reports appear in Project evidence after completion. The workflow history and verification for interactive tasks are available immediately.

## Troubleshooting

Startup and database state survive a Codespace stop/start. To retry startup, run `python scripts/start_platform.py`. To inspect services use `docker compose ps` and review `docker compose logs --tail 60` locally. Do not share credentials or unreviewed logs. To stop application containers while preserving data use `docker compose down`.

If a setup step fails, do not mark the walkthrough complete. Inspect the terminal error and compare the GitHub integration checks. Keep port 18780 private. Codespaces requires your own GitHub account and available allowance; this is not an anonymous shared public backend.
