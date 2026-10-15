[Start Here — GitHub employer demo](https://github.com/texasbredmj/ai-engineering-portfolio#start-here)

# Agent Evaluation Harness

Project 04 of AI Systems Engineering Lab evaluates whether an agent selects the right tool,
uses correct arguments, respects authorization, recovers within a retry budget, and produces
an independently verified outcome. A candidate's assertion is compared with mock backend receipts
and a versioned acceptance oracle. No language model judge decides the required gates.

## Install and run

Requires Python 3.11 or later. From this repository:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.lock .
.venv/Scripts/agent-eval.exe run --suite benchmarks/baseline-v1.jsonl --output .evaluation/baseline-v1 --version baseline-v1
.venv/Scripts/python.exe scripts/demo.py
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m ruff format --check .
```

On Linux/macOS use `.venv/bin/python` and `.venv/bin/agent-eval`. No credentials or external
services are needed. Output directories must be new: reports are preserved across candidate versions.
The demo creates a unique directory each time and verifies that the baseline passes while four
deliberately faulty candidates fail. It writes comparisons, reports, per-case JSONL, and traces.

```text
agent-eval run --suite benchmarks/baseline-v1.jsonl --output .evaluation/regression-v2 --candidate no-recovery --version regression-v2
agent-eval compare .evaluation/baseline-v1/report.json .evaluation/regression-v2/report.json
```

Exit codes: **0** gate passed, **1** evaluation/regression gate failed, **2** invalid input.
The regression commands above should return 1. The aggregate gate requires every applicable
per-case check to pass; there is no averaging away a policy or correctness failure.

## Architecture and scoring

```text
JSONL cases → strict validation → candidate decisions → policy-controlled mock tools
           → receipts + backend effects → independent oracle → ten checks
           → versioned report + JSONL + OpenTelemetry traces → regression comparison
```

The baseline planner receives only task input; it cannot see expected outcomes. Each case gets
a fresh inventory backend. Three typed tools perform integer sums, read inventory, or reserve
inventory in memory. External text is data and cannot request executable code or a network call.

| Dimension | Required criterion |
| --- | --- |
| Task completion accuracy | Status, value, and side-effect count match the acceptance oracle |
| Tool selection | Exact expected tool identifier |
| Argument correctness | Exact expected typed arguments |
| Authorization | No unauthorized attempts except an explicitly expected, safely rejected policy probe |
| Recovery | Expected outcome achieved on fault cases within at most three attempts |
| Latency | Measured mock execution plus recorded model latency within the case budget |
| Tokens | Input plus output tokens within the case budget |
| Cost | Tokens × configured per-million prices within the case budget |
| Failure rate | No unexpected execution outcome; observed failures are separately counted |
| Verification accuracy | Candidate verification claim agrees with independently verified acceptance |

Scores are pass fractions, with explicit denominators. Recovery includes only fault cases;
if a custom suite has none, its recovery metric is null. Two baseline cases intentionally probe
denied actions: their attempts are counted even though safe rejection passes the expected criterion.
`verified` means acceptance criteria were satisfied; a correct rejection or expected failure can
be verified without a successful business action. Inspect `status` separately.

All gate thresholds live in the hashed case data. Comparisons require matching suite hash,
schema, prices, and case IDs, and reject contradictory summary scores. Each report includes
candidate version, harness version, decision hash, run ID, UTC timestamp, resource totals,
per-case receipts, and correlated trace IDs. Wall-clock latency and trace IDs naturally vary;
logical outcomes and decision hashes are repeatable. P95 uses the nearest-rank method.

## Optional model-based evaluation

Record a model's structured decisions outside this harness, then evaluate them with the same
mock tools and deterministic oracle. This provides an offline model integration boundary without
depending on paid endpoints or judge availability. See [the input contract](examples/recorded-decisions.md).

```text
agent-eval run --suite benchmarks/baseline-v1.jsonl --predictions my-decisions.jsonl --input-price 2 --output-price 4 --output .evaluation/model-v1 --version model-v1
```

Every case ID must occur exactly once. Explicit input tokens, output tokens, and model latency
are required; missing usage cannot silently become zero. Prices are USD per million tokens.
Recorded measurements are supplied by the caller and cannot independently prove provider billing.
The harness measures its own execution latency. The deterministic baseline uses no model and costs $0
in model usage; that does not include computer or CI infrastructure costs.

## Containers and CI

```text
docker build -t agent-evaluation-harness .
docker run --rm --network none agent-evaluation-harness
```

The image installs a regular wheel and runs as a non-root user. It prints the gate summary;
ephemeral reports disappear when the container is removed. Mount a writable output directory if
you want to retain reports. Local tests require no Docker server.

GitHub Actions is configured for Windows/Linux × Python 3.11/3.12/3.14, plus a clean Docker
build and offline baseline run. Each matrix job tests resource budgets and regression rejection,
runs the demo, and uploads JUnit, reports, and local traces for 14 days. [The implementation CI passed all seven jobs](https://github.com/texasbredmj/agent-evaluation-harness/actions/runs/38491693842).
See the [portfolio evidence](https://github.com/texasbredmj/ai-engineering-portfolio) for current delivery results.

## Evidence and limits

See [verification results](docs/verification.md), [architecture](docs/architecture.md), and
[threat model](docs/threat-model.md). These fixtures evaluate small typed decisions and bounded
mock executions, not arbitrary long-running agents or production workloads. There is no live
provider adapter, shell execution, real side effect, network exporter, or LLM judge. Replay of
recorded model decisions tests their tool choices, not real provider reproducibility. Model latency
is recorded, not timed by this harness. Mock retries are immediate and injected before side effects;
they do not establish durable recovery after process termination. Fixture changes require a new
benchmark baseline. Local file access is not hostile-code containment.

The project demonstrates evaluation design, regression gates, independent evidence, resource
accounting, strict contracts, OpenTelemetry instrumentation, and reproducible Python packaging.
Future work can add authorized provider-specific recording adapters and reviewed domain suites.
