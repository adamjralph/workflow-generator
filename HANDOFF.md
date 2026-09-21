# Workflow Generator — next-session handoff

## Token-efficiency requirements — apply from ticket 23 onward

Adam requested these after reviewing ticket-22 token consumption:

- **Use one implementation agent.** The main agent implements; do not routinely
  spawn separate implementation or research agents. Ask before adding delegation
  beyond the two required independent reviewers.
- **Retain independent Standards and Spec reviews.** Token savings must not remove
  these reviews, agreed test seams, regular typechecking or final full regression.
- **Keep exploration narrow.** Consult Graft first as required, using literal
  identifiers and focused questions. Prefer skeletons and exact relevant spans;
  avoid broad queries, whole-file dumps and repeatedly retrieving the same code.
  If ranking misses a known document, open that document directly rather than
  repeatedly querying unrelated source nodes.
- **Reuse context already read.** Do not reload large contracts, domain documents
  or skills unless a required detail is missing or the file changed. Give reviewers
  the fixed baseline, relevant paths and a concise task rather than unnecessary
  copies of the entire implementation conversation.
- **Bound command output.** Save long test/build logs to files; bring summaries and
  relevant failure excerpts into context. Run focused tests during implementation
  and the full suite at the end; rerun after fixes when needed for valid evidence.
- **Report actual usage honestly.** Graft's “tokens saved” figures are hypothetical
  whole-file comparison estimates, not metered usage or billed savings. Do not sum
  repeated-query/subagent estimates or publish them as an actual savings total.
  Omit routine savings footers. Use measured usage if available; otherwise state
  that actual consumption or its breakdown is unknown. Do not invent percentages.

These requirements reduce redundant context and delegation, not implementation
scope, safety checks or acceptance evidence.

## Latest handoff — parallel-wave D1 contract drafted and reviewed; Adam will approve P13 next session

Adam selected planning-map item **P13** (one complete parallel wave) and asked for a
draft of the **D1 parallel-wave contract** plus a proposed ADR, so that P13 and the
items it unblocks (P14-P16, P18, P27) can later be published as implementable
tickets. This session produced documents only: **no code, no tests, no live calls,
no Hermes changes, no staging and no commits.** Baseline remains
`00807380b120f343780b26f697843dacfe054066`.

**Deliverables** (both untracked):

- `docs/parallel-wave-contract.md` — 410 lines, sha256
  `5d18c51f30c434e85d5e13ccbf70dfb3838e598baaa254f476200960797c6485`. Header states
  `Status: proposed, awaiting Adam's decision. No implementation is authorized`.
- `docs/adr/0011-parallel-waves-are-declared-order-deterministic.md` — 95 lines,
  sha256 `0347caf62e937566259dcc288e09419d98e04bc28042bd2542aecd9e8e2e7115`. Front
  matter `status: proposed`, in the shape of ADR 0010.

**Adam's next action is to approve P13.** He said so explicitly at the end of the
session; the handoff exists so approval can happen in a fresh session. On approval,
publish P13 as a ticket from the contract (and the same decisions unblock P14-P16,
P18 and P27), or apply whatever he overrides. Do not publish, commit or stage
anything before that approval. He may also ask for a pointer line to the contract in
`.scratch/workflow-generator/map.md`; that file is his planning document, so leave it
untouched unless asked.

**D1 items the contract now decides** (contract §2, six rows, all with rejected
alternatives recorded):

1. Concurrency: branch work stays synchronous, dispatched per branch step with
   `asyncio.to_thread` (precedent `lessons/lesson_02_workflow/test_parallel.py`),
   bounded by a `wave_concurrency` run parameter declared beside `bindings`, default
   `min(branch_count, 4)`, range 1-16, rejected before work when out of range, not
   part of the compared artefact. The reference driver stays sequential.
2. Admission and refusal: granularity stays one step, but a wave is admitted only
   if the remaining budget covers a static worst case (branch-region node count plus
   one for the join); refusal happens once at dispatch with `FAILED_BUDGET` and detail
   `wave_budget_refused`, before any branch step or model call, so mid-wave denial is
   impossible.
3. Reducer cost: the join is a framework join whose accumulation machinery is a
   private item collector; the caller reducer is invoked once from the join node's
   single step, charged one reserved step on the success **and** the failure path.
4. Failure: complete-all-then-select, no sibling cancellation (`cancel_sibling_tasks`
   and `ReduceFirstValue` are never used); each branch converges on the join carrying
   result or failure; the wave fails closed on the first failing branch in declared
   order, terminates at that branch's terminal with the fork-entry state, and does not
   invoke the reducer.
5. Evidence: logs append durably at completion (mechanics unchanged); the compared
   artefact is a canonical projection (branch events grouped in declared order between
   the fork-dispatch and join run-level events, join boundary record on both paths,
   per-event spend normalised to each step's own reservation). Raw interleaving and
   within-wave sequence numbers are recorded and explicitly non-normative. This amends
   the "identical events and digests" rule of ADR 0008, ADR 0001 and CONTEXT §§9.2/11.2
   for wave cases only.
6. Branch regions are pairwise disjoint, as a decision: otherwise events cannot be
   attributed to a branch and the worst case doubles-counts.

The contract also settles the join contract (a `TransformNode` whose binding comes
from a new caller-supplied `reducers` mapping keyed by join id — authoritative for
joins, while `operation` stays a required spec field and the binding key for every
other Transform, and `unbound_reference` must not fire for a join), branch-scoped
state seeded from a detached snapshot, the new admission findings, and the public
test seam (13 cases).

**Still open for Adam:** the P14 loop multiplier direction (whether the `exhausted`
visit counts as the `(max_iterations+1)`th), the exact `wave_concurrency` cap inside
1-16, and the D2 identity/approval question.

**Review status: closed on the frozen hashes.** Two independent reviews were run
(Standards and Spec) plus targeted verification passes. Standards reported 11
findings, Spec 15 findings, with further should-fix items and nits; every item was
applied and both reviewers confirmed on the exact hashes above that nothing remains
open. They caught two real gaps, not style: the failure path left the join step
uncharged and the two drivers disagreed on a failed wave's event set, and the join
binding key collided with the existing `unbound_reference` check. Reviewer agents are
idle and messageable as `WaveStandardsReview` and `WaveSpecReview` (`history://` and
`agent://` handles), should Adam want a further targeted pass.

**Working-tree care.** This session added only the two untracked documents above;
unrelated modified and untracked files from earlier sessions are untouched. Preserve
them, do not use `git add -A`, and do not commit the two documents unless Adam asks.
All five live authorizations remain consumed; any new live activity needs fresh
explicit permission and a new private destination. The token-efficiency rules at the
top of this file still apply: the main agent implements, the two independent reviews
are retained, and no completion percentage or token-saving total is invented.

## Previous handoff — offline transport investigation completed; no drop-in replacement

Adam approved the bounded offline investigation with “yes”. Report:
`docs/designer-offline-transport-investigation.md`. Baseline remains
`00807380b120f343780b26f697843dacfe054066`; production code, existing tests and
project dependencies are unchanged. Ticket 27 remains closed; parent 19 stays open.

Static inspection compared the installed Hermes auxiliary Codex construction path
and HTTPX configuration without importing or executing Hermes. Copied third-party
HTTPX 0.28.1/httpcore 1.0.9/h11 0.16.0 packages powered a throwaway loopback prototype.
Private temporary artifacts: `/tmp/workflow-transport-study/` (probe, results, logs,
synthetic TLS certificates and copied libraries). No real credential content was
read and no external request or smoke-store write occurred.

**52 loopback TLS observations plus one refused-connection check passed their
characterization assertions.** Explicit safe defaults preserve the exercised MIME,
body-size, elapsed-time, TLS-verification, proxy, redirect and retry boundaries.
However, the HTTPX response seam changes first-section handling, collapses equal
Content-Length duplicates, hides trailers, accepts a header over the existing limit
and accepts LF-only delimiters. It cannot reconstruct ticket 27's exact raw-header
observations. Both transports reject the synthetic 35-field missing-MIME response;
ALPN is still only an observed difference, not a demonstrated live cause or fix.

Recommendation: **do not implement a plain HTTPX streaming replacement** under the
current contract. Any further proposal must resolve the raw-byte validation and
evidence seam without weakening approved guarantees. That design/implementation is
not approved by this investigation. No additional live retry or diagnostics ticket
is recommended on this evidence alone.

Independent static Standards follow-up: 0 violations. Independent static Spec
follow-up: 0 blocking deviations; optional stronger payload/code assertions remain.
Reviewer suggestions about proxy controls, outcome assertions, genuine compressed
fixtures and refused connections were addressed and the probe rerun successfully.
Mypy: 35 source files clean. Final full offline regression: **1,892 passed,
3 expected skips**, including Chromium and completed-pair replay, in 377.12 seconds.
Console: `/tmp/workflow-transport-study/regression.log`. Whitespace checks pass.
No production or existing test changes occurred.

Next session: read the new report, then discuss whether to scope a lower-level
transport/evidence-boundary design. Do not treat this as implementation permission.
All five live authorizations remain consumed; any new live activity requires fresh
explicit permission and a new private destination. Preserve prior evidence/guards,
unrelated edits and uncommitted reports. No staging or commit occurred.

## Previous handoff — discuss an offline transport investigation before proceeding

After smoke 05, Adam asked what to do next. The recommendation was to stop live
retries and investigate offline whether a maintained HTTP client should replace
the hand-written transport. Adam then requested this handoff; **he has not approved
the investigation, a transport replacement, new diagnostics or another live test**.
The custom transport is a hypothesis, not an established culprit.

### Start next session here

1. Read `docs/designer-ticket27.md`, the corrected
   `docs/designer-codex-200-no-content-type-investigation.md`, and
   `/home/hermes/workflow-evidence/live-smoke-05/SMOKE.md`. Do not dump private
   captures, requests, headers or credentials into context. Ticket 27 is accepted
   and closed at `00807380b120f343780b26f697843dacfe054066`; parent 19 remains open.
2. Discuss and obtain approval for a bounded **offline** investigation: narrowly
   compare the adapter with Hermes's installed Codex client configuration, then
   evaluate a maintained HTTP client against synthetic responses and loopback TLS.
   No broad home-directory searches, Hermes runtime invocation, real credential
   loading or external requests. Agree test seams and any prototype scope first.
3. Preserve truthful client identity, strict MIME validation, bounded elapsed time/
   response size, no redirects/retries/fallback, credential read-only boundaries
   and durable execution evidence. Check client defaults explicitly; do not assume
   a library preserves these properties. Do not impersonate Hermes. ALPN remains
   an observed configuration difference, not a demonstrated cause or remedy.
4. Produce evidence and a recommendation before proposing production changes.
   A transport replacement requires separate implementation approval. Any eventual
   live test needs separate fresh permission and a new private destination; an A/B
   experiment requires authorization for multiple requests. All five prior live
   permissions are consumed. Preserve their stores and execution guards.
5. Do not start another diagnostics ticket without a specific question it can
   answer. Smoke 05 establishes multiple fields without Content-Type; it does not
   identify a bot challenge, proxy, response author/body, successful generation,
   billing or a second response. Earlier smoke failures are not all equivalent.

### Repository and verification state

Branch `main`, HEAD `0080738`; ticket-27 implementation and acceptance are committed.
Latest recorded full offline suite: **1,892 passed, 3 expected skips**, including
Chromium and completed-pair replay; mypy **35 source files clean**. Independent
Standards: 0 documented violations, 1 optional readability note; Spec: 0 blocking
deviations. These are recorded results, not tests rerun for this handoff.

This handoff update changes documentation only. No investigation, live activity,
credential read, production/test edit, staging or commit occurred during the update.
Preserve unrelated edits, the local handoff/map and uncommitted investigation
reports. No blanket staging, reset or cleanup.

## Previous update — fifth live observation consumed; 35 fields without Content-Type

After accepting ticket 27, Adam approved one fresh live observation at
`/home/hermes/workflow-evidence/live-smoke-05` ("approve"). At commit `0080738`,
Generator failed with **`missing_http_content_type`, HTTP 200**, after about
**1.11 seconds**. New diagnostics report **2,651 first-section bytes, 35 nonempty
field lines**, Content-Type/Content-Length/Content-Encoding absent and
Transfer-Encoding present. Its value was not retained; do not infer chunked
framing or body format. The section was not headerless. Root cause is unresolved.

One reserved generation attempt, zero recorded auth requests, unknown token usage.
No copy, Guardian or completed-pair Check followed. This approval was restricted
to one Generator observation, using the delivered Generator-only path so there
could be no additional Guardian/auth call. Local bookkeeping is version 1 rather
than the previous paired version 2; the exact Codex payload was verified identical
to smoke 04 before execution and from the durable attempt afterwards. Request
headers/client identity/TLS policy were unchanged; no identity impersonation.

Fresh capture selected the same oldest draft, unchanged 14-file guidance and model
selections. New request:
`b14867f76a10efc9d1df46325da503b7dff3c16a676b44dda39583cb6700ffe9`.
Snapshot/receipt digests, persisted observation, source/guidance/profile/config
integrity, one reserved attempt and private permissions verified offline. Private
evidence: `SMOKE.md`, `run-view.json`, `verification.json` in the fifth destination.
Only the authorized Codex adapter read its real credential file. No manual
credential inspection, Vertex credentials, auth repair, protected writes or earlier
smoke-store changes occurred. No production/test edits were made.

### Next session

1. Read the fifth private `SMOKE.md`; ticket 27 remains accepted and closed.
2. All **five** live authorizations are consumed. No retries, new live calls,
   credential reads or auth repair without fresh explicit permission and a new
   private destination. Preserve all stores and guards.
3. Discuss the next bounded investigation with Adam. These observations do not
   identify the response author, body, bot rule, billing or second HTTP response.
   Do not relax MIME checks, sniff bodies or skip response sections.
4. Parent 19 stays open; complete execution and editorial quality are unverified.
   Preserve unrelated edits and local handoff/map. This update is uncommitted;
   no staging or commit occurred during the live observation.

## Previous update — ticket 27 accepted and closed

Adam approved the versioned observation schema, persistence and offline public
adapter/durable-failure seams ("approve"), then explicitly accepted ticket 27
("accept"). Implementation and acceptance are committed as `0080738`, separately
from unrelated changes. Implementation baseline: `6149bcf1a4fbb65a5d2b982c2bc62f8dbda7e974`. Delivery:
`docs/designer-ticket27.md`; contract:
`.scratch/workflow-generator/issues/27-observe-rejected-header-shape.md`.
Ticket 27 is `resolved` and closed. Ticket 26 stays closed;
parent 19 stays open. The earlier requirement to obtain implementation approval
for these diagnostics is superseded; live authorization is still separate.

Codex generation and Vertex generation/OAuth attach optional version-1
`header_observation` to rejected complete, bounded first sections: delimiter-inclusive
byte count, nonempty field-line count before discard, and exact case-insensitive
Content-Type/Content-Length/Transfer-Encoding/Content-Encoding presence flags.
Existing failure code/status remain authoritative. Observations survive public
adapters, failed exchanges, receipt/views and duplicate inspection. Historical
failures omit the new field; receipt/replay versions and request identities remain
unchanged. No additional reads, raw headers, bodies, hashes, credentials or exception
text are retained. Incomplete/oversized sections and post-header failures omit the
observation. Validation order, limits and no-retry policy are unchanged.

Final full offline suite: **1,892 passed, 3 expected skips**, including real Chromium
and completed-pair replay. Console: `/tmp/workflow-ticket27-full-suite-final.txt`.
Mypy: **35 source files clean**; JavaScript syntax and whitespace checks pass;
Graft refreshed. No production/test edits followed the final suite. Independent
Standards: 0 documented violations, 1 optional fixture-readability heuristic
deferred. Independent Spec: 0 blocking deviations; independently ran 47 tests.
Nine suggested boundary cases were subsequently added, and all 56 observation
tests plus the final full suite passed. Red-first evidence is in the delivery.

### Next session

1. Read the ticket-27 delivery; it is accepted and closed. Do not reimplement it.
   Agree any next task or live observation separately with Adam.
2. Root cause remains unresolved. Diagnostics are not a demonstrated remedy, and
   offline success does not establish live availability or editorial quality.
3. All four live authorizations remain consumed. Any live attempt needs fresh
   explicit permission and a new private destination. Keep request identity
   unchanged initially; A/B testing requires separately authorized requests.
4. No real credential-content reads, external provider/auth requests, production
   captures, retries/resumes, protected writes or smoke-store changes occurred.
   Only ticket-27 implementation, tests, issue and delivery are committed.
   Preserve unrelated edits, local handoff/map and earlier uncommitted investigation
   reports; do not blanket stage/reset/clean. Acceptance changed documentation only;
   verification above is recorded evidence, not a new test run.

## Previous update — independent investigation corrected and continued offline

Read `docs/designer-codex-200-no-content-type-investigation.md` first. Its revised
version supersedes the initial independent report and earlier session conclusions
that attributed the response to Cloudflare, treated all prior smokes as equivalent,
claimed a successful SDK control, or eliminated all transport defects. **Root cause
remains unresolved.** Baseline remains `6149bcf`; no production fix was made.

Established: smoke 04's first parsed header section lacked Content-Type and had
status 200. This does not establish zero other fields, an empty body, a second
response, a proxy, a bot rule, or successful generation. Earlier smoke diagnostics
were broader and do not establish the same cause. ALPN differs between the adapter
and inspected httpcore defaults, but is not a demonstrated cause or remedy.

Continuation probe `/tmp/codex-offline-followup.py` passed five transport-only
synthetic cases with real connections/DNS denied and no credentials loaded:
zero fields, multiple fields without Content-Type, and a second block all reproduce
missing-type/200; preceding 103 gives provider_rejected/103; expected mixed-case MIME
is accepted. Captured writes confirmed POST framing and UTF-8 byte Content-Length.
Failing cases performed only one header read and closed the writer. These are not
real-TLS or public-adapter integration tests. The earlier session recorded 268
header/diagnostic tests passing; that suite was not rerun in the continuation.

### Next session: decision needed, not implementation authorization

1. Discuss approval for a minimal versioned observation contract at the existing
   rejection point: first-header-section byte count, field-line count before metadata
   discard, presence booleans for Content-Type/Content-Length/Transfer-Encoding/
   Content-Encoding, plus existing failure code/status. No raw names, values,
   hashes, bodies, credentials, or exception text. Schema and persistence seams
   need explicit approval before implementation.
2. If approved, implement and validate diagnostics offline through public adapter
   and durable-failure seams. Preserve limits, validation order, and no retries.
3. Any live attempt requires separate fresh permission and a new private destination.
   Keep request identity unchanged initially; do not impersonate Hermes. An A/B
   experiment requires multiple separately authorized requests, not one attempt.
4. Do not read beyond the first header section to count delimiters: this changes
   rejection behavior and may inspect body bytes; body delimiters do not prove
   additional HTTP responses. Do not skip arbitrary 200 blocks or relax MIME checks.

All four live authorizations remain consumed. Preserve smoke stores/guards. Ticket
26 stays closed; parent 19 stays open. This continuation touched only the revised
report and temporary synthetic probe, with no external requests or credential reads.
Do not repeat the earlier session's broad home-directory searches or private-record
dumps; their privacy was not independently audited. Preserve unrelated working-tree
changes. Report and handoff edits are uncommitted; no staging or commit was performed.

## Previous update — offline header-block investigation completed

Adam authorized the recommended offline investigation after smoke 04. At baseline
`6149bcf`, 144 synthetic public-adapter cases covered all three provider phases and
whole/one-byte/seven-byte delivery. Network/DNS were denied; synthetic credentials
remained unchanged. Existing response-header tests: 247 passed. No production/test
changes, real credential reads or live calls occurred; smoke stores are unchanged.
Report: `docs/designer-header-block-investigation.md`.

Fragmentation, field-name casing and preceding metadata did not lose Content-Type.
First-header-block parsing is confirmed. Informational 100/103 responses are rejected
instead of advancing to the final response, but with `provider_rejected` and status
100/103, not smoke 04's missing-type/200 signature. Synthetic extra blank lines or
CONNECT-style 200 preambles can reproduce missing-type/200, but this does not prove
they occurred live; adapters use direct TLS POST, not CONNECT. No framing fix is
established as a remedy for smoke 04. Do not skip arbitrary 200 blocks, accept missing
types or sniff bodies based on these results.

Next: discuss an approved bounded secret-safe observation schema before implementing
more diagnostics (possible header-block byte/field counts and fixed framing-presence
booleans, no raw values/names/bodies). This is a recommendation only. Any live run
still requires separate explicit permission and a new private destination. All four
smoke authorizations remain consumed. Ticket 26 stays closed; parent 19 stays open.

## Previous update — fourth live smoke stopped at missing content type

Ticket 26 remains accepted and committed as `6149bcf`. Adam separately authorized
one fresh smoke at `/home/hermes/workflow-evidence/live-smoke-04` ("Authorized").
That authorization is consumed. At `6149bcf`, fresh request
`049eaba17b53cb02f98966d6a4ecd99e1d213d7c044b412590050e53adb5c006`
failed at Generator with **`missing_http_content_type`, provider status 200** after
about 1.29 seconds. One reserved generation attempt, zero recorded auth requests,
unknown usage. No copy, Guardian, completed-pair Check or retry followed.

Fresh capture selected the same oldest draft and unchanged 14-file guidance/default
models. Snapshot/receipt digests, unchanged source/guidance and private permissions
verified. Private evidence: `SMOKE.md`, `run-view.json`, `verification.json` in the
fourth destination. No raw response headers or body were retained. The adapter did
not find a Content-Type field in the header block it parsed; this does not establish
body format, intermediary behavior or the causes of earlier smokes.

### Start next session here

1. Read `/home/hermes/workflow-evidence/live-smoke-04/SMOKE.md`. Ticket 26 is
   accepted and closed; do not reopen its completed implementation.
2. Stop live attempts. Discuss a bounded offline investigation of response-header
   framing/first-block handling before implementation. This is a possible next
   task, not an established diagnosis or approved policy change. Never silently
   accept missing content types or add format fallback on speculation.
3. All four live-smoke authorizations are consumed. No further credential reads,
   provider/auth calls, retries/resumes or auth repair are authorized. Any future
   observation needs fresh permission, a new private destination and an agreed
   secret-safe observation contract. Preserve all stores and execution guards.
4. Parent 19 remains open; complete live execution and editorial quality remain
   unverified. Preserve unrelated edits and local handoff/map; no blanket staging.

Only the separately authorized Codex adapter read real credentials in smoke 04.
No Vertex credential read, publication, source/Hermes write or previous-store
modification occurred. Handoff/map updates are local and uncommitted.

## Previous update — ticket 26 accepted and closed

Adam approved the offline content-type investigation, then the implementation
contract, public regression seams and baseline
`1e5e8e8b57289fbbd56e7624ca78142693473886` ("Approve"). Adam subsequently explicitly
accepted ticket 26 ("accept"); it is resolved and closed. Implementation and
acceptance are committed as `6149bcf`. Delivery: `docs/designer-ticket26.md`; contract:
`.scratch/workflow-generator/issues/26-normalize-response-media-types.md`.

Codex generation, Vertex generation and Vertex OAuth now compare expected media
types case-insensitively and distinguish `missing_http_content_type` from
`empty_http_content_type`. Other mismatches retain `unsupported_http_content_type`.
Existing ignored-parameter behavior, historical codes/messages, validation order,
receipt/replay versions, limits and no-retry policy are unchanged.

Final full offline suite: **1,836 passed, 3 expected skips**, including real
Chromium and completed-pair replay. Console:
`/tmp/workflow-ticket26-full-suite-final.txt`. Mypy: **35 source files clean**;
JavaScript syntax and whitespace checks pass; Graft refreshed. No production/test
changes followed final regression. Independent Standards: 0 documented violations,
1 optional mirrored-parser duplication heuristic deferred. Independent Spec:
0 findings, independently ran 291 targeted tests. See delivery for red-first logs.

### Start next session here

1. Read `docs/designer-ticket26.md` and ticket 26. Ticket 26 is accepted and closed;
   do not reopen it. Agree any next task or live observation separately with Adam.
2. Ticket-26 implementation, tests, issue and delivery are committed as `6149bcf`.
   Preserve unrelated edits and the local handoff/map, which remain uncommitted;
   no blanket staging/reset/clean.
3. Ticket 25 remains accepted. Parent 19 remains open. The offline MIME defect is
   not a confirmed cause of any smoke failure: the exact header was not retained.
4. All three live-smoke authorizations remain consumed. No real credential reads,
   provider/auth calls, retries/resumes, production captures or credential repair
   occurred during ticket 26. No further live observation is authorized. A future
   observation needs separate permission, a new private destination and an agreed
   secret-safe observation contract. Preserve all stores and execution guards.

The earlier instruction to scope an offline investigation is superseded by this
completed implementation; earlier live-smoke boundaries remain in force.

## Previous update — ticket 25 accepted; third live smoke stopped at content type

Adam approved offline header-rule diagnostics, public adapter/receipt/HTTP/browser/
replay seams and baseline `31d408b8fa7b0535c91734b3d5b8a8ff6c55ce21`.
Adam explicitly accepted ticket 25 ("1. Accept"); it is resolved and closed.
Implementation and acceptance are committed on `main` as `1e5e8e8`.
Ticket: `.scratch/workflow-generator/issues/25-classify-response-header-failures.md`.
Delivery: `docs/designer-ticket25.md`.

Codex and Vertex (generation and OAuth) now distinguish `invalid_http_status`,
`invalid_http_header`, `duplicate_http_header`, `unsupported_http_content_type`
and `unsupported_http_content_encoding`. Fixed messages remain secret-safe;
parsed status survives malformed header bytes. Strict acceptance policy, limits,
no-retry behavior, historical codes and receipt/replay versions are unchanged.

Final full offline suite: **1,727 passed, 3 expected skips**, including real
Chromium and offline replay. Mypy: **35 source files clean**. JS syntax/whitespace
checks pass; Graft refreshed. Console:
`/tmp/workflow-ticket25-full-suite-final.txt`. No production changes followed tests.
Independent Standards: 0 hard violations, 1 optional mirrored-parser duplication
heuristic deferred. Independent Spec: 0 implementation findings. Both reviews were
static; the implementation agent ran verification. See delivery record for details.

After acceptance, Adam separately authorized one fresh smoke at
`/home/hermes/workflow-evidence/live-smoke-03`. That authorization is now consumed.
Fresh capture selected the same oldest source and unchanged 14-file guidance/default
models. At `1e5e8e8`, request
`79d2f5931cb0ceea0d611c5aeeec13396e62ef7b5e8ff28fea8f9d4a5a93f1d8`
failed at Generator with **`unsupported_http_content_type`, provider status 200**
after about 1.62 seconds. One reserved generation attempt, zero recorded auth
requests, unknown usage. No copy, Guardian, completed-pair Check or retry occurred.
Snapshot/receipt digests, unchanged source/guidance and private permissions verified.
Details: `SMOKE.md`, `run-view.json` and `verification.json` in the third destination.

The rejected rule is now known: content type was missing or did not match the
expected `text/event-stream` under existing comparison. Its exact value was not
retained. Do not infer JSON, HTML, a challenge page, successful generation or the
cause of either earlier smoke. Next recommendation is a scoped **offline** content-
type compatibility/diagnostic investigation, not approved implementation. Agree
scope and seams before changing policy or adding diagnostics. Do not reopen ticket
25. Parent 19 remains open; quality and complete live execution remain unverified.

Only the separately authorized smoke read the real Codex credential through its
adapter. No further live/model/auth calls, credential-content reads, retries/resumes
or credential repair are authorized. Any future observation needs fresh permission,
a new private destination and an agreed secret-safe observation contract. Preserve
all three failed stores and the consumed execution guard unchanged.

Ticket-25 implementation/tests/issue/delivery are committed separately. This handoff
and local map remain local, preserving earlier edits. Preserve unrelated working-
tree changes; no blanket staging/reset/clean. Older next-step recommendations below
are superseded where they propose the now-delivered diagnostic refinement or a
third smoke.

### Start next session here

1. Read `docs/designer-ticket25.md` and
   `/home/hermes/workflow-evidence/live-smoke-03/SMOKE.md`. Inspect its
   `run-view.json` and `verification.json` only if more detail is needed.
2. Ticket 25 is accepted and closed. Do not repeat its implementation or the third
   smoke. Discuss the bounded offline content-type investigation with Adam before
   implementation; `1e5e8e8` is a baseline candidate, not an approved new baseline.
3. Consult Graft using `_https`, `unsupported_http_content_type`, `CodexSource`
   and `test_status_and_representation_rules_are_distinct`. Relevant paths are
   `agent_lab/designer/codex.py`, `vertex.py`, and
   `tests/test_designer_response_headers.py`. Existing evidence cannot reveal the
   exact content type. Do not weaken validation based on speculation.
4. All three live-smoke authorizations are consumed. No further credential reads,
   provider calls, retries/resumes or auth repair without fresh explicit permission.
5. Preserve unrelated changes and local handoff/map. Parent 19 remains open.

## Previous update — ticket 24 accepted and closed

Branch `main`, HEAD `31d408b` (ticket-24 implementation and acceptance). No runtime
changes followed acceptance. This handoff refresh changes documentation only;
verification results below are recorded results, not a new test run.

### Start next session here

1. Read `docs/designer-ticket24.md` and the private
   `/home/hermes/workflow-evidence/live-smoke-02/SMOKE.md`, then inspect
   `run-view.json` and `verification.json` there if needed. Ticket 24 is accepted;
   do not reopen it or repeat the completed header fixes.
2. The next recommended task is a small **offline diagnostic refinement**, not
   another blind live attempt: distinguish the specific response-header rejection
   rule using fixed allowlisted categories (for example duplicate singleton,
   malformed field, unsupported content type or encoding). This is a recommendation,
   **not approved new implementation scope**. Adam requested this handoff only.
   Agree scope, public test seams and a review baseline before implementing.
   `31d408b` is the current baseline candidate, not a newly approved task baseline.
3. Consult Graft with literal identifiers: `CodexSource`, `_https`, `header_field`,
   `REPEATABLE_METADATA`, `ModelFailure`. Main paths:
   `agent_lab/designer/codex.py`, `vertex.py`, `http_response.py`,
   `agent_lab/model_operation.py`, and `tests/test_designer_response_headers.py`.
   Receipt propagation and HTTP/browser coverage already exist. Keep diagnostics
   secret-safe: no raw values, cookies, credentials, arbitrary field names, provider
   bodies or exception text. Do not guess the rejected header from timing or HTTP 200.
4. Both smoke authorizations were consumed by their single fresh runs. No further
   live/model/auth calls, credential-content reads, retry/resume or credential repair
   are authorized. A future smoke needs explicit permission and a named private
   destination; preserve both failed stores and request identities unchanged.
5. Parent 19 remains open. Neither HTTP 200 nor passing offline tests establishes
   complete live execution, useful writing/review quality or publication permission.
   Preserve unrelated working-tree edits and the local handoff/map; no blanket staging.

### Second live smoke — completed attempt, stopped at Generator

After acceptance, Adam explicitly authorized a second smoke at
`/home/hermes/workflow-evidence/live-smoke-02`. At commit `31d408b`, fresh capture
selected the same oldest draft and unchanged 14-file authority/default models.
Fresh run `11dc5d322dead83f93bea562f41fc6ecd0a27937976321a7bd320cb82218d8ed`
failed with **`invalid_http_headers`, provider status 200**, after about 1.25 seconds.
One attempt, zero recorded auth requests, usage unknown. No Guardian, completed-pair
Check, retry, publication or protected writes. Receipt digests, unchanged source/
guidance bytes and private evidence permissions verified. Details: `SMOKE.md` and
`verification.json` in the second destination.

The observed failure is now narrowed to response-header validation, but neither
the rejected field nor exact rule was retained. Do not infer that the original
smoke had the same cause. Next: diagnose with secret-safe, allowlisted header-rule
classifications; existing evidence cannot recover raw headers. Further live calls
need separate authorization. Parent 19 remains open; ticket 24 remains accepted.

### Earlier execution and accepted fix

Adam authorized the first live smoke and confirmed private destination
`/home/hermes/workflow-evidence/live-smoke-01`. Capture succeeded; Generator failed
with sanitized `invalid_response` after one reserved attempt. No copy, Guardian
call or completed-pair Check followed. No retry occurred. Usage remains unknown.
Private evidence and summaries: `SMOKE.md`, `DIAGNOSIS.md` in that destination.
Sources and guidance still matched capture digests; evidence permissions were private.

Offline diagnosis reproduced rejection of legitimate repeated response headers,
without confirming that defect as the live failure's cause. Adam approved fixing
Codex/Vertex headers and adding secret-safe diagnostics, then explicitly approved
public adapter, receipt, HTTP/browser and replay regression seams against baseline
`3c18b5d5b84a45527657063953f7d3d1a72f7def`.

Adam explicitly accepted ticket 24 ("accept"). It is `resolved` and closed;
implementation and acceptance are committed together.
See `docs/designer-ticket24.md` and
`.scratch/workflow-generator/issues/24-harden-provider-response-diagnostics.md`.
Safe repeatable metadata is discarded; shared header/chunk/trailer syntax stays
strict. Fixed failure codes identify request, HTTP headers/framing, OAuth response
and model response validation without recording raw failures or credentials.
Existing historical codes and offline completed-pair replay remain compatible.

Final full offline regression: **1,654 passed, 3 expected skips**, including real
Chromium; mypy **35 source files clean**. Console:
`/tmp/workflow-ticket24-full-suite-final.txt`. JS syntax/whitespace pass; Graft
refreshed. No production changes followed final tests. Independent Standards:
0 hard violations, optional duplication addressed. Independent Spec: 0 outstanding
findings after red-first metadata/chunk/trailer fixes; final follow-up independently
ran all 100 new adapter tests. Review detail and limitations are in the delivery record.

Any later live smoke needs fresh explicit authorization; do not retry or resume
either failed request. Parent 19 remains open, and complete live availability/
editorial quality are still unverified. Ticket-24 implementation/tests used synthetic
credentials only. The separately authorized second smoke did read the real Codex
credential through its adapter; no further live calls or credential reads are authorized.
Preserve existing unrelated changes. Ticket-24 files are committed separately;
this handoff and the local map remain local to preserve earlier edits. No blanket
staging/reset/clean. Older ticket-23-only next-step guidance is superseded.

## Previous update — ticket 23 accepted and closed

Branch `main`, latest acceptance commit `3c18b5d`. Ticket 23 implementation:
`7aee160`; verification record: `f8770a0`. Delivery record:
`docs/designer-ticket23.md`; local issue:
`.scratch/workflow-generator/issues/23-check-completed-workflow-through-offline-replay.md`.
Adam approved implementation, test seams and baseline `101aa2f21075e89f4c878923ad8e543e7900a9fb`.
Adam explicitly accepted ticket 23 ("accept"); its status is now `resolved` and
this slice is closed. Parent 19 remains open. Tickets 21/22 stay accepted.

### Start next session here

1. Read `docs/designer-ticket23.md` and the ticket-23 issue. Do not reimplement the
   completed slice or reopen its approved contract/readiness decisions.
2. Ticket 23 is accepted; do not reopen it. Parent 19 acceptance and the next scope
   remain separate decisions for Adam, not automatically authorized work.
3. Recommended next step, discussed with Adam before ending this session: prove the
   complete workflow on one real draft, rather than start another feature ticket.
   Obtain explicit live-smoke permission and a named private evidence destination
   first; neither has been supplied. Adam's agreement to this direction and request
   for a handoff are not live execution authorization.
4. Once authorized: capture and inspect the oldest eligible draft and configured
   defaults, run Generator then Guardian (at most two generation calls, no retries),
   run offline Check, and inspect output/review/usage. Authentication network activity
   is separate. Sources and Hermes remain read-only; nothing is published.
5. Use that evidence to discuss parent-19 acceptance. Its local issue has stale
   proposed-contract/readiness text superseded by accepted tickets 20–23 and ADR
   0010; do not reopen settled decisions. Live availability and writing quality are
   still unverified. Do not automatically close parent 19.

### Delivered behavior and final evidence

- Browser **Check completed pair (offline)** and protected `/api/drafts/check`
  validate the immutable capture, complete version-2 receipt/reservation/exchange
  chain, exact request identities, strict editorial results, usage and semantic log.
- Independent fresh recorded sources execute actual reference/candidate drivers.
  No final-state substitution, live fallback, credentials, network, source
  rediscovery or partial-run resume. Unused/exhausted exchanges, caught extra
  invocations, candidate drift and missing replay audit events cannot pass.
- Fresh check evidence binds the original snapshot/run/receipt digest. Historical
  usage is separate from zero new model/auth calls. Guardian verdict and publication
  authority remain separate from conformance. Invalid recordings retain sanitized
  failure evidence without replay. Browser stale success/error and inert rendering
  are tested; existing source/evidence records remain untouched.
- Final full suite: **1,544 passed, 3 expected skips**, including real Chromium and
  all **72 new ticket-23 tests**. Console: `/tmp/workflow-ticket23-full-suite-final.txt`.
  Mypy: **34 source files clean**; JS syntax/whitespace checks pass; Graft refreshed.
- Independent Standards: **0 hard violations**, 2 deferred optional duplication
  heuristics (historical limit encodings and browser fixture setup). Independent
  Spec: **0 actionable implementation findings**, 52 core replay tests rerun.
- First full run found one stale capture-era assertion expecting Check to be absent.
  Updated it to require valid Check identities, retained the absent load-route check,
  passed its 43-test HTTP file, then reran the full suite successfully. This test-only
  update followed independent review; no production changes followed final tests.
- No live calls, production captures or real credential reads occurred. Live provider
  availability and editorial quality remain unverified.

### Working-tree care

Ticket-23 code/tests/delivery/issue records are committed separately from unrelated
work. This handoff remains local, preserving earlier uncommitted edits. Preserve
existing `.gitignore`, `ROADMAP.md`, tickets 04/09, docs for tickets 04/16/18 and
untracked map, earlier issues, parent 19, provider research and local config files.
Inspect `git status`; no blanket staging/reset/clean.

Older summaries below are historical wherever superseded by this update.

## Previous update — ticket 22 accepted and closed; ticket 23 implementation approved

Verified against git history and delivery/issue records. Branch `main`, HEAD
`101aa2f21075e89f4c878923ad8e543e7900a9fb`:
- `538c101` — ticket 21 acceptance and closure.
- `7695153` — ticket 22 independent exact-draft Guardian review.
- `d9d7a33` — ticket 22 verification and readiness for acceptance.
- `101aa2f` — ticket 22 acceptance and closure (Adam: "accept 22").

Tickets 21 and 22 are resolved and closed. Do not reopen their approved decisions.
Parent 19 remains incomplete. Ticket 23's dependency is satisfied. Adam subsequently
explicitly approved ticket-23 implementation, its public test seams and review
baseline `101aa2f21075e89f4c878923ad8e543e7900a9fb`. Its local status is now
`ready-for-agent`; implementation and acceptance remain outstanding.

### Start next session here

1. Read `docs/designer-ticket22.md` and
   `.scratch/workflow-generator/issues/23-check-completed-workflow-through-offline-replay.md`.
2. Reuse the approved `docs/designer-ticket19-execution-contract.md` and accepted
   ADR 0010. Ticket 23's stale readiness paragraph has been corrected; do not ask
   Adam to approve these decisions again.
3. Proceed with ticket 23 using approved baseline
   `101aa2f21075e89f4c878923ad8e543e7900a9fb` and the approved HTTP/browser,
   independent replay and network-denying seams.
4. Implement only completed-pair offline Check: validate capture/receipt/versions/
   digests/order; independently replay exact request-bound responses through the
   plain reference and actual candidate; expose fresh case-scoped conformance in
   HTTP/browser separately from Guardian's verdict and historical usage.
5. Preserve network-denying and no-credential-loading replay tests, candidate-drift
   and corrupt/partial/unused recording failures, actual HTTP and real Chromium
   seams, existing ticket-18 behavior, independent Standards/Spec reviews,
   typechecking and final full offline regression.

No live smoke, real credential-content reads or model/auth calls are authorized.
Live smoke needs separate explicit authorization and a named evidence destination.
Replay must not discover sources, load credentials, fall back to live transport,
resume partial runs, change eligibility or authorize publication. Parent acceptance
remains Adam's decision.

### Ticket 22 delivered behavior

- Fresh explicit runs execute Generator then one independent Guardian review using
  the original captured source/authority and exact draft digest. Generator failure
  or blocked output prevents Guardian. Two steps and at most two generation
  attempts, one per role; no retries, revisions, fallback or background review.
- Guardian validates ten criteria and distinguishes Approved, Changes requested
  and Blocked. All are completed editorial reviews, never publication permission.
  Required fixes and optional preferences are separate. Copy-only review explicitly
  says `Image consistency not reviewed.`
- Dedicated Vertex adapter uses the approved pinned authorized-user file
  `~/.config/gcloud/application_default_credentials.json`, not Hermes's auth file.
  Token acquisition is bounded and in-memory only; auth activity is separately
  reported. Explicit defaults: project `project-54e16fcb-7c62-4041-bb1`, region
  `global`; operator-only overrides. No credential discovery or protected writes.
- Version-2 receipts bind capture, request/claim, reservations, ordered exchanges,
  exact draft/review, versions, usage and execution log. Duplicate/restart handling
  never resends or resumes; same-capture attempt warnings are durable. Guardian
  failure retains valid Generator output; storage/audit uncertainty is not approval.
- Legacy Generator-only identities retain `not_reviewed` attribution. They are not
  silently upgraded into pairs. Completed-pair Check remains ticket 23.

### Latest recorded verification

- Full offline suite: **1,472 passed, 3 expected skips**, including real Chromium.
  Console: `/tmp/workflow-ticket22-full-suite-final.txt`. Skips: two opt-in live Jev
  checks and the optional real Hermes plugin-loader check.
- Mypy: **33 source files clean**. JavaScript syntax and whitespace checks passed;
  Graft refreshed. No production changes followed the final suite.
- Independent Standards: **0 hard violations**, 3 deferred optional maintainability
  heuristics. Independent Spec: **0 actionable findings**, 141 focused tests rerun.
- These are recorded results, not tests rerun during this handoff refresh. No live
  availability, authentication or editorial-quality verification is claimed.

### Current working-tree care

This refresh and subsequent approval update change this handoff and ticket 23's
readiness record only. Preserve existing modifications in
`.gitignore`, `ROADMAP.md`, tickets 04/09 and docs for tickets 04/16/18. Existing
untracked files include `.ignore`, `AGENTS.md`, `opencode.json`, the local map,
earlier tickets, parent 19, ticket 23 and the provider-feasibility document. Ticket
22 and its delivery record are now committed, not untracked planning material.
Inspect `git status` before editing/staging; no blanket add/reset/clean.

All older status, next-step and working-tree summaries below are historical where
superseded by this update.

## Previous update — ticket 21 accepted and closed

Branch `main`; implementation/verification through `5e8c44d`:
- `3bf1bf9` — captured Signal Generator runs and explicit model operations.
- `56438c6` — review fixes: typed failures, HTTP states and strict token reads.
- `5e8c44d` — verification and independent review record.

Adam approved all ticket-21 readiness decisions, clarified Codex means his
subscription, then confirmed using the existing Hermes login read-only and said
"proceed". Adam subsequently explicitly accepted ticket 21 ("accept").
Ticket 21 is `resolved` and closed; parent 19 remains incomplete.
Acceptance does not authorize a live smoke or implementation of ticket 22.

### Start next session here

1. Read `docs/designer-ticket21.md` and
   `.scratch/workflow-generator/issues/21-generate-one-linkedin-draft.md`.
2. Ticket 21 is accepted; do not reopen its approved design/readiness decisions.
   Ticket 22 is the next slice, pending Adam's instruction to proceed.
3. If Adam requests a live smoke, obtain explicit authorization and a named
   evidence destination before reading real credentials or making a model call.
   No production capture or live authentication/model availability has been tested.
4. If he requests the next slice, read the local ticket 22 and approved
   `docs/designer-ticket19-execution-contract.md`; scope Guardian independently.
   Ticket 23 owns completed-pair offline Check. Neither is implemented here.

### Approved decisions and delivered behavior

- ADR 0010 is **accepted**. Transform supports explicit, versioned model operations
  with deterministic prepare/apply and a declared live/fixture/recorded source.
  Ordinary callable Transforms remain deterministic; Judgment is unchanged.
  Both existing drivers independently execute the operation. Admission and actual
  candidate inspection distinguish the contract; conformance rejects live/shared
  sources. No sixth node kind or new workflow runtime.
- Ticket-20 selection, immutable captures and full 14-file authority manifest are
  unchanged. Browser capture now issues an opaque input-bound run request. Explicit
  **Run Signal Generator** returns structured copy marked **Not reviewed**, or
  distinct blocked/failed/uncertain status. No Guardian or publication permission.
- Dedicated Codex subscription adapter, default `~/.hermes/auth.json`, optional
  operator-only `--codex-auth-file`. Reads an owned regular file with `O_NOFOLLOW`;
  uses only a valid existing access token. No refresh, discovery, locks, repair,
  Hermes sessions/imports, auxiliary calls or protected writes. Missing/expired
  credentials require operator action through Hermes separately.
- One Generator attempt, no retries/repair/fallback. Approved local limits:
  180-second whole-request deadline, 64-KiB SSE envelope, 3,000-code-point post.
  No capped-spend/token promise or remote-cancellation guarantee.
- Exclusive durable claim/reservation before invocation; exact canonical request
  and sanitized response persisted before application. Immutable exchange/log
  evidence and receipt retain input/operation/schema identity, provider metadata,
  separate usage and typed sanitized failures. Unknown usage remains unknown.
- Duplicate/concurrent identities never resend paid work. Interrupted incomplete
  claims remain uncertain after restart, never resume. Explicit new request is
  required for another run. UI renders inert text and rejects stale responses;
  same-capture warning memory is page-local, while request deduplication is durable.

### Verification and review

- Full offline suite: **1,331 passed, 3 expected skips**, including real Chromium.
  Console: `/tmp/workflow-ticket21-full-suite.txt`. Skips: two opt-in live Jev tests
  and optional real Hermes loader. No runtime changes after this full run.
- Mypy: **31 source files clean**. Focused ticket-21 checks: **192 passed**.
  Graft refreshed and whitespace checks passed.
- Independent Standards: **0 hard findings**, 1 optional fixture-naming heuristic
  intentionally deferred. Independent Spec follow-up: **0 outstanding actionable
  findings**, with 89 focused tests rerun.
- Review fixes were red-first: typed sanitized failure codes/status survive exchange
  and receipt; HTTP pre-execution rejections display failed while lost responses or
  unverifiable prior work stay uncertain; credential symlinks/foreign ownership fail.
- Original approved review baseline: `f0e0eded07dfe6f7b0d91424a40d46d3ca036da6`.
  Optional review notes: `/tmp/ticket21-spec-review.md`,
  `/tmp/ticket21-spec-followup.md`, `/tmp/standards-followup-review.md`.
- No real credential-content reads, live calls, production captures, source edits
  or Hermes writes occurred. Post quality and live provider availability are unverified.

### Code and operator pointers

- `agent_lab/model_operation.py`: explicit request/response/failure/operation contracts.
- `agent_lab/reference.py`, `generation.py`, `conformance.py`, `spec.py`: core extension.
- `agent_lab/designer/linkedin.py`: versioned Generator request/schema/apply and spec.
- `agent_lab/designer/draft_runs.py`: durable request/attempt/evidence lifecycle.
- `agent_lab/designer/codex.py`: isolated subscription-token adapter/transport.
- `agent_lab/designer/server.py`, `static/app.js`: HTTP Run and browser state.
- Public endpoints: `/api/drafts/capture`, `/api/drafts/request`, `/api/drafts/run`.
  Existing exact loopback Host/Origin/token and bounded JSON protections remain.
- Setup command and limitations: `docs/designer-ticket21.md`; complete capture
  manifest: `docs/designer-ticket20.md`. Fixture and transport tests are in
  `tests/test_model_operations.py`, `tests/test_designer_draft_runs.py`,
  `tests/test_designer_draft_run_{server,browser}.py`, and
  `tests/test_designer_codex{,_failures}.py`.

### Working-tree care

Ticket-21 implementation, ADR 0010, approved contract and delivery record are
committed. This handoff remains local to preserve earlier uncommitted handoff edits.
Do not blanket stage/reset/clean. Existing unrelated edits remain in `.gitignore`,
`ROADMAP.md`, tickets 04/09 and docs for tickets 04/16/18. Local untracked material
includes `.ignore`, `AGENTS.md`, `opencode.json`, the map, earlier tickets, parent 19,
tickets 22/23 and `docs/designer-ticket19-provider-feasibility.md`. Inspect `git status`.
Older sections below are historical; their "ticket 21 needs-info", "ADR proposed",
"capture-only" and former HEAD statements are superseded by this update.

## Previous update — ticket 20 accepted and closed

Adam explicitly accepted ticket 20 ("accept"). Capture and preview of the oldest
eligible draft is delivered: `e000f8a`, review fixes `3b6224a`, verification `ad6bbea`.
Acceptance is committed in `f0e0ede`, current HEAD on `main`.
Evidence/setup: `docs/designer-ticket20.md`. Full offline suite: **1,139 passed,
3 expected skips**, including **114 Chromium tests**; mypy **27 files clean**.
Independent follow-up: no outstanding Standards hard findings or Spec findings.

Folder-based eligibility is approved: top-level content-drafts only, never inbox
or published. Exclude exact public-copy-bank.md before parsing; its frontmatter
was removed by Adam. Actual field spelling remains date_created. Limits, strict
invalid-metadata blocking, filename tie-break, bounded explicit guidance set and
capture/HTTP/Chromium seams were approved for ticket 20. No model calls or protected
writes occurred. The browser mode is capture-only, with operator --draft-config.

Ticket 19 was split into approved slices 20–23. Ticket 21 (one Generator draft) is
next, with dependency 20 satisfied; its execution/ADR, credential and other remaining
readiness decisions still require closure. Acceptance of 20 does not authorize
implementation of 21 or live smoke calls. Parent 19 remains open; do not reimplement
20. Preserve unrelated working-tree changes, including earlier handoff/map edits.

### Start next session here

Read in order:
1. `.scratch/workflow-generator/issues/21-generate-one-linkedin-draft.md`
2. `docs/designer-ticket20.md` (delivered API, complete operator manifest and setup)
3. `docs/designer-ticket19-execution-contract.md`
4. `docs/designer-ticket19-provider-feasibility.md`
5. `docs/adr/0010-explicit-model-operations-and-offline-replay.md` (still proposed)

Close only ticket 21's remaining readiness decisions before implementation:
- Explicit model-operation ADR and execution/replay contract; ordinary callable
  Transforms remain deterministic today. Do not hide live calls in them.
- Precise approved read-only Codex credential source, strict valid-token/no-refresh
  behavior, generation output schema, numerical execution bounds, durable request
  claiming and uncertain/duplicate handling. The 180-second/64-KiB response limits
  remain execution proposals; ticket 20's approved capture limits are distinct.
- Ticket-21 public execution/transport/HTTP/Chromium seams and review baseline.
  `f0e0ede` is current HEAD, **not an approved ticket-21 baseline**.

Do not reopen settled capture decisions: folder classification, public-copy-bank
exclusion, date_created, required metadata blocking, filename tie-break, explicit
14-file authority set, capture limits and read-only behavior are delivered/accepted.
Provider adjustments also remain approved: preserve both configured defaults,
no retries, local size/time bounds without capped-spend/remote-cancellation claims,
and in-memory-only Vertex token acquisition. That is not live smoke permission.

Scope sequence: ticket 21 produces one Generator draft marked **not reviewed**;
22 adds Guardian in the same new two-call run; 23 adds independent exact-request
recorded conformance. Do not prematurely claim reviewed pairs or replay in 21.
Live smoke always needs separate explicit authorization and a named destination.

### Delivered seams and verification

- `DraftSource.capture()` and `load()` in `agent_lab/designer/drafts.py` provide
  bounded immutable input capture/integrity checking, not execution or conformance.
- CLI `--draft-config` pins operator manifest paths at startup. Complete example:
  `docs/designer-ticket20.md`. Source/guidance/model changes require recapture;
  manifest path changes require restart. No production capture was performed.
- `GET /api/drafts` is availability only; protected `POST /api/drafts/capture`
  accepts only `{}`. No draft run/check/load HTTP endpoints. Existing offline and
  controlled-JSON-source modes remain available, including alongside draft capture.
- Real browser mode: **LinkedIn draft capture (no execution)**. Inert preview,
  invalidation and late success/blocked/error response protection are covered.
- Review found two bugs and both were reproduced red-first and fixed: unloadable
  bundles from non-UTF-8 inventory names, and transient hard-link counts rejecting
  concurrent atomic capture. Independent follow-up verified both fixes. One optional
  duplicated-eligibility-predicate observation remains, not an approved refactor task.
- Latest full-suite console: `/tmp/workflow-ticket20-full-suite.txt`. It ran once
  after review fixes: 1,139 passed, 3 expected skips, including 114 Chromium tests.
  Mypy 27 files clean. Subsequent edits were documentation/acceptance only.

### Working-tree care

Implementation, ticket 20 and its evidence/acceptance are committed. This handoff
and the existing local map remain uncommitted, preserving earlier local edits.
Tickets 19 and 21–23, proposed ADR 0010 and ticket-19 contract/provider research
remain untracked planning records; they are important context, not cleanup targets.
Other preserved changes include `.gitignore`, `ROADMAP.md`, tickets 04/09,
`docs/designer-ticket16.md`, `docs/designer-ticket18.md`, `docs/read-only-ticket04.md`,
and prior untracked local tickets/config/map files. Inspect `git status` before
editing/staging. No blanket add/reset/cleanup. Parent 19 was not modified or closed.

Older summaries below are historical where they differ from this update.

## Previous update — ticket 19 contract drafted; provider adjustments approved

### Start next session here

Ticket 18 is accepted and closed. Ticket 19 is **needs-info**, not implemented.
Adam selected a useful role workflow and authorized contract drafting and read-only
provider feasibility research. His latest "approve" accepted the provider adjustments
listed below, not blanket implementation or a live smoke run.

Read in order:
1. `.scratch/workflow-generator/issues/19-refine-and-review-oldest-linkedin-draft.md`
2. `docs/designer-ticket19-execution-contract.md`
3. `docs/designer-ticket19-provider-feasibility.md`
4. `docs/adr/0010-explicit-model-operations-and-offline-replay.md` (proposed)

### Agreed user workflow

- Source: `/home/hermes/Documents/life-os/Business/Personal Brand/content-drafts`.
- Both article and post drafts with frontmatter `processed: false`; choose oldest
  `date_created`. Adam is adding dates. Reinspect rather than relying on the old
  inventory (seven undated files at initial inspection). Never fix source metadata.
- Signal Generator refines the selected source into one LinkedIn post.
- Signal Guardian independently reviews brand voice, LinkedIn fit, strong hook,
  AIDA and a CTA coherent with the source; existing evidence/privacy rules also apply.
- A complete draft plus review is a completed run even for Changes requested.
  **Never set `processed: true`, move/archive a draft, or silently exclude it because
  a run receipt exists.** The same oldest source remains selectable until another
  process changes eligibility. Archiving is a different future workflow.
- Use existing SOUL/skills and each profile's configured default model. Observed:
  Generator `openai-codex` / `gpt-5.6-sol`; Guardian `vertex` /
  `google/gemini-3.1-pro-preview`. Re-resolve non-secret selections for capture.
- Two generation calls maximum (one per role), no retries, revisions, fallback
  models or background review. No publishing. Save output/evidence outside sources
  and Hermes. Guardian approval is not publication authority.

### Latest approved adjustment — do not re-ask

Installed Codex integration documents rejecting `max_output_tokens`. The suggested
hard 4,096-token ceiling was an agent proposal, not Adam's requirement. Adam approved:

- Keep both defaults and the hard two-generation-call limit, no retries.
- Bound local response size and elapsed time without claiming remote cancellation,
  a universal output-token cap or capped spend.
- Permit Vertex token acquisition **in memory only**; no credential-file or Hermes
  state writes. This is auth network activity, not a third generation call.

No live calls, credential-content reads or protected writes occurred in research.
Static inspection does not establish live authentication/model availability. Do not
reuse Hermes runtime/auxiliary resolvers unchanged: they can write auth state,
retry, fall back or raise output limits. Dedicated tool-free adapters are proposed.
Codex credential access remains read-only, valid existing token only; no refresh.

### Remaining closure before implementation

1. Recheck metadata and settle explicit article/post eligibility versus references
   (the folder includes `public-copy-bank.md`), required-field error behavior and
   deterministic date tie-break. Do not manufacture creation dates or silently skip
   ambiguities while claiming oldest.
2. Present/finalize proposed ADR 0010 and the whole execution/replay contract.
   Current ADR 0007 says Transform is deterministic/no-model. Proposed extension
   uses explicit prepare → bounded source → apply bindings, separate from ordinary
   callables; it is **not accepted yet**. Both drivers must execute independently;
   replay binds exact requests/responses and performs zero model calls.
3. Pin allowed authority inputs, precise credential-source configuration, concrete
   local bounds (180 seconds/64 KiB are proposals), and duplicate/uncertain handling.
   Preserve the already approved provider adjustments above.
4. Confirm public capture/run/replay, actual HTTP and real Chromium test seams and
   review baseline. Proposed baseline is current HEAD
   `35b9a5d7ac8784c062d25ec91f367e6c6d9ffb93`, **not yet approved for ticket 19**.
5. Only mark ready-for-agent after closure. Live smoke requires separate explicit
   authorization and a named output destination. Do not substitute another offline
   fixture demo for the requested useful model-backed workflow.

### Repository / verification state

- Branch `main`, HEAD `35b9a5d`; ticket 18 implementation `fce3a59`.
- Latest executed verification remains ticket 18: **1004 passed, 3 expected skips**,
  **100 Chromium tests**, mypy **26 files clean**. Console:
  `/tmp/workflow-ticket18-full-suite.txt`. Planning changes do not constitute a new
  test run; no runtime code changed during ticket 19 planning.
- Ticket 18 acceptance edits and ticket 19 planning files are **uncommitted**.
  New ticket 19 contract, provider report and ADR are currently untracked.
- Preserve existing unrelated changes in `.gitignore`, `ROADMAP.md`, tickets 04/09,
  `docs/designer-ticket16.md`, `docs/read-only-ticket04.md`, and existing untracked
  local tickets/map/config files. Inspect `git status` before edits/staging;
  no blanket add, reset or cleanup. Handoff includes earlier preserved local edits.

The older summaries below are historical where they differ from this update.

## Previous update — ticket 18 accepted and closed

Adam explicitly accepted ticket 18 ("accept"). Implementation: `fce3a59`;
verification documentation: `35b9a5d`, `docs/designer-ticket18.md`.
Controlled local JSON capture, preview, generated execution and digest-bound
offline conformance replay are delivered. Do not reimplement ticket 18.

- Full offline suite: **1004 passed, 3 expected skips**, including **100 Chromium tests**.
- Mypy: **26 files, no issues**. Independent Standards/Spec review found no
  confirmed violations; two optional robustness/duplication observations are
  recorded in the evidence document.
- Next direction: useful LinkedIn writing and independent Guardian review. Draft
  contract: `.scratch/workflow-generator/issues/19-refine-and-review-oldest-linkedin-draft.md`
  (`needs-info`, not implementation-ready). Adam agreed oldest `date_created`,
  both article/post drafts with `processed: false`, read-only sources (never update
  that flag), each profile's default model and two calls maximum, no retries.
  Adam is adding creation dates. Execution/replay contract is now drafted in
  `docs/designer-ticket19-execution-contract.md`, with proposed ADR 0010 for
  explicit model-operation bindings (no hidden live calls in deterministic work).
  Contract/ADR, test seams and baseline await approval. Static provider findings:
  `docs/designer-ticket19-provider-feasibility.md`. Codex's installed integration
  documents rejection of the proposed hard output-token cap. Adam approved retaining
  defaults/two calls/no retries, local response/time bounds without capped-spend or
  remote-cancellation promises, and Vertex token acquisition in memory only (no
  credential/Hermes writes). Full contract/ADR, concrete configuration, classification,
  test seams and baseline still require closure. No live calls have been made.
- Preserve unrelated working-tree changes. Hermes remains read-only; no live calls.

Older next-step instructions below are historical and superseded.

## Previous update — ticket 17 accepted and closed

Ticket 17 is implemented on `main` in `a1384c5`. Select **Role workflow (offline
fixtures)** in the browser to compose Signal Generator → `evidence_handoff` →
Signal Guardian, run either fixture, and independently check both supplied cases.
Studio Producer demonstrates an incompatible consumer; matching registry types
without fixture operations are explicitly unsupported. No real agents/models run.

- Full offline suite: **915 passed, 3 expected skips**, including **68 real Chromium
  tests**. Mypy: **25 files, no issues**. Console: `/tmp/workflow-ticket17-full-suite.txt`.
- Independent review against `19ae20e563ab82968a23874380315ccfbc0a5678`: Standards
  found no documented violations and two optional duplication heuristics; Spec
  found no confirmed issues and independently reran all 107 new tests successfully.
- Evidence: `docs/designer-ticket17.md`. No code changes after full-suite verification.
- Adam explicitly accepted ticket 17 ("approve"); it is accepted and closed.
  Do not reimplement it. Ticket 18's implementation prerequisite is now satisfied,
  and Adam has approved its controlled local JSON source and digest-bound snapshot
  contract and review baseline `163c586517c724fcd5c202b92033893956f632f8`.
  Ticket 18 is now `ready-for-agent`; implementation has not started.
- Unrelated working-tree changes remain preserved. Hermes stays read-only; no live calls.

Next implementation frontier: ticket 18. Read its approved source/snapshot
contract in the local ticket before starting; preserve unrelated working-tree changes.
Older next-step instructions below are historical and superseded by this update.

## Previous update — ticket 16 accepted and closed

Adam explicitly accepted ticket 16 ("accept"). Implementation is committed on
`main` as `0b87473`: **custom support requests execute offline against the
currently authored triage workflow**. Do not reimplement it. The local issue now
records acceptance and closure with its acceptance checklist checked.

### Next session

1. Read `docs/designer-ticket16.md` and the approved contract at
   `.scratch/workflow-generator/issues/16-try-custom-support-requests.md`.
2. Ticket 16 is accepted and closed. Adam approved the next two slices:
   ticket 17, compose and run one role-compatible workflow; ticket 18, run that
   workflow with one controlled read-only data source (blocked by 17).
3. Ticket 17 is now `ready-for-agent`: Adam explicitly approved the complete
   contract and review baseline `19ae20e563ab82968a23874380315ccfbc0a5678`.
   Read its local issue before implementation. The demo is Signal Generator →
   Signal Guardian via `evidence_handoff`, with two deterministic fixture-backed
   Transforms, two supplied cases and a two-step budget; no real agent execution.
   Ticket 18 remains `needs-info`, blocked by 17 and an agreed source/snapshot
   contract. No live integrations are authorized.
4. Inspect `git status` and use Graft before source exploration. Preserve the
   unrelated changes listed below. Hermes remains read-only; no live calls.

### Delivered behavior and verification

- `agent_lab/designer/custom.py::run_request` validates the current triage design
  and strict request fields, generates and executes the actual graph once, and
  returns submitted input, observed route, team, priority, deterministic summary,
  terminal, steps and fresh evidence path. Shared `TriageRequest` input rules feed
  the existing `TriageState`; no second triage runtime or model.
- Protected `POST /api/run` accepts only `{design, request}`. Exact loopback
  Host/Origin/token, JSON/body limits and caller-selected protected evidence root
  remain in force. No browser-supplied code, paths or output roots.
- Browser **Run request** results are separate from **Generate / check** supplied-
  case conformance. Custom input edits do not replace or expand conformance
  evidence. Workflow/request edits clear stale custom results and invalidate late
  success/error responses. Descriptions and rendered outputs remain inert text.
- Full offline suite after review fixes: **808 passed, 3 expected skips**, including
  **44 real Chromium tests** (none skipped). Mypy: **24 files, no issues**.
  Skips are two opt-in live Jev tests and the optional real Hermes loader check.
  Console evidence: `/tmp/workflow-ticket16-full-suite.txt` (temporary local file).
- Parallel independent review against starting HEAD `eabde12`: Standards found no
  violations/material smells; Spec found two gaps. Both were reproduced red-first
  and fixed: silent audit-event loss now fails event-count/accounting/route checks;
  description entry no longer truncates emoji using UTF-16 `maxlength` semantics.
  Regression tests and the full suite passed after fixes. The reviewers did not
  independently re-review those final fixes. Details: `docs/designer-ticket16.md`.
- Graft refreshed; diff checks clean. Ticket 15 and score composition still work.

### Try it

```bash
.venv/bin/python -m agent_lab.designer --evidence-dir /tmp/workflow-ticket16-evidence
```

Open the printed exact `http://127.0.0.1:PORT/` URL. Select **Support-request
triage**, fill the four fields under **Try a custom support request**, and click
**Run request**. **Generate / check** still checks only the six supplied cases.

### Working-tree caution

Ticket-16 implementation committed only its nine implementation/test/evidence
files. Existing modified files remain: `.gitignore`, `ROADMAP.md`, tickets 04/09,
`docs/read-only-ticket04.md`. Existing untracked files remain: `.ignore`,
`AGENTS.md`, `opencode.json`, local tickets 12/13/16 and
`.scratch/workflow-generator/map.md`. Do not stage them incidentally or discard
user changes. This handoff does not authorize expanding the runtime, persistent
Spec format, packaging, live integrations or Hermes writes/activation.

All older next-step instructions below are historical and superseded.

## Previous update — ticket 15 accepted

Adam explicitly accepted ticket 15 ("accept"). Offline support-request triage is
implemented in `178f3e0`, accepted and closed. Evidence: `docs/designer-ticket15.md`
(720 passed, 3 expected skips, 19 Chromium tests; mypy clean; independent review
found no blocking Standards or Spec findings). Do not reimplement it.

Ticket 16, custom support-request entry/execution, is the next unblocked ticket.
Its approved contract is in the local issue file; acceptance of ticket 15 does not
itself request implementation of ticket 16. Preserve unrelated working-tree changes.
Hermes remains read-only; no live calls are authorized.

Older next-step instructions below are historical and superseded by this update.

## Previous update — ticket 14 accepted

Adam explicitly accepted and closed ticket 14: “sounds good. Accept ticket 14.”
The local issue is now resolved. Browser composition is delivered; do not reimplement
or re-scope it. Evidence: `docs/designer-ticket14.md` (614 passed, 3 expected skips;
mypy clean; independent review findings resolved). Implementation and acceptance
records are included in the ticket-14 commit; preserve unrelated working-tree changes.

Next direction discussed: choose and scope one useful offline request-triage workflow
with meaningful operations, sample inputs and visible outputs. No concrete next-ticket
contract or implementation is approved yet. Parallel and Gates need not block that
scope discussion. Hermes remains read-only; no live calls are authorized.

The prior session notes below are historical: statements that ticket 14 awaits scope
or implementation are superseded by this update.

## Start here: previous state and approved direction

Working branch: `main`.

**Latest session:** ticket 13 is implemented and reviewed in `0bad1d0` and
`3e47b2b`. Adam tried the UI, confirmed that it is a constrained pre-built workflow
demo, and said “good work. next”. Do not reimplement ticket 13. Its local issue and
the planning map still contain older `ready-for-agent` wording; the implementation
and verification evidence is `docs/designer-ticket13.md`.

**Next-session priority:** scope **ticket 14: compose workflows through the browser
questionnaire**, moving beyond the fixed threshold-demo shape. Adam approved this
direction with “yes, but we will have to do it in next session handoff”. Detailed
contract design and implementation are deferred to the next session. Ticket 14 has
not yet been published; do not treat this direction as an agreed detailed spec.

**Numbering warning:** published ticket 13 came from planning item **P26**. The new
browser-composition ticket 14 is **not P14** (parallel branch Decisions/Loops), and
neither P13's parallel kernel nor P17's Gate work blocks this browser direction.
Read this handoff before selecting an item by number.

Tickets **01–12 are accepted and closed**. Ticket 12 implementation and review:
`597d315` (bounded Loop execution and conformance), `c0a2760` (review evidence and
candidate-side audit-failure regression). Adam explicitly confirmed ticket 12
acceptance/closure (“confirm 12”); its local issue now records closure and checked
acceptance criteria.

The generation/checking loop now supports Transform/Decision, restricted
Intervention Judgment and bounded Loop nodes with Route edges.
Its artifact is in-memory, with independently supplied candidates and
same-ID/separate-fresh-log exact trace/byte/digest comparison. Persistent spec
serialization remains deferred. Later milestones remain outlines, not authorized
implementation work.

Adam approved the next direction:

> Prove the smallest complete generation loop first:
> authored spec → plain reference → generated graph → passing conformance check.
> Keep the initial target restricted to Transform/Decision nodes and Route edges;
> expand node support only after this loop is demonstrated.

That restricted loop is now accepted. Adam subsequently clarified that a small
implementation slice must not restrict the planning horizon. The next session should
review the whole-product dependency map before refining the implementation frontier.

### Next session's job

1. Read `docs/designer-ticket13.md` and
   `.scratch/workflow-generator/issues/13-build-browser-workflow-designer.md` for the
   delivered browser slice. Inspect working-tree changes before editing; use Graft
   before opening source. The implementation is in `agent_lab/designer/`.
2. Scope ticket 14 with Adam around the approved direction:
   - Choose steps from a small, safe operation catalog.
   - Add Decisions and select their destinations.
   - See the graph change structurally, not just its threshold.
   - Generate/check through the same existing core.
   - Keep questionnaire-based editing, **not drag-and-drop**.
   Existing Transform/Decision + Route execution is enough for this direction;
   parallel execution and Gates remain separate work, not prerequisites.
3. Agree a bounded concrete demo, catalog/state contract, allowed graph shapes and
   size/budget limits, destination editing and invalid-design behavior, typed offline
   cases/independent expected outcomes, public test seams and review baseline before
   marking ticket 14 `ready-for-agent`. These details have **not** been approved yet.
   `3e47b2b` is the latest implementation baseline candidate, not an approved ticket-14
   review baseline. Publish the agreed contract under `.scratch/workflow-generator/issues/`.
4. Retain ticket 13's safety and evidence guarantees: finite trusted operations,
   strict inputs, caller-selected protected evidence root, exact loopback/origin/token
   request boundary, real core checking, visible failures and stale-result invalidation.
   No persistent public spec format, arbitrary browser-supplied code, live calls or
   Hermes changes are authorized by this direction.
5. Read `.scratch/workflow-generator/map.md`, `ROADMAP.md`, `CONTEXT.md` and relevant
   ADRs for the whole-product horizon. Update stale ticket-13 bookkeeping explicitly;
   do not conflate provisional P-identifiers with published issue numbers. Parallel,
   Gate/artifact identity, roles/data/skills and other outlines remain future work.
   No broad prefactor is pre-authorized.

### Ticket 13 verification and trying the UI

- Full offline suite: **474 passed, 3 expected optional skips**, including five real
  Chromium smoke tests. Mypy: **22 source files, zero errors**.
- Independent Standards/Spec review: no outstanding hard/blocking findings. A concern
  about digest-addressed logs was withdrawn on follow-up: the browser reuses the
  accepted temporary conformance-evidence contract, not an approval-bound artifact store.
- Commits: `0bad1d0` implementation; `3e47b2b` protected-root review follow-up/evidence.
- The current UI's shape is fixed: receive → threshold Decision → chosen terminals.
  Threshold/outcome choices author a real spec and execute real generation/conformance;
  it is not yet a general composer. Adam understands this limitation.

```bash
.venv/bin/python -m agent_lab.designer --evidence-dir /tmp/workflow-evidence
```

Open the printed `http://127.0.0.1:PORT/` URL, not `localhost`. Ctrl-C stops serving.
Browser tests require `requirements-browser.txt` and system Chromium (or `CHROMIUM`).
Repeatable `--protected-root PATH` protects additional Hermes installations.

**No live calls, Hermes activation changes or Hermes writes are authorized.**

## What works now

- Repo-local foundation in `agent_lab/`, with existing plain and graph business
  drivers and their equivalence tests. No sibling-runtime imports.
- Shared run-level budget reservations and append-only event sequence allocation;
  parallel foundation tests prove cap enforcement and preservation of branch
  results through reducers. This is not a general generated parallel engine.
- Read-only Kanban/Hermes diagnosis, four metrics, worker/auxiliary/review traffic
  separation, separate reasoning tokens, per-role/per-run reports and measured
  baseline comparisons. Immutable digest-addressed diagnosis/report artifacts.
- Terminal and local Hermes plugin commands. Installation/registration without
  protected edits is accepted; normal activation remains an explicit operator
  config opt-in. Do not bypass the host activation gate.
- `agent_lab.spec.validate_spec`: typed in-memory declarations for all five node
  types, Route/Fork edges, complete routing, joins and bounded-cycle validation.
  Admission is not execution or conformance.
- `agent_lab.reference.compile_reference`: Transform/Decision/Intervention Judgment/Loop
  + Route execution with explicit caller bindings and frozen Pydantic state.
  Judgment uses node-ID bindings with an assessment adapter and source; checking
  requires independent offline sources and compares full judgment/input evidence. All unsupported/unbound
  declarations, including unreachable ones, are rejected before execution.
  State snapshots are validated/detached; binding failures and budget exhaustion
  are recorded. Arbitrary node identities work, not just business Stage values.
- Loop predicates use exact opaque caller-binding keys and strict boolean results.
  Every visit reserves a step before invocation. True exits even after the last
  allowed repeat; false repeats while allowance remains, otherwise exhausts.
  Counters are per Loop identity/per run, never reset on re-entry, and start fresh
  for a new run. Predicate snapshots cannot mutate retained state or caller input.
  Events persist `repeat_count` and `max_iterations`; structural checking inspects
  actual bounds, predicate references, routes and unreachable declarations.
- Reference execution reuses `RunAccounting.reserve`, `Budget` and
  `RunLog.append_next`. `RunLog.fresh_run` refuses reused recorded identities and
  overlapping reference passes on the same log. Audit I/O failure stops execution
  visibly. No resume or crash durability.
- `agent_lab.generation.generate_graph` emits an owned in-memory executable graph;
  `agent_lab.conformance.check_conformance` checks actual execution configuration
  and supplied-case behavior against its independently compiled plain reference.
  Passing is restricted, case-scoped evidence, not universal conformance.

## Verification at the end of ticket 12

- Loop public-seam tests: **32 passed** (`tests/test_loop_routes.py`).
- Full offline suite: **423 passed, 3 optional skips**.
- Mypy: **19 source files, zero errors**; diff checks clean; Graft refreshed.
- Parallel Standards/Spec review against `5038a372780171b892b057be150baf7fb2f0dd8d`:
  no documented Standards violations and no confirmed Spec violations. The Spec
  reviewer suggested candidate-phase checker audit-failure coverage; added it.
- One optional maintainability smell retained: repeated type switches selecting
  `operation` / `value` / `exit_predicate` / Judgment node ID in admission,
  execution, generation and structural inspection. A small shared accessor could
  reduce drift, but is not a blocker or an approved standalone next ticket.
  Preserve independent driver control flow and actual-candidate inspection if
  addressing it; do not conflate shared metadata lookup with driver delegation.
- Evidence: `docs/loop-ticket12.md`. No live calls or Hermes edits.

```bash
.venv/bin/python -m pytest -q tests/test_loop_routes.py
.venv/bin/python -m mypy agent_lab
AGENT_LAB_JUDGMENT=stub .venv/bin/python -m pytest -q
git diff --check
```

## Historical verification at the end of ticket 11

- Judgment public-seam tests: **55 passed**.
- Full offline suite: **391 passed, 3 optional skips**.
- Mypy: **19 source files, zero errors**; diff checks clean; Graft refreshed.
- Standards: no hard violations, two optional heuristics retained.
- Spec: one coercion defect fixed with seven red→green cases; independent follow-up
  confirmed resolution. No live calls or Hermes changes.
- Evidence and public APIs: `docs/judgment-ticket11.md`.

## Historical verification at the end of ticket 10

- Focused generation/conformance/reference tests: **98 passed**.
- Full offline suite: **336 passed, 3 optional skips**.
- Mypy: **19 source files, zero errors**; diff checks clean; Graft refreshed.
- Both review axes found the same unordered-state strict-comparison bug, fixed
  with red→green public-seam regressions. Independent follow-up: Standards
  **0 new findings**, Spec **0 outstanding findings**.
- Evidence and public APIs: `docs/generation-ticket10.md`.

## Historical verification at the end of ticket 09

Implementation: `cc10740`; review improvement and evidence: `027efa0`.
Approved review baseline: `e6c1c9bc3d7920c518f210e05bcc271b685eebb8`.

- `tests/test_reference.py`: **26 passed**.
- Full offline suite: **264 passed, 3 optional skips** (two live Jev tests and the
  real Hermes loader check).
- Mypy: **17 source files, zero errors**.
- Parallel review: Standards **0 hard violations**, one optional duplication
  improvement addressed; Spec **0 actionable findings**.
- Focused tests, mypy and full suite rerun after the improvement; diff check clean
  and local Graft graph refreshed. No live calls or Hermes changes.

```bash
.venv/bin/python -m pytest -q tests/test_reference.py
.venv/bin/python -m mypy agent_lab
AGENT_LAB_JUDGMENT=stub .venv/bin/python -m pytest -q
```

## Remaining product work

See `ROADMAP.md` for ordered milestones and their completion evidence. Most of the
full generator and user-facing product remains: expansion beyond restricted
generation/conformance, arbitrary Judgment vocabularies, Gate and generated
parallel/resume support, spec/bundle approvals,
regeneration, roles/data/skills, questionnaire/visual surface, second runtime
and end-to-end dogfooding. There is no credible completion percentage or delivery
estimate yet; later milestones are not sized implementation tickets.

The product spec `.scratch/workflow-generator/spec.md` describes the whole product,
not current implementation authorization. It has stale introductory/out-of-scope
wording (for example, “No ADRs exist yet” and questionnaire/skill-policy language).
Use the later explicit decisions in `CONTEXT.md` and ADRs, plus approved ticket
contracts; do not interpret stale wording as new scope permission.

## Boundaries and decisions still owned by Adam

- Hermes source, configuration, authentication and live application state remain
  read-only. Outputs go to a caller-named project directory/tool store.
- Persistent spec serialization and distribution/packaging remain deferred behind
  the internal-versus-community decision. Naming remains undecided.
- Whether gated Hermes writes are ever added remains open. Producing a generated
  artifact does not authorize installing or activating it inside Hermes.
- UI versus TUI can be chosen later; the core remains the spec/conformance seam.
- The existing business approval binds run/draft, **not** a spec/bundle pair.
- Shared accounting is in-process; logging uses local advisory file locks. Do not
  mix explicit-sequence replay/import appends with active runtime writes.
- Bindings are trusted deterministic local code, not sandboxed code. State
  validators/serializers must support deterministic Python round-trip validation.
- Conformance means structural/behavioral agreement, not semantic correctness,
  proven savings, production readiness or verified least privilege.

## Working-tree care

Before this handoff update there were unrelated local edits to `.gitignore`,
tickets 04 and 09, and `docs/read-only-ticket04.md`, plus untracked `.ignore`,
`AGENTS.md`, `opencode.json` and the ticket-12 issue file. Leave these alone unless
explicitly updating ticket bookkeeping with Adam; inspect `git status` before
staging. Ticket-12 implementation commits deliberately excluded those files.
Do not use `git add -A` or discard user changes.

## Historical evidence pointers

- Foundation promotion: `docs/foundation/README.md` (source lab `ce34093`, repo
  promotion `cddadc6`; ticket 01 closure `a158632`).
- Ticket 02: `docs/foundation/parallel-accounting.md` (`7e1d517`, `c492e93`).
- Ticket 03: `docs/diagnosis-ticket03.md` (`fcfb06c`, `39a2bd2`).
- Ticket 04: `docs/read-only-ticket04.md` (`6271106` and subsequent explicit
  acceptance of installation without protected edits; activation remains separate).
- Ticket 05: `docs/measurement-ticket05.md` (`3106982`, `7abde37`).
- Ticket 07: `docs/typechecking-ticket07.md` (`2077d7d`, `12db524`).
- Ticket 06: `docs/report-ticket06.md` (`ea50593`, `c4af4d3`, `f6b9c49`).
- Ticket 08: `docs/spec-ticket08.md` (`98f555a`, `abfe1e8`; closure `e6c1c9b`).
- Ticket 09: `docs/reference-ticket09.md` (`cc10740`, `027efa0`).
- Ticket 10: `docs/generation-ticket10.md` (`568ad14`, `0855f25`, `03f1af3`); accepted.
