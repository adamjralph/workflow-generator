# Ticket 23 — completed-pair offline conformance

Implementation of [ticket 23](../.scratch/workflow-generator/issues/23-check-completed-workflow-through-offline-replay.md).
Adam approved implementation, public replay/HTTP/Chromium/network-denying seams and
review baseline `101aa2f21075e89f4c878923ad8e543e7900a9fb`. ADR 0010 and the ticket-19
execution/replay contract remain authoritative. Acceptance remains Adam's decision;
this does not close parent 19 or authorize a live smoke.

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

## Verification in progress

Focused new and ticket-22 regression checks: **104 passed**, including real Chromium.
Mypy: **34 source files clean**. JavaScript syntax and whitespace checks pass.
Red-first cycles covered the new seam/HTTP/browser action, corrupt or incomplete
recordings, unused candidate exchanges, a replaced evidence-root symlink and lost
replay audit writes. Network-denying checks run with original inputs removed and
reject any file access outside immutable evidence; existing evidence bytes, modes
and modification times remain unchanged.

Independent Standards/Spec reviews and final full offline regression are pending.
No production captures, real credential-content reads or live auth/model calls
were used. Live provider availability and editorial quality remain unverified.
