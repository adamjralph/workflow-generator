# Workflow Generator

Software that takes a person through step-by-step and multiple-choice questions, produces a
visual workflow, and builds or modifies a runnable workflow from that design.

**Start here → [HANDOFF.md](HANDOFF.md).** Run its state check before reading status.
[CONTEXT.md](CONTEXT.md) provides detailed decisions on demand.

## Status

**Current project state and next decisions: [CURRENT.md](CURRENT.md).**
The compact status index is [state.json](state.json); check it with
`python3 scripts/project_state.py check` and measure the fresh read with
`python3 scripts/project_state.py measure`.

Delivered: read-only diagnosis and baselines; restricted in-memory workflow
execution/conformance; a local browser designer and questionnaire; bounded role/data
snapshots; LinkedIn capture, generation/review plumbing and offline replay; one
parallel wave, Decision routes and bounded Loops within its branches; a restricted
offline Gate pause/restart path. Tickets 01–18 and 20–27 are closed, including
ticket 13's reconciled bookkeeping. Tickets 28–31 are accepted and published;
ticket 32 is implemented, verified and pushed, awaiting Adam's separate acceptance.
This is not full-product completion: gates between parallel waves, regeneration,
role/skill emission, permission proof and the integrated journey remain unfinished.
The [delivery map](.scratch/workflow-generator/map.md) lists the remaining outline
rows; most are blocked on unsettled decisions rather than on code.

Ticket 19 is accepted for its bounded **operator-pinned** live path only. A real
Codex Generator → independent Vertex Guardian pair completed with a passing offline
Check, but the default oldest-draft selection mode has never been live-exercised:
invalid inventory stays fail-visible and the oldest eligible file is dated
2026-09-08. See [issue 19](.scratch/workflow-generator/issues/19-refine-and-review-oldest-linkedin-draft.md).

**First-stop release scope (accepted 2026-09-26):** [the expected-outcome verification pillar](docs/outcome-verification-pillar.md)
— declare what each agent must produce, check the observed outcome, try a bounded
remedy, alert on failure. Internal-only first stop; LinkedIn is one acceptance
scenario, not the release definition. Verify **behaves as declared**, not "was the work
good." Scope accepted; V2–V5 open and no implementation authorized.
[Issue 33 context cleanup](.scratch/workflow-generator/issues/33-unambiguous-fresh-session-context.md)
is implemented locally, with guard and injected-failure checks passing; it awaits
Adam's acceptance. For publication status, inspect Git and remote.

Full offline regression (2026-09-26, this checkout): **2,399 passed, 3 optional
skips, exit 0**; `mypy agent_lab` clean in 43 source files. Run it through the
validation wrapper that supplies a permitted evidence root outside Hermes:

```bash
/home/hermes/.hermes/profiles/astra-pinned/bin/workflow-generator-validation \
  .venv/bin/python -m pytest -q --tb=short
```

A plain `pytest` from a session whose scratch root sits inside Hermes still fails
against the evidence-directory guard by design; do not disable the guard. Public
format, distribution/naming and Hermes writes remain deferred.

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
budget without merging incompatible branch stages or artifacts. The accepted wave
engine (tickets 28–32) executes declared Fork/join waves with thread-dispatched
concurrency, whole-wave budget admission and declared-order failure selection;
Decision routes and bounded Loops are supported inside a branch, and Gates remain
a separate offline-only path. See [ADR 0011](docs/adr/0011-parallel-waves-are-declared-order-deterministic.md)
and the [parallel wave contract](docs/parallel-wave-contract.md).

See [ticket 02 evidence and concurrency contract](docs/foundation/parallel-accounting.md).
`.venv/bin/python -m mypy agent_lab` passes with zero errors (43 source files).
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
