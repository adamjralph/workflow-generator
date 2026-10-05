# Ticket 36 — one bounded offline output repair

## Implemented boundary

`agent_lab.remedy.run_with_remedy` admits one offline Transform, budget one,
`done` directly to `COMPLETED`, with a declared output. Gates, models, multistep
workflows and alternate execution routes are rejected before either factory.
Existing `run_checked` behavior is unchanged. This opt-in API supplies trusted
Python bindings, not a sandbox or provider permission.

The caller supplies `step_allowance=1` (original only) or `2` (one repair allowed).
A saved policy reserves the original step before its factory. Only a completed
original execution with failed output is eligible. Repair receives the immutable
original verdict, including declared requirements and unmet fields, starts from
the original detached input, and writes a fresh run-owned directory. It executes
through the selected existing driver and the same actual-file checker.

The second step is reserved before the repair factory; failure does not refund it.
There is no loop, restart or resume API. Each engine execution independently has
budget one; the receipt records the aggregate reserved allowance across both.
The original output, declaration, run log and verdict remain; the final receipt
links run identities and exact saved-verdict digests. Output verdicts retain their
existing spec/output digests. A compliant repair produces `repaired`; an unresolved
output produces `exhausted`. Failed original execution is `ineligible`. Callback or
setup failure produces `repair_failed` without exception content. Audit errors
propagate, leaving no completed receipt. Interrupted execution is not automatically
resumed; a reservation without a final receipt is incomplete, never a success proof.

This is a concrete offline repair seam and executable demonstration, not a live
agent repair, durable exactly-once guarantee, source-write authorization, real
alert, or complete release. Trusted bindings can perform arbitrary effects;
production provider guards and real/spend policy V3 are still open. V2, V4 and V5,
browser integration and a representative real-workflow acceptance remain open.

## Reproduction and evidence — 2026-10-05

Checkout: `/home/hermes/Documents/Codex/2026-10-05/task-4/workflow-generator`.
Base checkpoint: ticket35 commit `0166402896f3a275395c65062b1dd3f9eac8155c`.
Ignored `.venv` symlink points to the existing project interpreter, fixing the
checkout-local launch path without environment/package changes.

Every pytest invocation uses the existing wrapper from the original project cwd:

```bash
cd /home/hermes/Projects/workflow-generator
/home/hermes/.hermes/profiles/astra-pinned/bin/workflow-generator-validation \
  /home/hermes/Projects/workflow-generator/.venv/bin/python -m pytest -q \
  /home/hermes/Documents/Codex/2026-10-05/task-4/workflow-generator/lessons \
  /home/hermes/Documents/Codex/2026-10-05/task-4/workflow-generator/tests --tb=short
```

Before implementation, the complete ticket35 regression passed: **2,470 passed,
3 expected skips**, exit 0, 1,034.33 seconds. Evidence:
`/home/hermes/workflow-validation-scratch/v-P217r0`. This is one complete run,
not an aggregate inferred from earlier failed-test reruns.

Final focused command uses the same wrapper/interpreter and these absolute test
paths: `tests/test_outcome_remedy.py`, `tests/test_outcome.py`,
`tests/test_outcome_values.py`, `tests/test_workflow_spec.py`,
`tests/test_generation.py`, with `-q --tb=short`: **188 passed**, exit 0,
evidence `/home/hermes/workflow-validation-scratch/v-Qd3zFv`.
An earlier fixture omitted frozen state configuration and failed; it was corrected.
Subsequent narrower passes were superseded by this final focused run.

Typing from the isolated checkout: existing interpreter `-m mypy --cache-dir
/tmp/ticket36-mypy agent_lab`: **47 source files clean**, exit 0.

Post-change full regression was interrupted before completion. The run used the
full command above, evidence `/home/hermes/workflow-validation-scratch/v-0ZH6CV`,
and reported progress through 77% without a reported failure. The wait was aborted
and the runner PID was subsequently absent. No aggregate exit status or complete
test total was observed; **no post-change full green result is claimed**.
Next session must rerun the complete command before calling ticket36 technically
complete or starting another ticket. The ticket35 baseline remains a distinct
complete passing run.

Standalone demonstration completed, exit 0, evidence
`/home/hermes/workflow-validation-scratch/v-72oSIB`. Exact command:

```bash
cd /home/hermes/Projects/workflow-generator
/home/hermes/.hermes/profiles/astra-pinned/bin/workflow-generator-validation \
  bash -c 'cd /home/hermes/Documents/Codex/2026-10-05/task-4/workflow-generator; exec /home/hermes/Projects/workflow-generator/.venv/bin/python -m agent_lab.remedy_demo --store "$WORKFLOW_VALIDATION_DIR"'
```

Four saved receipts were observed: repaired and exhausted through reference and
graph drivers. The focused demo test also executed its entry point and verified
receipt content. Public-safe internal checklist artifacts are produced; this is
not real-workflow acceptance.

## Self-review and handoff

Standards and Spec self-review use the code-review skill's two axes, adapted to
Adam's explicit self-review instruction. No independent agent was delegated and
no personal review/acceptance by Adam is claimed. Review caught and fixed audit
error handling before final focused validation. No remaining blocking findings.
Runtime admission, bounds, original-input preservation, fresh output, saved digest
attribution, invalid route, factory/binding errors and no further repair are tested.

The original checkout and task-3 checkout are untouched. Focused implementation
commit excludes the five inherited status files. `../ticket36-status.patch` is a
cumulative ticket35+ticket36 delta against the exact inherited original status
contents, excluding the inherited edits themselves; do not apply ticket35's delta
again when using it. Combined status files remain uncommitted in this checkout.
No merge, PR, deployment, outgoing communication, live call or credential change.
For publication, inspect Git and the focused remote branch; the final handoff
records the observed push/read-back result.
