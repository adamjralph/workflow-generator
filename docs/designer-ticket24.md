# Ticket 24 — provider response compatibility and diagnostics

Implementation of [ticket 24](../.scratch/workflow-generator/issues/24-harden-provider-response-diagnostics.md).
Adam approved implementation and adapter/receipt/HTTP/browser test seams against
`3c18b5d5b84a45527657063953f7d3d1a72f7def`.
**Accepted and closed:** Adam explicitly accepted ticket 24 ("accept").

## Behavior

Both default adapters accept repeated `Set-Cookie`, `Cache-Control`, `Vary`,
`Warning`, `Link`, `Server-Timing`, `Via`, `Allow`, `Accept-Ranges`,
`Content-Language`, `Pragma`, `Accept-Patch`, `Accept-Post`, `Alt-Svc` and
`Preference-Applied` headers. These unused values are discarded,
not combined, persisted or exposed. Other repeated fields remain rejected,
including framing fields and singleton/security-sensitive headers. Header names
must be HTTP tokens, values cannot contain forbidden control characters, and
obsolete folded fields are rejected. Duplicate detection is case-insensitive.

Content type/encoding and framing remain strict. Transfer-Encoding with
Content-Length is rejected, as are empty/unsupported transfer encodings,
non-decimal lengths, invalid chunk sizes, malformed extensions and invalid chunk
terminators. Trailer fields use the same syntax checks and are restricted to
`Server-Timing`, `Digest`, `Content-Digest`, `Repr-Digest` and `ETag`; only
`Server-Timing` may repeat. Framing/authentication/routing trailers are rejected,
never allowed to override response headers. Shared syntax/policy helpers prevent
Codex/Vertex drift while each adapter retains transport and deadline ownership. Existing
response-size/deadline bounds and incomplete-exchange uncertainty remain in force.

New fixed failure codes distinguish `invalid_request`, `invalid_http_headers`,
`invalid_http_framing`, `invalid_auth_response` (Vertex) and
`invalid_response_body`. They carry no raw headers, cookies, SSE event names,
provider error bodies or arbitrary exception text. A valid HTTP status is retained
for header/framing validation failures; body validation does not fabricate one for
injected transports. Credential, provider rejection, response-limit, timeout and
transport-uncertainty categories are unchanged. `invalid_response` remains valid
for historical records and unclassified injected-transport failures.

Codes flow through existing exchange/receipt identities and the HTTP/browser
failure display. There is no new public schema field, receipt version, model
operation version or replay behavior. Completed-pair Check remains offline and
failed runs remain ineligible. No retries, fallback, credential repair, source
writes or publication are added.

## Verification

Red-first cycles reproduced repeated-cookie rejection in Codex, Vertex generation
and Vertex OAuth; absent header/framing classifications and malformed header
acceptance; rejection of other repeatable metadata and acceptance of empty transfer
encoding; missing body/request/OAuth distinctions; and loss of new codes at the
run-receipt boundary. One initial receipt fixture had a synthetic provider instead
of Vertex and failed preflight; it was corrected, then the receipt red/green cycle
was rerun against the actual failure-code boundary.

Focused adapters, HTTP, real Chromium and completed-pair replay: **323 passed**.
Initial full regression: **1,605 passed, 3 expected skips**. Initial independent
Standards review found no hard violations and one optional duplicated-policy
heuristic. Initial Spec review found two gaps: additional repeatable metadata
(`Via`) and malformed chunk extensions/trailers. Both were reproduced red-first
(29 failures), then fixed with a shared syntax/policy helper. Post-fix adapter tests:
**252 passed**. The next full regression passed **1,636 tests, 3 expected skips**;
Standards follow-up had no findings. Spec follow-up found one remaining repeatable
metadata gap (`Content-Language`). A further red-first cycle covered that and
additional standard list-valued metadata (18 failures before the policy update).
All **100** header/diagnostic regression cases now pass. Tests use synthetic
credentials and HTTP bytes, never production credentials.

Final full regression after all fixes: **1,654 passed, 3 expected skips**, including
real Chromium. Console: `/tmp/workflow-ticket24-full-suite-final.txt`. Mypy:
**35 source files clean**; JavaScript syntax and whitespace checks pass; Graft
refreshed. No production changes followed these tests.

## Standards

Independent initial and follow-up review: **0 hard violations**. The initial optional
header-policy duplication finding was addressed by the shared helper; follow-up
found no actionable optional smells. The final metadata allowlist extension followed
that Standards review and was covered by the final Spec follow-up and regression.
Reports: `/tmp/ticket24-standards.md`, `/tmp/ticket24-standards-final.md`.

## Spec

Independent review identified the repeatable metadata and chunk/trailer gaps above;
each was reproduced red-first and fixed. Final focused follow-up: **0 remaining
actionable findings**, independently rerunning all **100** new adapter cases.
Earlier independent review also ran HTTP/Chromium tests. Final report:
`/tmp/ticket24-spec-closure.md`. The last follow-up reviewed the final delta, not a
fresh full-diff audit.

**Review summary:** Standards 0 hard / 0 outstanding actionable heuristics;
Spec 0 outstanding actionable findings. Adam explicitly accepted this slice;
implementation and acceptance are recorded together. Parent 19 remains open,
and another live smoke requires separate authorization.

## Live-smoke boundary

Repeated-header rejection is a reproduced compatibility defect, **not a confirmed
explanation of the first live smoke**: its sanitized evidence lacks the response
headers/body and failure-stage detail. This change does not rerun that request or
establish provider availability or writing quality. A further live smoke needs
fresh authorization; parent 19 remains open.
