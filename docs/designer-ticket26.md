# Ticket 26 — response media-type compatibility and diagnostics

Implemented against approved baseline `1e5e8e8b57289fbbd56e7624ca78142693473886`.
Contract: [ticket 26](../.scratch/workflow-generator/issues/26-normalize-response-media-types.md).
Adam explicitly accepted ticket 26 ("accept"); it is closed.
Ticket 25 remains accepted and parent 19 remains open.

## Behavior

Codex generation, Vertex generation and Vertex OAuth now compare their expected
media types case-insensitively, after the existing trimming and extraction before
`;`. Codex still requires `text/event-stream`; Vertex still requires
`application/json`. No format fallback or content sniffing was added.

Two additive fixed diagnostics distinguish `missing_http_content_type` (no field)
and `empty_http_content_type` (a present, entirely whitespace-trimmed empty value).
Other mismatches, including parameter-only values, retain
`unsupported_http_content_type`. Parsed provider status and validation ordering
are preserved. Raw headers, credentials, cookies, bodies and exception text are
not exposed as diagnostics.

Parameter handling is deliberately unchanged: everything after the first semicolon
is ignored, including malformed parameters or unterminated quotes. This is not a
new full MIME grammar validator. Historical codes and messages remain valid;
receipt identities/versions, replay behavior, framing, encoding, deadlines, size
limits and retry policy are unchanged.

## Verification

Red-first public seams:

- Six case-variant adapter failures, then green after normalized comparisons:
  `/tmp/ticket26-red-case.txt`.
- Nine missing/empty adapter failures, then green after fixed classifications:
  `/tmp/ticket26-red-absent.txt`.
- Six wire-to-receipt failures, then green after extending the failure schema:
  `/tmp/ticket26-red-receipts.txt`.

Additional characterization covers all three provider phases, canonical and mixed
case types, surrounding whitespace, existing parameter forms, malformed ignored
parameters, absent/empty/parameter-only/wrong/comma-separated/internally spaced
values, validation precedence, sanitized output and unchanged synthetic credentials.
Public HTTP tests cover immutable exchanges/receipts, duplicate retrieval without
resending, retained Generator output, Guardian suppression and network-denying
failed-recording Check. Shared diagnostic cases also exercise real Chromium.

- Final full offline regression: **1,836 passed, 3 expected skips**, including real
  Chromium and completed-pair offline replay. Console:
  `/tmp/workflow-ticket26-full-suite-final.txt`.
- Mypy: **35 source files clean**, checked during implementation and at the end.
  Final console: `/tmp/ticket26-mypy-final.txt`.
- JavaScript syntax and whitespace checks passed. Graft refreshed.
- No production or test changes followed the final full regression.

The expected skips are the two opt-in live Jev checks and optional real Hermes
plugin-loader check. Tests used synthetic credentials only. No real credential
reads, production captures, live provider/auth calls, retries/resumes, credential
repair, publication or source/Hermes writes occurred. All smoke stores and consumed
execution guards remain untouched.

## Standards

Independent review: **0 documented violations; 1 optional low-priority duplication
heuristic**. The mirrored content-type classification remains in each provider's
existing transport. Extraction is deferred: the change is small, both copies share
public coverage, and broader refactoring is unnecessary for this bounded fix.
Report: `/tmp/ticket26-standards.md`. This review was static.

## Spec

Independent review: **0 findings or scope creep**. The reviewer independently ran
**291 targeted tests** (response headers, wire-to-receipt diagnostics and HTTP
review tests). Chromium, full regression and typechecking were run by the main
implementation agent, not independently by this reviewer.
Report: `/tmp/ticket26-spec.md`.

## Limits and next decision

The offline compatibility defect does not establish the cause of any prior smoke
failure. Smoke 03's exact response content type was never retained. No live
availability or editorial-quality claim follows from these tests.

Acceptance does not authorize live execution. A future live observation requires separate
explicit permission, a new private destination and an agreed secret-safe observation
contract. No retry or new smoke is authorized by implementation or acceptance.
