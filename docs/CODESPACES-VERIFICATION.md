# Run the employer demo in Codespaces

[Open in GitHub Codespaces](https://github.com/codespaces/new?repo=texasbredmj/ai-engineering-portfolio&ref=showcase%2Fcodespaces-verification)

This launch link selects the verification branch and its **Portfolio guided demo** development container. GitHub sign-in is required; creation and image builds take additional time beyond the five-minute walkthrough. Codespaces usage is charged to the account shown on GitHub's creation screen, subject to its included allowance.

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

### Unresolved automatic startup check

The unattended launch of source `32848fad247a14d3de02ec0c82591dc02fca4f83` failed when `lab-ops08-postgres-1` exited with code 1. This is a recorded execution failure, not a configuration-only check. See [the failure record](../evidence/codespaces-final/unattended-startup-failed.json). The separately recorded clean-volume runtime tests passed; automatic startup remains unverified.

The test Codespace `fictional-space-guacamole-xq9v76qqx7g2p6gr` had a diagnostic rebuild requested with its lifecycle commands temporarily paused. The browser did not reconnect to a terminal during the observed rebuild, and the test Codespace was stopped with its files preserved. Its original configuration is preserved in ignored `.demo/devcontainer-original.json`. Once its terminal reconnects, restore that test-only change and obtain the diagnostic capture fix:

```sh
cp .demo/devcontainer-original.json .devcontainer/devcontainer.json
git pull --ff-only
python scripts/setup_codespaces.py
```

If startup fails, inspect `.demo/postgres-startup.log` privately. For additional diagnosis, run these commands from `.demo/agent-operations-control-center`:

```sh
docker compose ps -a
docker compose logs --no-color --tail 100 postgres
docker info --format '{{.DockerRootDir}}'
df -h
```

Do not print `.env`, run `docker compose config` into shared evidence, or remove database volumes. Preserve the actual database error before changing configuration. After fixing the observed cause, rerun `python scripts/verify_codespaces.py` from the portfolio root, then launch another fresh Codespace from the fixed commit without intervening in setup. Record successful post-create completion, the full runner result, and a private forwarded-URL task/receipt check before marking automatic startup verified.

The initial slim development image could not install its Docker feature because its bundled Yarn repository signing key was unavailable. The launcher now uses the maintained standard Codespaces universal image and its `codespace` user. Its initial image download takes additional time. This image tag can change; the application itself is pinned, and recorded verification applies to the observed environment.

An early verification command in this session overlapped post-create setup and caused a container-name conflict. The final workflow waits for post-create setup and serializes setup/verification with a Linux file lock. This failed attempt is separate from the recorded application passes.

The first fresh Codespace resolved `postgres` correctly but timed out on container-to-container TCP. PostgreSQL remained healthy and all 35 tests passed through its published localhost port. The Codespaces Compose override makes the API and worker share PostgreSQL's network namespace and use `127.0.0.1:5432`. PostgreSQL publishes the API at `127.0.0.1:18780`; database port 15438 also remains bound to localhost. This changes networking only; application code and authorization checks remain pinned to the reviewed commit. Trusted fixture services share a network namespace, which is a deployment tradeoff, not a production isolation claim.

The original Project 08 `test_container.py` hard-codes the bridge network and is incompatible with this workaround. The portfolio runner uses `verify_codespaces_wheel.py` to run the same installed-wheel suite in the working PostgreSQL namespace. Report the host and wheel as two runs of the same 35 tests, not 70 unique tests.

To stop the app while preserving its database:

```sh
cd .demo/agent-operations-control-center
docker compose down
```

Then stop the Codespace from GitHub's Codespaces page. A full rebuild may clear nested Docker volumes. Do not delete an environment containing work you need to retain.

GitHub Pages serves the static showcase; Codespaces runs this application. Static role tokens, deterministic database effects, and zero live model calls remain explicit limitations. Pages publication, resume attribution review, and the portfolio evidence-workflow gate are separate work.
