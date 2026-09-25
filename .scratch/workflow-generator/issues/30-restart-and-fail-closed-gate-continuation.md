# 30: Restart and fail closed from a committed Gate pause

**Type:** task
**Status:** planning-ready (ticket 29 accepted; implementation requires Adam's separate go)
**Blocked by:** No longer blocked by 29, which Adam accepted on 2026-09-25. Authorization to implement 30 remains separate.
**Capability:** Completes the bounded P17 restart promise, subject to verification and Adam's acceptance; not arbitrary mid-step exactly-once execution.
**Contract:** Accepted D2 Gate identity contract and ADR 0012.
**Review baseline:** `4dddff4be891923452bdfdc06bc5f3e3340a10fd` is the repository HEAD at ticket publication, not the eventual implementation base. At start, record the accepted ticket-29 source/evidence hash and current working-tree diff; independent reviewers must assess this ticket's frozen delta against that actual base.

**What to build:** After a workflow durably pauses at a Gate, the operator decides through the scoped local CLI, exits, and starts a fresh process. The new process loads the retained immutable version and committed pause from the caller-named store, claims that run exclusively, verifies artifact identity and the decision/event chain, then executes only remaining work. Repeated or concurrent resume cannot repeat a step, charge the Gate again, or silently inherit approval; corruption and ambiguous crash states stop before downstream work. The reference and emitted graph remain independently checkable offline.

**Public test seam:** The ticket-29 authored Route/Gate workflow and frozen registered operations + externally stored artifact/checkpoint/decision/event receipts + fresh process boundary + independent offline approvals and typed cases → final state, canonical event/budget comparison, recovery receipt and conformance report. Expose deterministic crash/write-failure injection at declared commit boundaries; no live model/tool calls or Hermes writes.

## Acceptance criteria

- [ ] A real fresh process reconstructs the same admitted executable identity and post-Gate state from retained bytes, with no arbitrary entry or caller-reconstructed state, and completes only the approved remainder. Hand-authored expected state, exact spent/remaining budget and canonical event chain match independently running plain and emitted-graph drivers and offline conformance.
- [ ] Define atomic publication/recovery ordering for immutable artifacts, event chain, committed pause/checkpoint and decision; prove with crash injection at each relevant boundary which evidence is committed and which state is indeterminate. A mid-step in-flight crash is never automatically replayed, and this ticket makes no exactly-once claim for arbitrary effects.
- [ ] Per-run exclusive continuation claim prevents concurrent or duplicate resumes. Repeated resume adds no step, event or effect; conflicting decision/claim fails closed. Approval is consumed for exactly the original run/Gate/pause and cannot transfer to a later visit or altered version.
- [ ] Missing, torn, truncated or corrupt artifact, spec, bundle, binding/config/dependency, checkpoint, decision or event-chain evidence; forged/stale identity; wrong run/Gate/pause; and conflicting/late decisions are rejected before downstream work. Re-derive identities at recovery rather than trusting stored digest fields.
- [ ] Audit-write and checkpoint/decision commit failures do not report successful continuation or execute downstream work. Tests distinguish a committed pause eligible for recovery from an ambiguous partial write or in-flight step that requires explicit resolution/new run.
- [ ] Independent Standards and Spec reviews inspect frozen final source and evidence, blockers are resolved, and focused/type/full offline validation is read back before proposing P17 acceptance. Record exact baseline/hash and any remaining limitations; no build, commit, push or live call follows from publication of this ticket.

**Out of scope:** Gate inside a Fork or between waves, regeneration, live model/tool side effects, general arbitrary-crash exactly-once replay, person-level authentication, public persistent spec serialization. A separate explicit implementation go is required.
