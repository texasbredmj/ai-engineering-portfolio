# Development evidence workflow

Capture useful engineering evidence during implementation, then review it before publication. This foundation establishes the format; automated capture and project completion updates are section 2 deliverables.

## Milestone triggers

Create a record after an architecture decision, a reproduced bug and verified fix, a test exposing false success, an authorization improvement, a recovery demonstration, or a consequential tradeoff. Capture the problem, individual contribution, AI assistance, result, exact commit and supporting checks. Include a failing example when it explains why the fix matters.

Copy templates/milestone.json into evidence/milestones/YYYY-MM-DD-project-topic.json. Replace every placeholder and mark the record reviewed only after checking its links, attribution and results. Keep screenshots redacted. Do not include .env, tokens, credentials, personal data or raw unreviewed logs. A CI workflow file is not evidence of a successful run.

## Project completion sequence

1. Run project-specific checks and inspect the actual results.
2. Record exact source commit, CI run and evidence checksums; preserve useful redacted results before artifact expiry.
3. Review contribution attribution, limitations and two interview tradeoffs.
4. Update showcase/projects.json and the project walkthrough.
5. Add supported accomplishments to resume/2026.md after personal attribution review.
6. Run python scripts/build_showcase.py, python scripts/verify_checkpoint.py and python scripts/verify_foundation.py.
7. Review browser behavior and publication, then add each project's Start Here link to the verified published URL.

No background collector or scheduled updater is active. During future authorized development, milestone capture is an explicit development task. Automation implementation must include an invalid-record check and a reviewed example before section 2 can pass.
