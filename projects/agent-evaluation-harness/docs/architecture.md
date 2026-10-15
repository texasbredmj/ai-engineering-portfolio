# Architecture and decisions

The runner separates input validation, candidate decisions, backend policy, and evaluation.
Candidates receive `Task` only. Cases define expected tool, arguments, status, value, permissions,
approval, fault injection, and budgets. A JSONL file contains at most 1000 records and 2 MiB.
Pydantic rejects extra fields, coercions, malformed arguments, and nonfinite measurements.
The mock backend validates tool arguments independently and enforces permission/approval before
attempting execution. It never interprets tool names as Python imports or commands.

Mock transient failures occur before effects, and only transient statuses retry. Permanent failures,
rejections, and invalid arguments stop immediately. Attempt count is capped at three. A fresh backend
per case prevents cross-case contamination. Independent verification checks expected status/value
and effect count; it does not accept a candidate's verification claim as evidence.

Report comparison detects per-case regressions, including ones that aggregate averages would hide.
It requires identical benchmark data and prices, recomputes scores, and checks case sets. This
detects inconsistent reports but does not cryptographically authenticate them. Store trusted reports
and their CI artifact metadata in version control for review.

OpenTelemetry uses a per-run `TracerProvider`, synchronous `SimpleSpanProcessor`, and a custom
local JSONL `SpanExporter`. Each case is a root span and each attempt is its child. Provider shutdown
flushes/closes the exporter. There is no global provider mutation or external collector requirement.
Only case ID, tool name, pass/fail, and attempt count are attributes. Prompts, arguments, and
credentials are excluded. JSON reports supply benchmark metrics; spans provide execution correlation.
This uses the [official Python instrumentation API](https://opentelemetry.io/docs/languages/python/instrumentation/)
and [SDK exporter interface](https://opentelemetry-python.readthedocs.io/en/stable/sdk/trace.export.html).

The package is independently installable and has no runtime dependency on Projects 01–03.
Python 3.11+ permits consistent typed contracts on Windows/Linux. Pydantic enforces schemas;
OpenTelemetry serves trace interoperability; pytest and Ruff provide required checks. No database,
web UI, collector, or scheduler is needed for this bounded batch evaluation problem.
