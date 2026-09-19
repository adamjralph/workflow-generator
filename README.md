# Workflow Generator

Software that takes a person through step-by-step and multiple-choice questions, produces a
visual workflow, and builds or modifies a runnable workflow from that design.

**Start here → [CONTEXT.md](CONTEXT.md).** It holds the decided context: what has been decided,
what was ruled out and why, and what is still open.

## Status

Ticket 01 promotes the foundation into `agent_lab/` as the single local runtime core.
Its full regression suite runs here: **65 passed, 2 optional live-Jev tests skipped**.
Diagnosis adapters and measurement are not implemented yet. Tickets 02–06 have not
been started; ticket closure remains with Adam.

The product spec and ADRs record future work, not this ticket's build target.
Spec serialization, distribution/packaging, product naming, and the community-plugin
question remain undecided.

## Local development

Tested with Python 3.14.7. From this repository's root:

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
AGENT_LAB_JUDGMENT=stub .venv/bin/python -m pytest
```

No lab checkout, Hermes installation, API key, or network access is needed to run
the tests after dependency installation. Credentials tests use temporary fake files;
the two live tests remain opt-in. Do not point credential files or stores at Hermes.

Import the existing boundary directly (no wrapper or second implementation):

```python
from agent_lab import RunState, Budget, Deps, StubSource, ApprovalStore, RunLog, run_plain
from agent_lab.state import ALLOWED, TERMINATES, Terminal
from agent_lab.graph_workflow import run_graph
```

`Deps` injects a `JudgmentSource`, approval store, and run log. Both drivers use
`agent_lab.workflow.step`; the plain driver is the reference. Store paths must be
in a user-named project directory, never in Hermes.

See [foundation provenance and limits](docs/foundation/README.md) for adoption
scope, inherited limitations, and verification details.

## In one line

Diagnose existing Hermes workflows and measure them, then generate better ones — as a
read-only integration with Hermes; whether this ships as a community plugin remains open.

## Where the evidence lives

- Cost baseline and the measurement join:
  `~/Documents/life-os/Business/Stillroom/agent-team/verification/2026-09-18-cost-baseline/`
- Foundation and proven mechanics: `~/Projects/agent-workflow-lab` (see its `WHY.md`)
- Integration precedent (Hermes without modifying Hermes): `~/Projects/stillroom-studio`
- Plugin-with-a-UI precedent: `<hermes-agent>/plugins/kanban/dashboard/`
