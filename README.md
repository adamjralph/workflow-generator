# Workflow Generator

Software that takes a person through step-by-step and multiple-choice questions, produces a
visual workflow, and builds or modifies a runnable workflow from that design.

**Start here → [CONTEXT.md](CONTEXT.md).** It holds the decided context: what has been decided,
what was ruled out and why, and what is still open.

## Status

Ticket 01 promotes the foundation into `agent_lab/` as the single local runtime core.
Ticket 02 adds run-level budget reservations, atomic event numbering, and a
return-value findings join; both tickets are accepted. Ticket 03 adds single-run
Kanban diagnosis, immutable records and a minimal terminal UI, pending acceptance.
Tickets 04–06 are untouched. See [ticket 03 evidence](docs/diagnosis-ticket03.md).

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

Concurrent branches must share `Deps.accounting` (a `RunAccounting` owner), even
when using separate judgment sources. Reserve before work; no model call holds
an accounting lock. Branches return their own frozen states through a reducer;
`collect_findings(base, returned_states, deps)` joins notes and refreshes the
budget without merging incompatible branch stages or artifacts. The existing
business route remains linear; the tests compose real parallel branches around
these shared semantics, not a new spec engine.

See [ticket 02 evidence and concurrency contract](docs/foundation/parallel-accounting.md).
The inherited **11 mypy errors** remain unsuppressed; typechecking is not green.

See [foundation provenance and limits](docs/foundation/README.md) for adoption
scope, inherited limitations, and verification details.

## Diagnose one Kanban run

From this checkout, supply a Hermes home to read and an artifact store outside it:

```bash
.venv/bin/python -m agent_lab.diagnosis \
  --hermes-home /path/to/hermes-home --store /path/to/project/artifacts
```

Enter the board directory name and its `task_runs.id` at the prompts. The terminal
shows calls/run (including auxiliary calls) and the saved artifact path. It reads
summed usage rows, never the sessions rollup. Each invocation creates a new
immutable observation; unavailable data is an error, not zero. Only calls/run is
implemented; the other units and breakdowns remain ticket 05.

## In one line

Diagnose existing Hermes workflows and measure them, then generate better ones — as a
read-only integration with Hermes; whether this ships as a community plugin remains open.

## Where the evidence lives

- Cost baseline and the measurement join:
  `~/Documents/life-os/Business/Stillroom/agent-team/verification/2026-09-18-cost-baseline/`
- Foundation and proven mechanics: `~/Projects/agent-workflow-lab` (see its `WHY.md`)
- Integration precedent (Hermes without modifying Hermes): `~/Projects/stillroom-studio`
- Plugin-with-a-UI precedent: `<hermes-agent>/plugins/kanban/dashboard/`
