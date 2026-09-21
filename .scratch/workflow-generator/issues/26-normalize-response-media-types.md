# Ticket 26 — normalize response media types and distinguish absent values

Type: task
Status: resolved
Parent: 19

## Authorization

Adam approved the offline investigation and scoping, then explicitly approved
this implementation contract, public regression seams and review baseline
("Approve"). Ticket 25 remains accepted and closed. Parent 19 remains open.

Approved fixed review baseline: `1e5e8e8b57289fbbd56e7624ca78142693473886`.

## Investigation evidence

At that baseline, 48 synthetic public-adapter cases exercised Codex generation,
Vertex generation and Vertex OAuth. Real socket connections and DNS resolution
were denied; credentials were synthetic and unchanged. All three phases reject
mixed/uppercase variants of their expected media type. HTTP media type and subtype
names are case-insensitive (RFC 9110, section 8.3.1).

Existing response-header tests also passed: 148 passed. Local investigation
artifacts: `/tmp/workflow-content-type-investigation.py`,
`/tmp/workflow-content-type-investigation.json`, and
`/tmp/workflow-content-type-existing-tests.txt`.

These results do not establish the cause of any live smoke failure. Smoke 03
retained no exact content-type value. No real credentials or live calls were used.

## Approved implementation contract

- Compare the existing extracted media type case-insensitively: Codex expects
  `text/event-stream`; Vertex generation and OAuth expect `application/json`.
  Preserve existing trimming and extraction before the first semicolon.
- Add fixed `missing_http_content_type` for an absent Content-Type field and
  `empty_http_content_type` for a present field whose entire value is empty after
  existing whitespace trimming. Keep `unsupported_http_content_type` for every
  other mismatch, including a parameter-only value such as `; charset=utf-8`.
- Preserve validation ordering: status and header syntax/duplicates precede
  content-type checks, which precede content-encoding and framing checks.
- Preserve parsed provider status and fixed secret-safe messages. Never persist
  or expose raw field names/values, cookies, credentials, response bodies or
  arbitrary exception text as diagnostics.
- Retain historical diagnostic codes, receipt versions, identities and replay
  compatibility. Failed runs remain ineligible for completed-pair Check.
- Preserve response limits, deadlines, framing, encoding, metadata policy,
  duplicate-header rejection and no-retry behavior.

## Explicitly unchanged parameter policy

Parameters remain ignored after the first semicolon, as they are today. This
includes malformed parameters and unterminated parameter quotes. This ticket does
not claim full MIME grammar validation. Tightening parameter syntax is a separate
policy decision, not bundled into this compatibility correction.

No JSON fallback for Codex, content sniffing, missing-type fallback or acceptance
of arbitrary media types is permitted.

## Public regression seams and acceptance evidence

1. Red-first public `CodexSource.invoke` and `VertexSource.invoke` tests with
   synthetic HTTP bytes and credentials; cover all three provider phases.
   Accept mixed/uppercase expected media types, canonical types, whitespace and
   existing parameter forms. Reject absent, empty, parameter-only, wrong,
   comma-separated and internally spaced types with the specified categories.
   Preserve duplicate/syntax precedence, status, sanitization, call counts and
   unchanged credential bytes. Characterize unchanged parameter handling.
2. Wire-to-receipt tests through public adapters and HTTP runs for the new codes;
   retain stored exchange/receipt identity, duplicate retrieval without another
   call, Guardian suppression after Generator failure and valid Generator output
   after Guardian failure. No raw diagnostic values may escape.
3. HTTP and real Chromium tests for sanitized diagnostic display, historical-code
   compatibility and existing stale-response behavior.
4. Network-denying offline Check rejection for failed recordings, plus existing
   completed-pair replay regressions without credential loading or live fallback.
5. One implementation agent; independent Standards and Spec reviewers against the
   fixed baseline; regular mypy checks; final full offline regression, JavaScript
   syntax and whitespace checks. Refresh Graft after implementation.

## Boundaries

No live model/auth requests, real credential-content reads, retries/resumes,
credential repair, production captures, publication or source/Hermes writes.
Preserve all three smoke stores and their consumed execution guards. Any future
live observation needs separate explicit permission, a new private destination
and an agreed secret-safe observation contract.

Preserve unrelated working-tree changes. Ticket acceptance and parent-19 closure
remain separate decisions.

## Answer

Implemented, explicitly accepted by Adam ("accept"), and closed.
Delivery: [docs/designer-ticket26.md](../../../docs/designer-ticket26.md).
Final full offline suite: 1,836 passed, 3 expected skips, including real Chromium
and offline replay. Mypy: 35 source files clean; JavaScript syntax and whitespace
checks passed; Graft refreshed. No production/test changes followed regression.

Independent Standards: 0 documented violations, 1 optional duplication heuristic
deferred. Independent Spec: 0 findings; reviewer independently ran 291 targeted
tests. No live calls, real credential reads or smoke-store changes occurred.
