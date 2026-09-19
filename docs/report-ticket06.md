# Ticket 06 — role/run reports and measured baselines

Authorized by Adam, including report API, artifact store, CLI/plugin and real
read-only adapter/offline-fixture test seams. Review baseline:
`9497f53a74f923c01bb448b86fd9509d5c5d483a`.

**Accepted and closed** at Adam's explicit approval. Implementation: `ea50593`;
review fixes: `c4af4d3`; final verification: `f6b9c49`.

## Usage

Create a JSON manifest outside Hermes, listing explicit run selections:

```json
[{"board":"stillroom-research","run_id":"2"}]
```

Measure it through the same Kanban attribution and summed-usage join used by
single-run diagnosis:

```bash
.venv/bin/python -B -m agent_lab.diagnosis \
  --hermes-home /path/to/hermes --store /path/to/artifacts \
  --report /path/to/runs.json --workflow team
```

Keep the printed artifact path as the before-number. Measure the next cohort
with the same command plus `--baseline /path/to/artifacts/.../reports/DIGEST.json`.
The baseline must reside in the same store. `--workflow` names a stable logical
report cohort; it does not overwrite or invent the individual runs' workflow
identities. This permits the original baseline's multi-board, multi-task cohort.

The plugin provides the same rendering, with shell-style quoting:

```
/workflow-report HERMES_HOME RUNS_JSON WORKFLOW STORE [BASELINE_ARTIFACT]
```

The existing `/workflow-diagnose` command is unchanged. The ticket-04 activation
constraint still applies; this work does not edit or activate any live plugin.
For separately installed Hermes source, use the CLI's `--protected-root`; the
plugin forwards the loaded host source location automatically.

Python callers use `diagnose_report(home, selections, workflow_identity, store,
baseline=path)` and `load_report(path, store)` in `agent_lab.diagnosis.report`.
The runtime-neutral core is `measure_report(selections, source, workflow_identity,
store, baseline=path)`. A `ReportSource` supplies the existing attribution adapter
and usage protocols, plus a stable measurement-method version. Source-qualified
run selections are runtime-neutral; the Kanban front door interprets the source
as a board. Future adapters must change their method version whenever their join,
usage selection or metric semantics change, and configure their protected roots.

## Measurement and comparison contract

- Every selected run goes through `diagnose()` and the existing real read-only
  Kanban/Hermes adapters. The manifest is attribution input, never usage totals.
- Current and before evidence retains selections, run identities, roles, sessions,
  timestamps, task breakdowns and separate token counters. Unknown task names
  remain auxiliary; unrelated sessions remain excluded.
- Totals, every role, and every task show all four units. Calls/run and each
  token counter/run are arithmetic means over **all runs in that cohort/role**,
  including runs without that task. Context/call and cache hit rate use summed
  counters, not averages of individual rates. Raw calls, tokens and run counts
  are retained. Zero-denominator rates remain null (`n/a` in the terminal).
- Duplicate selections and shared sessions within a cohort fail rather than
  double-counting. Board-qualified selections disambiguate board-local run IDs.
- A before-number is a prior digest-verified report, with a required versioned
  measurement-method identifier. Legacy calls-only records, arbitrary supplied
  totals, another report workflow, or another join/metric version are rejected.
- Deltas are **after minus before**, for the four units overall and each shared
  role. Cache-rate deltas are fractional changes, displayed as percentage-point
  changes. There is no dollar estimate or generalized improvement claim.
- Run counts and role/task composition can differ. Both complete cohorts are
  presented; comparisons are explicitly descriptive, not causal. Roles present
  only on one side have no delta. Without a before artifact there is no comparison.
- The baseline digest and complete before cohort are embedded in the new report,
  so later source changes cannot rewrite the before-number. Reports used as a
  subsequent baseline contribute their **current** cohort, not their older before.

Report JSON includes rendered per-role/per-run summaries and comparisons alongside
source measurements. Computed fields are re-derived on load, and inconsistent
summaries are rejected. Narrow `prop-decorator` mypy suppressions accommodate
Pydantic's documented computed-property decorator limitation; metric functions
and their consumers remain typechecked.

Artifacts use the existing exclusive-link, read-only-mode, SHA-256-addressed
publisher under a per-report-workflow directory. Repeated measurements create
new observations, not overwrites. The store is an operator-controlled evidence
store, not a signed attestation against an operator forging an entire dataset.
Sequential live reads are not a transaction across multiple databases; the
existing snapshot-change checks and each run's observation timestamp still apply.

## Baseline and verification

`tests/test_diagnosis_baseline.py` now exercises the product report API through
real adapters against the existing numeric-only offline fixture. A saved before
and subsequent comparison reproduce **23 runs, 214 calls, 1,132,524 fresh input
tokens**, and all six independently published role rows. No new live extraction
or edits to Hermes were needed; fixture provenance is in `measurement-ticket05.md`.

Red/green slices covered the missing report API, measured-before comparison,
invalid cohort/baseline rejection, persisted role summaries, CLI/plugin rendering,
and direct-Python read-only protection. Targeted diagnosis/report/baseline tests:
**57 passed** before review; an additional runtime-neutral source regression now
passes. Mypy: **zero errors, 15 source files**.

## Standards

Independent review of implementation `ea50593` found one documented-standard
breach: the report boundary was Kanban-specific despite CONTEXT §9.1. A failing
public-seam test reproduced the absent runtime-neutral interface. Added
`ReportSource`/`measure_report` using the existing attribution and usage contracts,
with Kanban retained as the shipped front door. The new test measures and compares
a non-Kanban recorded runtime and rejects a changed join version.

Two heuristic duplication findings were addressed: the plugin commands now share
the subprocess/protected-root boundary, and single-run and aggregate measurements
share the token context/cache formulas.

## Spec

Independent review found **0 spec findings**; the reviewer independently ran all
57 targeted offline tests. All ticket-06 acceptance criteria were verified.

Follow-up independent reviews of `c4af4d3` confirmed **0 outstanding Standards
findings and 0 Spec findings**. All three original Standards findings were
addressed. The Spec reviewer additionally ran 14 report/baseline tests.

## Final verification

The first full suite exposed an older plugin-registration assertion expecting
only one command. Updated that public-boundary test to expect both commands and
exercise report invocation, protected-source rejection and byte preservation.
No production change was needed. The targeted read-only suite then passed (10
tests), followed by the full suite:

```bash
AGENT_LAB_JUDGMENT=stub \
HERMES_PLUGIN_TEST_SOURCE=/home/hermes/.hermes/hermes-agent \
HERMES_PLUGIN_TEST_PYTHON=/home/hermes/.hermes/hermes-agent/venv/bin/python \
  .venv/bin/python -m pytest -q
.venv/bin/python -m mypy agent_lab
```

**172 passed, 2 optional live-Jev skips.** The real Hermes loader registered and
invoked both commands in isolated fixture homes. Mypy: **zero errors in 15 source
files**. `git diff --check` passed. No live Hermes state was changed, no live model
calls were made, and plugin activation was not enabled.
