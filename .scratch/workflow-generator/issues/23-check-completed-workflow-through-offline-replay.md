# 23: Check the completed workflow through offline replay

**Parent:** 19: Refine and review the oldest unprocessed LinkedIn draft

**What to build:** Browser Check validates a completed draft/review recording and independently executes the plain reference and actual generated candidate against exact request-bound recorded responses. Show case-scoped conformance without contacting a model or creating a new editorial review.

**Blocked by:** 22: Independently review the exact draft with Signal Guardian.

**Status:** claimed

## Readiness

Adam explicitly approved ticket-23 implementation, the public HTTP/browser, independent replay and network-denying test seams, and review baseline `101aa2f21075e89f4c878923ad8e543e7900a9fb`. Ticket 22 is accepted and closed, satisfying the dependency. ADR 0010 and the complete execution/replay contract are already accepted; inherit the settled capture/run/evidence rules without reopening them. Tests also cover candidate drift, corrupt/partial/unused recordings and preservation of ticket-18 behavior. Retain independent Standards/Spec reviews, typechecking and final full offline regression. No live calls or credential loading are needed or authorized for replay. Implementation readiness is not completion or acceptance of ticket 23 or parent 19.

## Acceptance criteria

- [ ] Check validates the captured input, completed-pair receipt, operation/schema versions, referenced digests and exchange ordering before execution. Failed, partial or uncertain runs cannot masquerade as completed pairs.
- [ ] Reference and actual generated candidate use independent fresh recorded sources and independently prepare requests and apply validated responses. No stored final-state substitution, reference-driver delegation or shared mutable replay cursor.
- [ ] Supply each response only for its exact operation, ordinal and canonical request identity, including role, configured model, semantic options, captured authority and Guardian's exact draft input.
- [ ] Missing, corrupt, reordered, duplicate, wrong-request, exhausted or unused exchanges fail visibly. Deliberately altered candidate preparation, application or execution configuration fails even with otherwise valid recordings.
- [ ] Existing conformance checks compare actual structure, state, routes, budgets and deterministic event/log evidence. Fresh replay logs agree without requiring live transport timestamps or latency to be regenerated.
- [ ] Replay has no live transport, credential loading, network fallback or source rediscovery; a network-denying test proves zero model/auth calls.
- [ ] Browser Check reports fresh conformance evidence attributed to the captured run, separately from Guardian's verdict and publication authority. Historical usage is not rebilled or presented as new paid calls.
- [ ] Actual HTTP tests protect capture/recording identities and existing request boundaries; real Chromium tests cover successful replay, corrupt evidence, stale responses and inert result rendering.
- [ ] Preserve inspectable failure evidence, read-only sources/Hermes and existing ticket-18 behavior. Literal fixtures test failure semantics without claiming failed live runs succeeded.
- [ ] Agreed full offline regression, typechecking and independent Standards/Spec review pass. Evidence distinguishes fixture coverage from any separately authorized live smoke; parent acceptance remains Adam's decision.

## Scope boundary

Replay proves restricted, case-scoped structural/behavioral agreement, not post quality, provider authenticity, capped spend or publication permission. No new model calls, source eligibility changes, revisions, general resume or automatic closure of ticket 19.
