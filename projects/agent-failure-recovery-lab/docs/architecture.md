# Architecture and implementation decisions

The experiment controller starts only its own fixed worker subprocesses. Workers call a fixed typed
mock operation through Toxiproxy. A separate direct API path reads the fixture's persisted receipt to
verify the outcome independently of worker claims and proxy state. Each scenario uses a new task ID,
worker database, and evidence directory. The backend binds a key to quantity and rejects conflicts.
The same key is reused for recovery, and a unique receipt row prevents replay from creating a second
mock side effect. Nothing in task data becomes a command, URL path, or dynamic import.

SQLite preserves lifecycle transitions, attempts, errors, backoff delays, and final reports. Legal
transitions are explicit; invalid transitions roll back. The final state/report are committed together.
Worker restart preserves consumed attempts and marks resumption. A nonblocking OS file lock prevents
two processes using one worker database. This is a local filesystem guarantee, not a distributed lock.
Receipts live in a separate backend database persisted on a Docker volume.

Timeout or malformed responses can follow a committed effect. The worker therefore queries the receipt
before replaying. Receipt identity and quantity must match; malformed or duplicate-effect receipts fail
schema validation. Verification outages are recorded. After the budget is exhausted, explicit HTTP
failure plus a confirmed missing receipt can fail safely; ambiguous transport/verification failures
require intervention. This logic applies to the fixture's receipt contract and cannot be generalized
to APIs lacking equivalent durable idempotency/verification.

The fixture models pre-effect HTTP failures/rate limits/dependency failures and post-effect malformed
or delayed responses. Toxiproxy separately injects real TCP latency and connection unavailability.
Its API canonicalizes wildcard listeners to `[::]:8666`; that equivalent address is accepted only for
the fixed wildcard lab listener. Existing different proxy destinations or toxics are rejected.
See the [official Toxiproxy API](https://github.com/Shopify/toxiproxy).

The Python Prometheus client exports counters and histograms at `/metrics`; Prometheus scrapes every
two seconds. Grafana provisions a fixed datasource and five query panels from repository files.
Actual API checks verify both a scraped metric and the provisioned dashboard. Metric semantics follow
[Prometheus metric types](https://prometheus.io/docs/concepts/metric_types/); dashboards use
[Grafana provisioning](https://grafana.com/docs/grafana/latest/administration/provisioning/).

The repository installs independently of Projects 01–04. There is no runtime dependency on another
portfolio project. Docker provides reproducible lab services, not arbitrary-agent code containment.
