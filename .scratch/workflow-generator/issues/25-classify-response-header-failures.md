# Ticket 25 — classify response-header failures offline

Type: task
Status: resolved
Parent: 19

## Approved contract

Adam approved this scope, public test seams and review baseline
`31d408b8fa7b0535c91734b3d5b8a8ff6c55ce21` with "approve".

- Add fixed failure codes distinguishing malformed HTTP status, malformed header,
  rejected duplicate header, unsupported content type and unsupported content encoding.
- Apply the diagnostics to Codex and Vertex (generation and OAuth). Preserve the
  existing strict acceptance rules, response limits, deadlines and no-retry behavior.
- Never expose raw header names/values, cookies, credentials, response bodies or
  arbitrary exception text. Retain parsed provider status when available.
- Preserve historical codes, receipt identities/versions and offline replay compatibility.
- Test through public adapters using synthetic HTTP, receipts, HTTP/browser and
  offline replay. Retain independent Standards and Spec reviews, typechecking and
  final full offline regression.
- No live/model/auth calls, real credential reads, retries/resumes, credential repair,
  source writes or publication. Existing smoke stores remain unchanged. Their exact
  rejected header rule cannot be recovered from existing evidence.

## Implementation categories

`invalid_http_status`, `invalid_http_header`, `duplicate_http_header`,
`unsupported_http_content_type`, `unsupported_http_content_encoding`.
Historical `invalid_http_headers` remains accepted for old records and injected failures.
This changes diagnostics only, not header compatibility policy or parent-19 acceptance.

## Comments

Implementation approval does not constitute ticket acceptance or live-smoke authorization.

## Answer

Implemented, explicitly accepted by Adam ("1. Accept"), and closed. Delivery and verification:
[docs/designer-ticket25.md](../../../docs/designer-ticket25.md).
Final offline suite: 1,727 passed, 3 expected skips; mypy 35 source files clean.
Independent Standards: 0 hard violations, 1 deferred optional duplication heuristic.
Independent Spec: 0 implementation findings. Both reviews were static.
No live calls or real credential reads occurred during implementation. Parent 19 remains open.

Adam separately authorized one fresh live smoke at
`/home/hermes/workflow-evidence/live-smoke-03`, with no retries. That authorization
is separate from this ticket's acceptance; the smoke result will be recorded in
its private destination.
