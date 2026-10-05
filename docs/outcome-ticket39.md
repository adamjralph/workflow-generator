# Ticket39 — explicit alert delivery attempt and receipt

## Implemented boundary

The existing ticket38 LinkedIn review-packet journey accepts either an explicit
endpoint or one trusted `AlertAdapter`. Supplying both stops before recording
replay. The same attribution-redacted ticket37 envelope is constructed and checked
before reservation; successful/repaired outcomes suppress delivery without calling
an adapter. No new source, model call, destination or external transport is added.

`deliver_alert_with_adapter` closes an exclusive saved reservation before invoking
`send(payload, attempt_id, timeout)` once. The adapter contract requires one bounded
attempt without retry, fallback or redirect. Trusted adapter code is responsible
for enforcing timeout; the coordinator cannot cancel arbitrary trusted Python.
The supplied `LoopbackAlertAdapter` retains the actual socket/deadline bounds and
literal-loopback endpoint validation. Implementing another adapter is not approval
for its recipient, credentials or external communication.

The final receipt retains the existing suppressed/delivered/failed status and adds
suppressed/acknowledged/rejected/unknown completion. HTTP 2xx establishes transport
acknowledgement only, never human reading or acceptance. Explicit non-2xx responses
are rejected; late responses, exceptions and malformed adapter replies are unknown.
Exception text, endpoint and response body never enter the receipt. Interruption
leaves only the reservation; audit-write failures propagate. Every consumed attempt
blocks re-entry regardless of adapter selection or final receipt availability.

`read_alert_audit` performs no transport and returns unattempted, reserved without
a final receipt, or completed with its receipt. It checks saved remedy bytes,
reservation run identity, remedy/payload digest links and receipt status consistency.
These are consistency checks for trusted local evidence, not tamper-proof distributed
exactly-once delivery. Reserved and completed/unknown both forbid automatic resend.
The reader admits ticket39 reservations; older ticket37/38 audit records remain
unchanged and require their existing inspection, not migration or resend.

## Validation — 2026-10-05

Checkout `/home/hermes/Documents/Codex/2026-10-05/task-7/workflow-generator`, branch
`ticket/39-explicit-alert-delivery`, directly based on verified ticket38
`8da7b153743de67fb5aadc7e37763675ebfc6741`. Original and predecessor edits are preserved.
Checkout-local ignored `.venv` symlink uses the existing interpreter; no package,
credential/profile or persistent credential-helper changes. The successor origin
URL matches the verified original remote. Python 3.14.7, pytest
9.1.1 and local `agent_lab` import were verified before aggregate testing.

Plugin subprocess preflight passed, 1 test, exit 0, 1.69 seconds; private evidence
`/home/hermes/workflow-validation-scratch/v-2u9tWV`. The initial sandboxed wrapper
could not create its required private evidence directory; the authorized escalated
wrapper succeeded. An early focused command named a nonexistent file and ran zero
tests (exit 4); the corrected run passed 91 tests before final added coverage.

Final focused command from the original project cwd:

```bash
/home/hermes/.hermes/profiles/astra-pinned/bin/workflow-generator-validation \
  /home/hermes/Documents/Codex/2026-10-05/task-7/workflow-generator/.venv/bin/python -m pytest -q \
  /home/hermes/Documents/Codex/2026-10-05/task-7/workflow-generator/tests/test_outcome_alerts.py \
  /home/hermes/Documents/Codex/2026-10-05/task-7/workflow-generator/tests/test_review_outcome.py \
  /home/hermes/Documents/Codex/2026-10-05/task-7/workflow-generator/tests/test_outcome_remedy.py \
  /home/hermes/Documents/Codex/2026-10-05/task-7/workflow-generator/tests/test_outcome.py \
  /home/hermes/Documents/Codex/2026-10-05/task-7/workflow-generator/tests/test_outcome_values.py --tb=short
```

**202 passed**, exit 0, 29.58 seconds; private evidence
`/home/hermes/workflow-validation-scratch/v-S7kfYi`. Tests cover real local receivers,
both drivers, reservation visible inside adapter invocation, acknowledgement versus
rejection/unknown, exception/interruption and no resend, suppressed invocation,
malformed replies, saved-link mismatch, receipt-write failure and ticket38 attribution
redaction. Existing slow-header deadline checks continue to pass. No external sends.
Typing: `.venv/bin/python -m mypy --cache-dir /tmp/ticket39-mypy agent_lab` —
**49 source files clean**, exit 0. `git diff --check`, `graft build` and fresh-state
check passed. Initial typing failures were corrected before the final clean run.

Complete final-code regression at implementation checkpoint `7a19158` passed
**2,601 tests with 3 expected skips**, exit 0, **1,037.99 seconds** (17m17s),
on 2026-10-05. Saved terminal summary and `pytest-exit.txt` (0) were read back.
Skips are the two opt-in live TypeSafe tests and optional real Hermes plugin loader.
Exact command from original project cwd:

```bash
/home/hermes/.hermes/profiles/astra-pinned/bin/workflow-generator-validation bash -c '
/home/hermes/Documents/Codex/2026-10-05/task-7/workflow-generator/.venv/bin/python -m pytest -q \
  /home/hermes/Documents/Codex/2026-10-05/task-7/workflow-generator/lessons \
  /home/hermes/Documents/Codex/2026-10-05/task-7/workflow-generator/tests --tb=short \
  2>&1 | tee "$WORKFLOW_VALIDATION_DIR/pytest-output.log"
result=${PIPESTATUS[0]}
printf "%s\n" "$result" > "$WORKFLOW_VALIDATION_DIR/pytest-exit.txt"
exit "$result"'
```

Private full-run evidence: `/home/hermes/workflow-validation-scratch/v-zSwrWZ`.
No duplicate runner was started. Final implementation remains unchanged during
validation; subsequent updates are status/evidence documentation only.

## Independent review

Separate Standards and Spec agents reviewed fixed diff `8da7b15...7a19158` using
the code-review skill. Both initial turns failed due to model capacity; retrying the
same reviewers without model substitution completed. Both reported **zero findings**.
Reviews were read-only and made no independent test-run claim. Status/evidence
updates occur after that reviewed implementation; no personal Adam acceptance.

## Remaining release boundary

Actual channel/exact recipient or endpoint and existing authorized mechanism are
pending with the parent. Only loopback is supplied. Live acceptance, broader editorial
repair/spend policy, browser integration and attributed measurement remain open.
This session makes no provider/auth call, external send, root merge/reset, gate bypass,
source mutation, credential change or deployment.

## Publication and recovery

Focused implementation push succeeded and remote readback matched
`7a1915874988dbe4b92b63c986c73e683ad4bf4e`. The established original repository-local
credential helper was loaded only into the push/readback process using ticket37's
non-secret loader. No values were displayed, tokens read or credential settings
persisted. Documentation follow-up uses the same process and is verified in the
final handoff.

Five combined status files remain uncommitted and separate from focused commits.
The cumulative 35–39 status patch excludes the original inherited five-file edits.
Its reconstructed baseline matched all five current original-root files and
applying it in a temporary baseline reproduced every successor status file exactly.
The predecessor `../ticket38-status.patch` is byte-identical to its source.
Recovery: `../ticket39.bundle` and `../ticket39-status.patch`; final artifact checks
and publication state are recorded in [HANDOFF.md](../HANDOFF.md).
