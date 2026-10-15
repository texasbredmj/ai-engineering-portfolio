# Local verification — October 13, 2026

Project 05 is locally implemented. Both full Windows and Linux suites passed **25 tests, zero failures/errors/skips**. [Publication CI passed all seven jobs](https://github.com/texasbredmj/agent-failure-recovery-lab/actions/runs/38501915496) at implementation commit `614f137e31cdffe31cfb557b4c9e29024c8a787d`.
Results are captured in [machine-readable evidence](evidence/verification-summary.json).

The full suite exercises ten real subprocess/HTTP scenarios with the Docker backend, Toxiproxy,
Prometheus, and Grafana. Controlled outcomes are eight recoveries, one safe dependency failure, and
one human-required permanent outage, with no duplicate side effects. The worker interruption is a
real process kill after the backend receipt commits, followed by a replacement worker using the
same durable task/checkpoint. Recovery consumes a second attempt and retains exactly one receipt.

Windows uses Python 3.14.6; Linux uses Python 3.12 with a clean installed wheel in Docker. The fixture
subset can run without Docker; its count excludes the stack test. Full verification requires
`LAB_STACK=1`, and a skipped stack test is not evidence of network-fault coverage. Exact parsed
JUnit counts and the captured scenario reports are preserved in the evidence file.

Executed commands include pinned installation, Ruff lint/format, `pip check`, installed CLI help,
`docker compose up -d --build`, full pytest, `recovery-lab run`, and the observability verifier.
Prometheus was queried for actual scraped scenario data. Grafana's API returned the provisioned
dashboard with all five panels. Windows and Linux scenario reports agree on outcomes and duplicate
counts; timings and task IDs naturally differ.

Initial checks exposed a misplaced test assertion, sandbox/shared-temp permission conflicts, and
Toxiproxy's canonical wildcard listener address. These were corrected before final verification.
Workspace-local fresh pytest temporary directories and disabled cache writes were used for the
Windows execution account. Failed preliminary commands are not counted as passing checks.

Retry effectiveness is the fraction of multi-attempt scenarios ending recovered, including intentional
exhaustion cases in the denominator. Recovery success rate uses the eight scenarios expected to
recover. Scenario duration includes controller and process startup; worker CPU measures only the
execution section of the final worker process. Database bytes exclude WAL and logs. These are local
fixture measurements, not production performance or reliability claims.

CI is configured for six OS/Python fixture jobs and one full-stack job. The downloaded implementation artifact independently confirmed 25 passing tests, all ten expected
scenario outcomes, zero duplicate effects, Prometheus scraping, and the provisioned Grafana dashboard.
The [portfolio index](https://github.com/texasbredmj/ai-engineering-portfolio) records the latest delivery
commit and artifact checks. The run above is a historical snapshot for the implementation commit.

A later remote documentation-commit run exposed timing sensitivity: the original 120ms deadline
was also applied to ordinary fixture calls and independent verification. A Windows dependency case
therefore correctly escalated an unintended transport ambiguity, and the stack suite had an
unexpected outcome. Normal execution now has a one-second deadline, verification has two seconds,
and only deliberately injected timeout faults use 150ms. The crash experiment uses a wider request
window. CI retains pytest scenario directories and matrix-failure artifacts, with fail-fast disabled.
Final delivery evidence records the corrected commit and its independently checked CI results.
