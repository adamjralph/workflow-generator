# Ticket 29 — hand-authored offline acceptance cases (draft)

These are independent expected outcomes for the public seam in [issue 29](../.scratch/workflow-generator/issues/29-pause-decide-and-continue-one-route-gate.md). They are not output captured from either driver. The event schema and commit ordering still require implementation/review; do not mark the ticket accepted from this document.

## Fixed specimen

A frozen strict state with integer `value`, initially `0`. A Route workflow has `before` (registered pure `add 1` transform) → `review` (Gate) → `after` (the same registered pure `add 1` transform) → `DONE`. The Gate's `approved` edge leads only to `after`; `rejected`, `pending`, and `invalid` edges terminate as `REJECTED`, `PENDING`, and `FAILED_VALIDATION`. The safety terminal `FAILED_BUDGET` is declared. No arbitrary Python binding is admitted. A separate caller-named external store holds immutable spec, bundle, run and audit artifacts. Reference and graph drivers receive distinct offline fixture decisions when checked; fixture decisions never authorize an operator run.

## Expected state and accounting

- With budget **1**, `before` finishes at value `1`, used `1`; the Gate visit is refused as `FAILED_BUDGET` before it is charged. `after` is never invoked. The log records the refusal; there is no pause or decision.
- With budget **2**, `before` finishes at value `1`, used `1`; Gate visit charges exactly one step and commits `PENDING` with value `1`, used `2`, remaining `0`. On a valid scoped approval, the Gate is not charged again, but `after` is refused for budget, ending `FAILED_BUDGET` with value `1`, used `2`. On rejection, end `REJECTED` with value `1`, used `2`, and never invoke `after`.
- With budget **3**, pause has value `1`, used `2`, remaining `1`. Approval for that exact run/version/Gate/pause continues to `after`, yielding `DONE`, value `2`, used `3`; rejection yields `REJECTED`, value `1`, used `2`. Neither decision submission nor continuation spends a step itself.
- Before a decision, `after` has not run. An invalid, stale, conflicting, wrong-run/Gate/pause/version or forged decision never runs `after`; altered spec, bundle, checkpoint, event chain or audit-write failure also prevents downstream execution. Identical repeated submissions are idempotent; conflicting submissions are not.

## Canonical event intent

A successful pending prefix has a completed `before/done` transition at used `1`, then exactly one `review/pending` transition at used `2` with a committed pause/checkpoint binding both identities. A rejection appends one auditable `review/rejected` resolution with unchanged used `2`; approval appends one `review/approved` resolution with unchanged used `2`, then the `after/done` event at used `3` (or `after/FAILED_BUDGET` at used `2`). There must never be a second Gate visit event or duplicate `before` event on continuation. Exact fields, sequence numbering, failure events, event-head digest and checkpoint/decision ordering are to be fixed before green implementation, and independently asserted from retained bytes rather than inferred from driver agreement.

## Review baseline

At authorship, the accepted D2 contract and ADR 0012 are uncommitted in the shared worktree; repository `HEAD` alone cannot identify the review contract. The earlier RED probe used arbitrary lambda mappings and is retained outside Git only as evidence that current drivers reject Gate—not as a test of this restricted seam. Freeze the eventual source/test/contract set before independent review. No live call, commit, push or ticket 30 work follows from these cases.
