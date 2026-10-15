# Threat model

The operator is trusted to start the local lab and select output paths. Control endpoints can change
faults and proxy availability, so they are exposed only on loopback host ports. They deliberately lack
authentication/TLS and must not be made public. The fixed Docker network permits lab services only;
the application accepts loopback and explicit Compose service hostnames rather than arbitrary URLs.
Redirects and ambient HTTP proxy configuration are disabled for control and worker calls.

Task IDs and quantities are strictly validated. The backend operation is a mock ledger insert, with
request-bound idempotency and conflict checks. External instructions cannot introduce new commands,
tools, providers, or executable worker code. Only subprocesses launched by the controller are killed.
The suite changes only the `lab` proxy and the named toxic it creates, and restores availability.
Concurrent suites are unsupported because they intentionally share that one control surface.

The OS and trusted local filesystem enforce evidence access. New suite directories prevent ordinary
overwrite; this is not a public multi-user path API. Backend files and worker logs may contain fixture
task IDs/quantities. Credentials and model prompts are not involved. Prometheus metrics are telemetry,
not an authenticated audit trail. Backend restart resets counters while durable receipts remain.

The fixture's unique receipt is scoped exactly-once evidence for its mock insert. Network partitions,
database loss, unknown downstream effects, hostile workloads, and distributed lock safety are not
established by these tests. Unknown verification remains human-required rather than being declared
successful. A terminal intervention result requires an explicit operator decision before new work.
