# Run the employer demo in Codespaces

[Open in GitHub Codespaces](https://github.com/codespaces/new?repo=texasbredmj/ai-engineering-portfolio&ref=showcase%2Fcodespaces-verification)

This launch link selects the verification branch and its **Portfolio guided demo** development container. GitHub sign-in is required; creation and image builds take additional time beyond the five-minute walkthrough. Codespaces usage is charged to the account shown on GitHub's creation screen, subject to its included allowance.

**Verified October 14, 2026:** fresh unattended startup, both lifecycle hooks, the 35-test suite on host and installed wheel, eight HTTP scenarios, eight Chromium scenarios, restart preservation, and authenticated private forwarded-URL task/receipt/trace inspection passed at portfolio commit `90ae4dc4c640e4ea337c4612bf5f0ca3fb67bfd2`. [Raw reports and hashes](../evidence/codespaces-operational/manifest.json).

## Fresh startup

1. Use the link above and create a fresh 2-core Codespace.
2. Let post-create setup finish. It clones Project 08 at commit `2147f79a6c2bc5ca89e0134f137ed5ee5e411f17`, installs its locked Python dependencies, generates distinct local credentials, builds the frontend/API image, starts PostgreSQL and the worker, and seeds eight HTTP scenarios.
3. In **Ports**, open **18780** in a browser. Keep visibility **Private**. Do not forward database port 15438. The development-container configuration suppresses its automatic forwarding.
4. Open `.demo/agent-operations-control-center/.env` privately in the Codespaces editor and copy the token for the role being used. Do not put credentials in chat, screenshots, evidence or commits. Reloading the dashboard clears its memory-only session.

Expected startup summary: `verified_demo=true`, `scenarios=8`, `paid_model_calls=0`. The dashboard URL is unique to each Codespace; use its Ports entry rather than a hard-coded example URL.

Setup can be rerun with `python scripts/setup_codespaces.py`. It reuses existing credentials and skips seeding when the HTTP report exists. Starting the Codespace again invokes the start-only path. Setup and verification share an exclusive file lock, so they cannot create the same Compose services concurrently. The editor waits for post-create setup. Application startup initializes the current idempotent schema; the pinned fixture has no versioned migration runner.

## Five guided exercises

| Action | Expected result |
| --- | --- |
| As operator create an Inventory reservation with quantity 2; inspect Evidence | SUCCEEDED, verified=true, observed_quantity=2 |
| Create a Reservation requiring approval; sign out and act as approver | PENDING_APPROVAL before the decision; approval produces verified SUCCEEDED; rejection of a separate task produces REJECTED with no effect; operator/viewer approval is denied |
| Create Temporary failure; inspect FAILED, then Retry with a reason | SUCCEEDED on attempt 2; viewer retries and ineligible retries are denied |
| Create Receipt mismatch with quantity 2; compare Tools and Evidence | Tool claims completion, independent quantity check fails, task stays FAILED and cannot retry |
| Inspect Workflow, Tools, Traces and operational views | Persisted history/spans, matching task trace IDs, visible reliability/resource metrics, zero model tokens/cost |

## Reproduce verification

From the portfolio root:

```sh
python scripts/verify_codespaces.py
```

The runner starts the real services, requires all 35 PostgreSQL-backed tests to pass with no failures/errors/skips, runs eight HTTP scenarios, verifies API/worker restart preserves records and receipts with zero duplicate effects, and runs eight Chromium scenarios including desktop/mobile views. A nonzero exit is a failure. Read `.demo/verification.json` and the application `.gates/` reports locally. The runner leaves forwarded-browser verification false because a passing loopback browser test does not verify GitHub's authenticated forwarding route.

Separately open the private forwarded URL, log in, and verify a task/receipt there before recording that route as passed. Preserve reviewed redacted JSON/XML and artifact hashes; never copy `.env` or raw unreviewed logs into evidence.

## Network decision and boundaries

### Automatic startup verified after storage fix

Fresh universal-image launches failed when PostgreSQL exited with code 1. The latest attempt at source `334d5db52c9244a9ebfedf58888cd8a3a6d6f0d4` also reported `No space left on device` while retaining database diagnostics. Its recovery container had 29 GB free in the workspace; that does not measure the original failed development container. Failure records remain separate from the passing clean-volume runtime evidence.

The launcher uses the official small Ubuntu 24.04 development base, installs Python 3.12 from Ubuntu packages, and adds the official Docker-in-Docker feature pinned to 4.1.3. This avoids the universal image's storage footprint and the first Python image's inherited Yarn signing-key failure. A fresh 2-core, 8 GB RAM, 32 GB Codespace passed unattended startup at commit `90ae4dc4c640e4ea337c4612bf5f0ca3fb67bfd2`. The create hook started at 19:13:37 UTC, recorded the application ready at 19:15:08 UTC, and the start hook completed before configuration finished at 19:15:13 UTC. Both hooks succeeded before any manual setup command. The full verification runner and private forwarded-browser check then passed. The final manifest records available storage and versions. The base tag can change; evidence applies to the observed commit and environment.

Setup writes ignored `.demo/startup-create.json` only after services and the seeded HTTP demo succeed. Restart writes `.demo/startup-start.json`. These reports contain versions, commits and available workspace storage, with no credentials. They complement the creation log; they do not replace the full verification runner or private forwarded-browser check.

If startup fails, inspect `.demo/postgres-startup.log` privately. From the application directory, use `docker compose ps -a`, `docker compose logs --no-color --tail 100 postgres`, `docker info --format '{{.DockerRootDir}}'`, and `df -h`. Do not print `.env`, publish resolved Compose configuration, or remove database volumes. Preserve the actual error before changing configuration. Diagnostic-only lifecycle pauses in the earlier test Codespace have been restored; the paused configuration is not shipped.

To repeat verification in a new environment, run `python scripts/verify_codespaces.py` from the portfolio root and verify a task/receipt at its private forwarded URL before recording that environment as verified.

An early verification command in this session overlapped post-create setup and caused a container-name conflict. The final workflow waits for post-create setup and serializes setup/verification with a Linux file lock. This failed attempt is separate from the recorded application passes.

The first fresh Codespace resolved `postgres` correctly but timed out on container-to-container TCP. PostgreSQL remained healthy and all 35 tests passed through its published localhost port. The Codespaces Compose override makes the API and worker share PostgreSQL's network namespace and use `127.0.0.1:5432`. PostgreSQL publishes the API at `127.0.0.1:18780`; database port 15438 also remains bound to localhost. This changes networking only; application code and authorization checks remain pinned to the reviewed commit. Trusted fixture services share a network namespace, which is a deployment tradeoff, not a production isolation claim.

The original Project 08 `test_container.py` hard-codes the bridge network and is incompatible with this workaround. The portfolio runner uses `verify_codespaces_wheel.py` to run the same installed-wheel suite in the working PostgreSQL namespace. Report the host and wheel as two runs of the same 35 tests, not 70 unique tests.

To stop the app while preserving its database:

```sh
cd .demo/agent-operations-control-center
docker compose down
```

Then stop the Codespace from GitHub's Codespaces page. A full rebuild may clear nested Docker volumes. Do not delete an environment containing work you need to retain.

GitHub Pages serves the static showcase at https://texasbredmj.github.io/ai-engineering-portfolio/; Codespaces runs the application. Static role tokens, deterministic database effects, and zero live model calls remain explicit limitations. Resume attribution review and the portfolio evidence-workflow gate remain separate work.
