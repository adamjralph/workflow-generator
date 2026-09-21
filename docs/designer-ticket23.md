# Ticket 23 — completed-pair offline conformance

Implementation of [ticket 23](../.scratch/workflow-generator/issues/23-check-completed-workflow-through-offline-replay.md).
**Accepted and closed:** Adam explicitly accepted ticket 23 ("accept").

Adam approved implementation, public replay/HTTP/Chromium/network-denying seams and
review baseline `101aa2f21075e89f4c878923ad8e543e7900a9fb`. ADR 0010 and the ticket-19
execution/replay contract remain authoritative. Ticket-23 acceptance does not close
parent 19 or authorize a live smoke.

## Operator use

Use the existing [ticket-22 setup](designer-ticket22.md). After a completed Generator
and Guardian run, choose **Check completed pair (offline)**. Approved, Changes requested
and Blocked Guardian verdicts are all eligible. Generator-only, Generator-blocked,
failed, partial, running and uncertain attempts are not completed pairs.

Check displays fresh case-scoped conformance separately from the original editorial
result. It preserves the Guardian verdict, attributes the check to the snapshot,
run request and receipt digest, and labels recorded usage as historical, not new or
rebilled calls. Model calls and authentication requests for Check are zero. A pass
is not post quality, provider authenticity, publication permission or a new review.

Repeated Check creates fresh independent evidence, not a new run identity or paid
work. Recapture, mode changes and requesting another run invalidate the displayed
check and any late success/error response. These actions never delete existing
private evidence or cancel prior paid work. There is no historical-run browser list;
a retained completed identity can be checked again through the protected HTTP API,
including after server restart with different or unavailable live credentials.

## Public seams and evidence

- `DraftChecks(source, evidence_dir).check(snapshot, run_request)` reads only the
  immutable capture and private run evidence. It accepts no model source, credential
  configuration or live transport. The existing server still needs its operator
  manifest at startup; Check itself does not reread original source/guidance/profiles.
- Protected `POST /api/drafts/check` accepts exactly `{snapshot, run_request}`.
  Existing exact loopback Host/Origin/token, bounded JSON and strict field/identity
  checks apply. The browser cannot supply paths, prompts or executable bindings.
- Preflight verifies canonical version-2 receipt, complete digest membership,
  request/claim identity, current operation/schema versions, pinned historical
  execution options, reservations, ordered exchanges, exact requests and sanitized
  responses. It validates strict editorial results, exact draft/review bindings,
  usage/attribution and the complete deterministic original transition log.
- Fresh recorded sources have separate cursors for reference and candidate, each
  consuming Generator then Guardian by exact request equality. Independent drivers
  prepare requests and execute real response application through existing core
  conformance. Neither returns a stored final state as its execution result.
- The checker also requires consumption of both exchanges, the recorded completed
  result and complete semantic replay logs. Driver agreement on missing events or
  on failure cannot become a completed-pair pass. Live elapsed time and provider
  metadata remain historical provenance, not values regenerated during replay.
- Each Check writes a private `draft-check-*/check.json`; successful execution also
  retains separate fresh reference/candidate logs under that check directory.
  Invalid recordings produce a sanitized failure receipt without executing either
  driver. Existing captures, receipts and partial records are not modified.
  Evidence publication failure cannot return a pass. No resume or live fallback.
- Trusted Python `candidate_factory` injection tests altered preparation,
  application, structure and unused/exhausted sources. It is not exposed through
  HTTP and is trusted code, not a sandbox. Hashes provide local integrity bindings,
  not signatures or protection against an owner rewriting an entire history.

## Offline verification

Final full offline suite: **1,544 passed, 3 expected skips**, including real Chromium
and all **72 new ticket-23 tests** (52 replay, 9 HTTP, 11 Chromium). Skips are two
opt-in live Jev checks and the optional real Hermes plugin-loader check. Console:
`/tmp/workflow-ticket23-full-suite-final.txt`. Mypy: **34 source files clean**.
JavaScript syntax and whitespace checks pass; Graft refreshed. No production changes
followed the final suite. Implementation commit: `7aee160`.

The first full run found one stale capture-era assertion expecting the Check route
to be absent. It now checks that Run, request creation and Check require identities,
while the unsupported load route remains absent. The focused capture HTTP file
passed **43 tests**, then the entire suite was rerun successfully. This test-only
adjustment followed independent review and changes no production behavior.

Red-first cycles covered the new seam/HTTP/browser action, corrupt or incomplete
recordings, unused and caught-extra candidate source invocations, a replaced
evidence-root symlink and lost replay audit writes. Network-denying checks run with
original inputs removed and reject any file access outside immutable evidence;
existing evidence bytes, modes and modification times remain unchanged. Earlier
focused new/ticket-22 regression checks passed 104 tests, before the final caught-extra
invocation regression was added. The final suite includes that additional regression.

## Standards

Independent review of `101aa2f...7aee160`: **0 documented-standard violations**;
2 optional duplication heuristics (historical limit encodings and repeated completed-
pair browser setup). Both remain deliberately deferred. Explicit historical evidence
shapes and literal test setup are retained rather than expanding this slice into a
policy-abstraction or test-helper refactor.

## Spec

Independent review: **0 actionable implementation findings or scope creep**; the
reviewer independently reran all **52 core replay tests** successfully. The pending
full-regression acceptance gate noted by the reviewer is now satisfied by the final
suite above. The subsequent stale route assertion update was not independently
re-reviewed; it changes no production behavior.

**Review summary:** Standards 0 hard / 2 optional heuristics; Spec 0 actionable.
Adam accepted ticket 23; this slice is closed. Parent 19 remains open. No production captures, real credential-content reads or live auth/model calls
were used. Live provider availability and editorial quality remain unverified.
