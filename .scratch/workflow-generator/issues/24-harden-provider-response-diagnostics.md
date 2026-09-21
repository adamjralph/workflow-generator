# 24: Harden provider headers and sanitized failure diagnostics

Type: task
Status: resolved

## Approved scope

Adam authorized fixing Codex and Vertex header compatibility and adding allowlisted failure-stage diagnostics after the first live smoke failed with `invalid_response`. The precise live cause remains unknown; repeated Set-Cookie rejection was independently reproduced offline, not confirmed from the live response.

Baseline: `3c18b5d5b84a45527657063953f7d3d1a72f7def`.

Approved test seams: public adapter `invoke()` with synthetic HTTP responses, durable run receipts and real HTTP/browser results, and existing offline replay compatibility. No private parser-only tests. Preserve one attempt per role, no retries/fallback, bounds, sanitized evidence and read-only Hermes/source behavior. No live calls or real credential reads are authorized by this task.

## Acceptance criteria

- Accept legitimate repeated non-framing response headers, including Set-Cookie; do not persist or return their values.
- Continue rejecting duplicate singleton/framing/security-sensitive headers, ambiguous Content-Length/Transfer-Encoding, malformed header syntax, unsupported content types/encodings, and invalid framing.
- Surface fixed allowlisted diagnostics distinguishing request validation, HTTP headers, HTTP body framing, OAuth response validation and model response validation. Preserve existing failure categories for credentials, provider rejection, bounds and uncertainty.
- Persist and display these sanitized codes through existing run receipts and HTTP/browser results without leaking provider text, cookies or credentials. Legacy recordings and completed-pair offline replay remain compatible.
- Red-first regressions at the approved seams, regular typechecking, full offline regression including Chromium, and independent Standards/Spec reviews.

## Boundaries

No raw response capture, logging of arbitrary exception text, automatic repair, retries, additional live smoke, parent-19 closure or publication. Preserve unrelated working-tree changes.

## Answer

Accepted and closed: Adam explicitly accepted ticket 24 ("accept"). Delivery record:
[provider response compatibility and diagnostics](../../../docs/designer-ticket24.md).

Final offline suite: **1,654 passed, 3 expected skips**, including real Chromium.
Mypy: **35 source files clean**. JavaScript syntax, whitespace checks and Graft
refresh complete. Independent Standards: 0 hard violations, initial optional
shared-policy duplication addressed. Independent Spec: 0 outstanding actionable
findings after red-first fixes for additional repeatable metadata and malformed
chunk extensions/trailers; final reviewer independently reran all 100 new adapter
cases. Five new HTTP and five new browser cases cover sanitized diagnostic
persistence and display. Existing completed-pair replay tests remain passing.

No live calls or real credential reads occurred in this implementation. The first
smoke's actual cause and live workflow availability remain unverified. Parent 19
is still open. Ticket-24 implementation and acceptance are recorded together;
unrelated work is preserved. Acceptance does not authorize another live smoke.
