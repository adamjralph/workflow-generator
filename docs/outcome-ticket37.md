# Ticket37 — bounded local webhook delivery

## Implemented boundary

`agent_lab.alerts.deliver_outcome_alert` completes the existing offline
report/checklist declared-output and bounded-remedy journey with an explicit
one-shot delivery. The caller supplies a literal loopback HTTP endpoint and
port. No listener is installed or left running. No external destination,
credential, query string, proxy or redirect is admitted. This is transport
capability verified locally, not a notification to Adam or acceptance of V2.

Passed and repaired results are suppressed. Exhausted, ineligible and
repair_failed results send the declared expectation, unmet requirements,
aggregate reserved allowance, outcome status, original/repair run identities,
exact remedy digest and a next action. Output artifact contents are excluded.
Expectation filenames, field names and allowed values are declaration data and
are included; endpoint selection therefore remains an explicit caller action.

Saved remedy and verdict bytes must match their in-memory records and digest
links before any reservation or delivery. One exclusive reservation precedes
transport. Re-entry raises and never resends, including after failure or
interruption. There is no retry or resume. A failed/timed-out delivery may already
have reached its receiver: the failure means no timely acknowledgement was
established. Interruption leaves a reservation without a final receipt, and is
unknown, never success. These are local single-attempt semantics, not distributed
exactly-once guarantees. Trusted caller code is not sandboxed.

A monotonic deadline bounds the attempt (positive timeout, maximum five seconds),
with socket shutdown to interrupt a receiver that drips response headers. HTTP
2xx means acknowledged by the local receiver, not read by a human. Redirects and
non-2xx responses fail. Delivery receipts are separate from the unchanged remedy
receipt and persist neither endpoint, exception text nor response body. Audit
write failures propagate rather than claiming recorded success.

## Validation — 2026-10-05

Checkout `/home/hermes/Documents/Codex/2026-10-05/task-5/workflow-generator`,
branch `ticket/37-local-outcome-alert`, isolated from verified ticket36 checkpoint
`c9e524a867f14fe96f76cd828e91b74283f0693b`. Original and predecessor checkouts
were preserved. The predecessor's five combined status files were copied only
into this successor; its separate status patch is retained at `../ticket36-status.patch`.
The ignored interpreter symlink points at the existing project `.venv`.

Final focused command, through the existing wrapper from the original cwd:

```bash
/home/hermes/.hermes/profiles/astra-pinned/bin/workflow-generator-validation \
  /home/hermes/Projects/workflow-generator/.venv/bin/python -m pytest -q \
  /home/hermes/Documents/Codex/2026-10-05/task-5/workflow-generator/tests/test_outcome_alerts.py \
  /home/hermes/Documents/Codex/2026-10-05/task-5/workflow-generator/tests/test_outcome_remedy.py \
  /home/hermes/Documents/Codex/2026-10-05/task-5/workflow-generator/tests/test_outcome.py \
  /home/hermes/Documents/Codex/2026-10-05/task-5/workflow-generator/tests/test_outcome_values.py --tb=short
```

**135 passed**, exit 0, 13.14 seconds. Private evidence
`/home/hermes/workflow-validation-scratch/v-s8q19h`.
Typing from this checkout: existing interpreter `-m mypy --cache-dir
/tmp/ticket37-mypy agent_lab`: **48 source files clean**, exit 0.
`graft build` completed; fresh-session state guard passed.

Tests exercise both existing drivers, successful/repaired suppression,
unresolved delivery, real local receiver acknowledgement, non-2xx/redirect
failure, connection failure, timeout ambiguity, interrupted reservation,
no-resend, endpoint rejection, evidence tampering and actual slow-header deadline.
They reuse the internal report/checklist contract from `remedy_demo.ReportInput`.
All receiver threads/listeners are cleaned up. No live provider or external
communication was performed.

Complete final-code regression: **2,534 passed, 3 expected skips**, exit 0,
1,055.63 seconds (17m35s), private evidence
`/home/hermes/workflow-validation-scratch/v-j4Ha89`. Both the saved terminal
summary and `pytest-exit.txt` (0) were read back. The skips are two opt-in live
TypeSafe tests and the optional real Hermes plugin-loader check. No duplicate
runner was launched, no elapsed-time abort occurred, and no corrective code
change was needed during this run. Final implementation checkpoint was `c7de3f4`;
subsequent changes are status/evidence documentation only.

Exact complete-suite command from the original project cwd:

```bash
/home/hermes/.hermes/profiles/astra-pinned/bin/workflow-generator-validation bash -c '
/home/hermes/Projects/workflow-generator/.venv/bin/python -m pytest -q \
  /home/hermes/Documents/Codex/2026-10-05/task-5/workflow-generator/lessons \
  /home/hermes/Documents/Codex/2026-10-05/task-5/workflow-generator/tests --tb=short \
  2>&1 | tee "$WORKFLOW_VALIDATION_DIR/pytest-output.log"
result=${PIPESTATUS[0]}
printf "%s\n" "$result" > "$WORKFLOW_VALIDATION_DIR/pytest-exit.txt"
exit "$result"'
```

Earlier focused passes (60 and 134 tests) preceded the final deadline regression;
they are superseded by the final 135-test run, not combined into evidence.

## Independent review

The code-review skill ran separate Standards and Spec agents against the fixed
checkpoint and implementation commits. Both found the same unbounded slow-header
response issue. Commit `c7de3f4` corrected it with an overall deadline and direct
regression. Both reviewers inspected the correction and reported zero remaining
findings. Reviews were read-only and did not claim independent test execution.
This is independent agent review plus developer validation, not Adam's personal
review or acceptance. No reviewer block was bypassed.

## Remaining release gaps

An actual external channel and recipient still need approval (V2); the local
transport does not settle that decision. Live repair/spend policy V3,
representative real-workflow acceptance V4, expanded runtime contract V5,
browser outcome/remedy integration and attributed end-to-end measurement remain.
No deployment, ongoing access, gate bypass, source mutation or credentials change.
