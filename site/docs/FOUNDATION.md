# Portfolio delivery structure

The employer entry point is the [GitHub portfolio](https://github.com/texasbredmj/ai-engineering-portfolio#start-here). The devcontainer starts the integrated platform and exposes one private forwarded port. See [the integrated architecture](INTEGRATED-ARCHITECTURE.md) and [employer walkthrough](EMPLOYER-TEST.md).

All eight source snapshots and their original commit references are under `projects/`. Projects 02, 03, 06 and 08 participate in the live workflow. Projects 01, 04, 05 and 07 have real independent demonstrations and serve maintenance, evaluation, recovery and delivery roles. Run `python scripts/project_demo.py all` to verify every demonstration.

Root `evidence/` retains historical component checkpoints. Their recorded CI applies to those original commits, not to new integration changes. Current integration results are checked through `.github/workflows/integrated-platform.yml`; generated per-environment reports appear in the dashboard's Project evidence view.

The static showcase is `site/`. The application and showcase run together in the Codespace. Production identity, paid model endpoints and arbitrary external side-effect guarantees are outside the fixture scope. Personal resume attribution remains a draft for owner review.
