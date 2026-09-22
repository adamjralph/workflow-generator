# Workflow Generator

Software that takes a person through step-by-step and multiple-choice questions, produces a
visual workflow, and builds or modifies a runnable workflow from that design.

**Start here → [CONTEXT.md](CONTEXT.md).** It holds the decided context: what has been decided,
what was ruled out and why, and what is still open.

## Status

**Current project state and next decisions: [CURRENT.md](CURRENT.md).**

Delivered: read-only diagnosis and baselines; restricted in-memory workflow
execution/conformance; a local browser designer and questionnaire; bounded role/data
snapshots; LinkedIn capture, generation/review plumbing and offline replay. Tickets
01–18 and 20–27 are closed, including ticket 13's reconciled bookkeeping. This is
not full-product completion: parallel execution, exact-version Gate/resume,
regeneration, agent permissions and the integrated journey remain unfinished.

Ticket 19 is **Blocked** on successful live execution; ticket 28 (one parallel wave)
is the next approved implementation and has not started. The new synthetic DeepSeek
probe establishes endpoint response, not a completed live workflow or exact-model
acceptance. See [provider triage](docs/provider-triage-2026-09-22.md).

Historical offline regression: **1,892 passed, 3 optional skips**. The fresh assessment
run was **1,016 passed, 876 failed, 3 skipped**, predominantly because the current
session's mandatory scratch root is inside Hermes and evidence guards reject it.
Do not claim a new green suite or disable those guards. Details and remaining direct
decisions are in `CURRENT.md`. Public format, distribution/naming and Hermes writes
remain deferred.

## Local development

Tested with Python 3.14.7. From this repository's root:

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
AGENT_LAB_JUDGMENT=stub .venv/bin/python -m pytest
```

No lab checkout, Hermes installation, API key, or network access is needed to run
the default tests after dependency installation. Credentials tests use temporary fake files;
the two live tests and the real-Hermes plugin-loader check remain opt-in. Do not point credential files or stores at Hermes.

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
`.venv/bin/python -m mypy agent_lab` passes with zero errors (16 source files).
See [ticket 07 verification](docs/typechecking-ticket07.md).

See [foundation provenance and limits](docs/foundation/README.md) for adoption
scope, inherited limitations, and verification details.

## Diagnose one Kanban run

From this checkout, supply a Hermes home to read and an artifact store outside it:

```bash
.venv/bin/python -m agent_lab.diagnosis \
  --hermes-home /path/to/hermes-home --store /path/to/project/artifacts
```

Use `-B` (or `PYTHONDONTWRITEBYTECODE=1`) if the tool checkout must also remain
byte-identical. If Hermes source is installed separately, add
`--protected-root /path/to/hermes-agent`. Stores must be outside Hermes and this
tool's source checkout. Temporary DB/WAL copies are read outside protected roots;
a changing database or nonempty rollback journal produces an explicit retry error.

For local plugin installation and its host activation constraint, see
[ticket 04](docs/read-only-ticket04.md#local-plugin-installation-not-a-distribution-decision).

Enter the board directory name and its `task_runs.id` at the prompts. The terminal
shows calls/run, context/call, separate token counters/run, cache hit rate, task
breakdowns and the saved artifact path. Totals include auxiliary/review traffic,
but only for sessions named by the recorded run. It reads summed usage rows,
never the sessions rollup. Each invocation creates a new immutable observation;
unavailable counters are errors, not zero. Undefined rates display as `n/a`.
See [measurement formulas and baseline reproduction](docs/measurement-ticket05.md).

## Compare a measured baseline

Pass `--report /path/to/runs.json --workflow team` to diagnose an explicit JSON
list of `{"board": "board-name", "run_id": "2"}` selections. Save the artifact
path, then add `--baseline /path/to/that/artifact.json` when measuring the next
cohort. Reports show all four units per run and role, plus the measured before
and numeric deltas. Without a measured before, there is no comparison.

The plugin equivalent is `/workflow-report HERMES_HOME RUNS_JSON WORKFLOW STORE
[BASELINE_ARTIFACT]`. See [the complete contract](docs/report-ticket06.md).

## In one line

Diagnose existing Hermes workflows and measure them, then generate better ones — as a
read-only integration with Hermes; whether this ships as a community plugin remains open.

## Where the evidence lives

- Cost baseline and the measurement join:
  `~/Documents/life-os/Business/Stillroom/agent-team/verification/2026-09-18-cost-baseline/`
- Foundation and proven mechanics: `~/Projects/agent-workflow-lab` (see its `WHY.md`)
- Integration precedent (Hermes without modifying Hermes): `~/Projects/stillroom-studio`
- Plugin-with-a-UI precedent: `<hermes-agent>/plugins/kanban/dashboard/`
