# Threat model

The operator controls dataset paths and output location. Dataset records and recorded decisions are
untrusted data. No field is executed as a shell command, Python expression, import path, or URL.
Tools are fixed typed in-memory functions. Permissions and approval are enforced by the backend,
not by candidate intent. A denied request has a receipt and no side effect.

Schema and size limits constrain ordinary malformed input. Output paths are explicitly supplied by
the operator; the application requires a new directory to avoid overwriting evidence. OS filesystem
permissions remain the boundary for local files. The CLI is not designed to accept hostile multi-user
path requests or execute unknown plugin code. Traces intentionally omit external content/arguments.
Reports include fixture receipts and should be reviewed before using sensitive domain datasets.

Dataset expectations and pricing are operator-controlled evaluation policy. A malicious operator can
weaken them or falsify recorded usage. Hashes detect changes, not authenticity. Code review, trusted
CI, and external provenance remain necessary. Recorded model usage is not a billing attestation.
No production model keys are needed or embedded. This project makes no claim of container isolation
for arbitrary code: its container executes only this fixed package.
