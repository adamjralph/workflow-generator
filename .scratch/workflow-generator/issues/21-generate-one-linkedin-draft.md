# 21: Generate one LinkedIn draft with Signal Generator

**Type:** task
**Parent:** 19: Refine and review the oldest unprocessed LinkedIn draft

**What to build:** Explicit Run on a captured input produces one useful LinkedIn post with Signal Generator, or a visible blocked/failure result, with immutable exchange evidence and usage. The browser clearly marks the result as not reviewed. Introduce explicit model operations through the existing independent execution drivers as part of this usable workflow, not as a separate horizontal refactor.

**Blocked by:** 20: Capture and preview the oldest eligible draft.

**Status:** ready-for-human

## Readiness

Adam approved all outstanding decisions and confirmed proceeding with the existing
Hermes Codex subscription login read-only. ADR 0010, the complete execution/replay
contract, ticket-20 authority manifest, 180-second/64-KiB/3,000-code-point bounds,
duplicate/uncertain policy and public seams are approved. Review baseline:
`f0e0eded07dfe6f7b0d91424a40d46d3ca036da6`. Credential source defaults explicitly to
`~/.hermes/auth.json` (operator override only), with no refresh, discovery or writes.
Configured defaults and no retries remain mandatory. Local bounds promise neither
remote cancellation nor capped spend. Live smoke still requires separate explicit
authorization and a named destination.

## Acceptance criteria

- [x] Browser Run uses the captured source, approved authority and configured Generator default to return a structured post, reader/one-point note, source/claim support and limitations, or an explicit blocked result. It never invents a review.
- [x] Explicit model-operation bindings separate deterministic prepare/apply from a declared live, fixture or recorded source. Ordinary Transform callables remain deterministic; Judgment is unchanged.
- [x] Admission and actual-candidate inspection distinguish operation identity/version and reject ambiguous, unbound or unsupported declarations before invocation. Both existing drivers independently execute prepare/source/apply; neither delegates control flow to the other.
- [x] A dedicated tool-free Codex adapter uses only the approved read-only existing valid token mechanism, without refresh, credential locks/recovery writes, fallback, auxiliary calls or Hermes sessions. Missing/expired credentials require operator action.
- [x] Reserve the workflow step and durable attempt before invocation. This slice makes at most one Generator request, with no retries or repair calls; enforce approved local deadlines/response bounds without claiming a universal token/spend cap or remote cancellation.
- [x] Exclusively claim an opaque input-bound run request before paid work. Duplicate/concurrent submissions return existing status; interruption with incomplete evidence remains uncertain and is never automatically resent or resumed.
- [x] Persist exact replayable sanitized request/response evidence, operation/schema versions, input digests, effective options, provider metadata and separate usage fields before applying a response. Unknown usage stays unknown; secrets never reach logs, artifacts or browser output.
- [x] Browser displays not reviewed, blocked, failed and uncertain states distinctly; invalid output, timeout or audit/storage failure cannot become successful completion. Stale responses cannot replace current UI state.
- [x] Fixture/injectable-transport tests exercise real independent drivers and literal outcomes; actual HTTP and real Chromium tests cover Run, duplicates, failures and inert rendering. Offline tests do not require live credentials or calls.
- [x] Sources, eligibility and Hermes remain unchanged; preserve existing designer behavior. Agreed offline checks, typechecking and independent review pass.

## Scope boundary

Evidence must support the agreed later exact-request replay contract, but the completed-pair Check action is delivered in ticket 23. No Guardian review, publishing, automatic revision, general durable resume or exactly-once remote-delivery claim. Ticket 19 is not complete when this slice lands.

## Answer

Implemented in `3bf1bf9`, with review fixes in `56438c6`. Full operator instructions,
evidence boundaries and verification: [ticket-21 delivery record](../../../docs/designer-ticket21.md).
Full offline suite: **1,331 passed, 3 expected skips**, including real Chromium;
mypy **31 source files clean**. Independent Standards review: 0 hard findings,
1 deferred fixture-naming heuristic; independent Spec follow-up: 0 outstanding
actionable findings. Review fixes were reproduced red-first.

Ready for Adam's acceptance. No production captures, real credential reads, live
model calls or Hermes writes occurred. Live authentication/model availability and
post quality are unverified, not implied by offline tests. A live smoke still
requires explicit approval and a named destination. Tickets 19, 22 and 23 remain
outside this completion claim.
