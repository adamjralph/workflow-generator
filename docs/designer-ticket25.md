# Ticket 25 — offline response-header diagnostics

Implementation of [ticket 25](../.scratch/workflow-generator/issues/25-classify-response-header-failures.md).
Adam approved scope, public test seams and review baseline
`31d408b8fa7b0535c91734b3d5b8a8ff6c55ce21`. Adam explicitly accepted ticket 25
("1. Accept"); it is closed. Ticket 24 remains accepted and parent 19 remains open.

## Behavior

Codex and Vertex now distinguish five fixed diagnostic codes:

- `invalid_http_status`: invalid or non-ASCII HTTP status line under existing rules.
- `invalid_http_header`: invalid header syntax, including non-ASCII bytes.
- `duplicate_http_header`: repeated field outside the existing metadata allowlist.
- `unsupported_http_content_type`: missing or unsupported content type.
- `unsupported_http_content_encoding`: unsupported content encoding.

Vertex uses these classifications for both OAuth and generation. Status is parsed
before individual header decoding, so malformed header bytes retain the parsed
provider status. Malformed status lines do not fabricate a provider status. The
first failing validation determines the classification; no rejected field name or
value is retained. Fixed messages and worker-boundary sanitization exclude raw
headers, cookies, credentials, provider bodies and arbitrary exception text.

The existing acceptance predicates, metadata allowlist, framing rules, size/time
bounds, call limits and retry behavior are unchanged. Historical
`invalid_http_headers` and other prior codes remain valid. New codes pass through
the existing failure schema, exchange, receipt, HTTP and browser surfaces without
receipt/version changes. Failed runs remain ineligible for completed-pair Check.

## Verification

Red-first adapter cycles produced **36 failures** for header-rule distinctions,
then **30 failures** for status/content-type/content-encoding distinctions. Public
HTTP receipt tests then produced **5 failures** until the failure-schema allowlist
was extended. Logs: `/tmp/ticket25-red-headers.txt`,
`/tmp/ticket25-red-representation.txt`, `/tmp/ticket25-red-receipts.txt`.

- Header/diagnostic adapter file: **148 passed**, including repeated metadata,
  malformed fields, chunk/trailer framing, and all three provider phases.
- HTTP and real Chromium review surfaces: **40 passed**, including historical and
  new diagnostic codes, sanitized display and duplicate retrieval.
- New wire-to-receipt integration: **15 passed**. Actual public adapters over
  synthetic HTTP bytes feed public HTTP runs; failures survive exchange/receipt
  storage and duplicate retrieval. Offline Check rejects those failed runs with
  provider connections denied. Fixture source/credential bytes and existing
  evidence remain unchanged; Generator failures do not invoke Guardian.
- Final full offline suite: **1,727 passed, 3 expected skips**, including real
  Chromium and completed-pair offline replay regressions. Console:
  `/tmp/workflow-ticket25-full-suite-final.txt`.
- Mypy: **35 source files clean** (`/tmp/ticket25-mypy-final.txt`). JavaScript syntax
  and whitespace checks pass. Graft refreshed. No production changes followed the
  final regression.

The three skips are two opt-in live Jev checks and the optional real Hermes plugin
loader check. Tests used synthetic credentials only. No production capture, real
credential-content read, live model/auth request, smoke retry/resume, publication
or source/Hermes write occurred.

## Standards

Independent review: **0 hard violations**, **1 optional duplication heuristic**.
The adapters retain mirrored classification progression. A shared parser extraction
was suggested but deferred: this bounded diagnostic change preserves existing
transport ownership and validates both copies through the same public test matrix.
Report: `/tmp/ticket25-standards.md`. Review was static; the reviewer did not run tests.

## Spec

Independent review: **0 implementation findings**. It confirmed fixed categories,
status retention, unchanged strict policy, sanitized failures, historical
compatibility and public seams. Report: `/tmp/ticket25-spec.md`. Review was static;
full-suite/typecheck evidence above was executed by the implementation agent after
review, not independently by the reviewers.

## Limits and next decision

These changes do not identify the rule rejected in either historical live smoke;
those stores contain no raw headers to recover it. After acceptance, Adam separately
authorized one fresh live smoke at `/home/hermes/workflow-evidence/live-smoke-03`,
with no retries. Its result belongs in that private destination. This does not
authorize further attempts, parent-19 acceptance or publication.
