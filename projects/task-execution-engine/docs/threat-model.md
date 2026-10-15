# Security considerations

Trust boundary: the local operator and target repository tests are trusted. Request content is
validated but cannot grant OS isolation. External content is never used to generate commands;
there is no model-driven planner in P0.

Controls:

- Strict schema rejects unknown fields, operations, duplicate operations, and excessive budgets.
- Explicit operation authorization happens before all subprocess launches.
- Only fixed interpreter commands execute, without a shell and without operator-provided flags.
- Python isolated mode reduces interpreter path/environment injection; pytest plugin autoload
  and inherited addopts are disabled. Repository test code/configuration remains executable.
- The subprocess receives a small environment allowlist, excluding provider credentials and
  Python/pytest override variables. Tests may still read credentials from the filesystem.
- Root validation requires a project manifest; the tests entry must remain within the repository.
- Retry eligibility excludes test code and formatting mutations; duplicate claims prevent replay.
- Formatting changes require explicit operation authorization and mandatory subsequent checks.
- Source scope rejects links/hardlinks and enforces file/byte limits. Ruff ignores repository
  configuration; there are no lint autofixes or user-controlled formatter arguments.
- Original source snapshots, patch hashes, and AST comparisons provide correction evidence.
- Structured audit records preserve authorization, invocations, errors, verification, and states.
- Container execution uses non-root, no network, dropped capabilities, and read-only mounts.

Residual risks: hostile tests/configuration can execute arbitrary Python, forge JUnit, tamper with
files accessible to the operator, create symlinks, leak secrets into output, or spawn detached
children. The validator does not comprehensively inspect every repository file or eliminate TOCTOU
races. Report output is bounded but temporary capture can exhaust disk. XML verification is size
limited but is not a hostile-input service. Audit records are not signed or tamper-proof.
Windows uses a kill-on-close Job Object and a startup gate so tool code begins only after job
assignment. POSIX uses a new process group. These lifetime controls are not a filesystem or
network containment boundary. A POSIX child can escape its process group; Windows children created
through external services may escape job inheritance. Never treat the local
CLI as suitable for untrusted repository execution.

Windows lifecycle behavior follows [Microsoft's Job Objects documentation](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects).

Future work: mount isolation and disk budgets, signed approval tokens, report redaction, process
containment tests, pinned dependency review, and authenticated multi-user control. No external
deployment or publication is part of P0.

Correction limits: local requests express the trusted operator's approval rather than an
authenticated external approval service. Source snapshots and patches can contain sensitive
code. The operator must protect artifact storage. AST equality detects changes to parsed Python
structure; it does not prove unchanged comments, tooling directives, or external behavior.
Concurrent writers and malicious test code can still race validation and mutate other accessible
files. Formatter interruption can leave partial changes, which are reported rather than silently
rolled back. Formatting/lint subprocesses buffer their output in memory; only runner display
output is capped. Use container limits for additional resource containment.
