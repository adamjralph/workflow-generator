# Ticket39 — explicit delivery adapter and inspectable attempt receipt

Type: task
Status: resolved — technically complete; no personal Adam acceptance

## Scope and authorization

Delegated continuing-development instruction authorizes one local successor to
verified ticket38 (`8da7b153743de67fb5aadc7e37763675ebfc6741`). Actual destination
and mechanism remain pending with the parent. No provider call or external send.

## Acceptance

- Reuse ticket38's concrete redacted envelope and policy/human-gate behavior.
- One explicit trusted adapter receives only payload bytes, fresh local attempt
  identity and bounded timeout; only loopback transport is implemented here.
  Adapters must perform one bounded attempt without retry/fallback/redirect.
- Reserve before adapter invocation. Re-entry cannot resend, including exceptions,
  interruptions, missing receipt and switching adapters. Successful/remedied results
  are suppressed without calling the adapter.
- Acknowledgement means transport receipt, never human reading or acceptance.
  Explicit rejection and unknown completion remain distinct; exceptions/timeout
  cannot establish success. No endpoint, secret exception or response body in audit.
- Read-only audit distinguishes unattempted, reserved without final receipt, and
  completed; validate remedy/reservation/receipt identity and digest links.
- Ticket38 accepts either its existing endpoint or one adapter, rejecting both
  before replay. Both drivers preserve attribution redaction and human decision.
- Deterministic loopback tests, typing, independent review, complete final-code
  suite exit 0, focused commit/push/readback, cumulative status patch and handoff.

## Result

Implemented the existing redacted envelope through one explicit trusted adapter,
reservation-before-invocation, separate acknowledged/rejected/unknown completion,
and read-only saved-attempt inspection. Ticket38 accepts either adapter or endpoint
and preserves attribution redaction and the human gate through both drivers.
202 focused tests passed; typing 49 files clean; independent Standards/Spec reviews
clear; complete final-code regression 2,601 passed, 3 expected skips, exit 0 on
2026-10-05. [Commands and evidence](../../../docs/outcome-ticket39.md).
No provider/auth calls or external sends.

**Still missing:** actual authorized destination/adapter, live acceptance, browser
integration and attributed measurement. This local contract settles none of those.
