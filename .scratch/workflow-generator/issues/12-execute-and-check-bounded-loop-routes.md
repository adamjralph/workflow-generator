# 12: Execute and check bounded Loop routes

**Type:** task
**What to build:** A caller authors a bounded retry spec, executes its plain reference and independently generated graph entirely offline, and checks that exit, repeat, exhaustion, failure and budget behavior agree with exact persisted evidence. This extends the accepted Transform/Decision/restricted Judgment + Route target through reference execution, graph generation and conformance together.

**Blocked by:** None (can start immediately). Tickets 08–11 are accepted and closed. Adam approved this ticket's granularity, absence of blockers, Loop semantics, public test seam and review baseline.

**Status:** accepted and closed

**Review baseline:** `5038a372780171b892b057be150baf7fb2f0dd8d`

## Approved contract

- Resolve each Loop's `exit_predicate` through explicit caller bindings, using its exact opaque reference. The deterministic callable receives a detached snapshot of the declared frozen typed state and must return a strict boolean; do not coerce truthy values or evaluate references as imports or expressions.
- Validate and copy declarations/binding maps before execution. Check all declarations, including unreachable ones, without invoking predicates or other bindings. Missing/invalid bindings produce located findings and no runnable artifact.
- Every Loop visit reserves one run-budget step before evaluating its predicate, including visits that exit, exhaust the repeat allowance or fail validation. Budget refusal records FAILED_BUDGET without invoking the predicate or overspending. Terminal routing remains free.
- Predicate true selects `exit`, including after the repeat allowance has been consumed. Predicate false selects `repeat` while allowance remains, otherwise `exhausted`.
- `max_iterations` caps repeat traversals per Loop node per run, not predicate evaluations or total body-node invocations. Increment the counter on each selected repeat traversal. Counters never reset on re-entry and are independent for distinct Loop identities. Each fresh run starts with zero counters.
- Loop itself leaves retained workflow state unchanged. Body nodes perform transformations through the existing typed-state contract. Predicate snapshot mutations cannot change retained state or caller input.
- Invalid predicate results and ordinary predicate exceptions record FAILED_VALIDATION. Preserve existing immediate terminal stopping and audit-failure stopping.
- Extend the authoritative plain control loop, actual graph execution and checking together. Graph control flow must not delegate to the whole plain runner; shared invocation/accounting/audit mechanics may remain shared.
- Inspect actual candidate execution configuration, including Loop bounds, predicate references, routes and unreachable declarations. Structural differences prevent behavioral execution. Execute the independently supplied candidate rather than regenerating a replacement.
- Persist deterministic Loop counter/routing evidence sufficient to verify consumed repeat allowance. Compare it alongside strict final state, terminal, spend, every ordered persisted event field, exact raw log bytes and raw-log digests. Retain same-run-ID execution in separate fresh logs.
- Preserve explicit freshness/input errors, evidence-location protection and visible audit failures. Incomplete persistence cannot produce a passing report; unexpected programming errors must not be hidden as ordinary mismatches.
- Retain restricted Judgment support and independent explicit offline sources when Judgment appears inside retries. No live calls are authorized.
- A passing check is structural and behavioral evidence for the supported target and supplied cases, not semantic correctness or universal conformance.

## Acceptance criteria

- [x] A hand-authored retry spec generates and runs through reference and graph drivers, with matching early exit, repeated body execution and exhausted routing verified through conformance.
- [x] Strict boolean predicate bindings work through public APIs without compilation-time invocation. Missing bindings, invalid declarations and unsupported declarations, including unreachable ones, return located findings without a runnable artifact or passing report.
- [x] Boundary cases prove zero repeats on immediate exit, exactly the declared maximum repeats, exit taking precedence when the predicate becomes true after the last allowed repeat, and exhaustion when it remains false.
- [x] Multiple Loop identities retain independent per-run counters; re-entry does not replenish allowance, and fresh runs do not inherit counters.
- [x] Loop does not alter retained state or caller input; body transformations and predicate snapshot isolation retain the accepted typed-state behavior.
- [x] Invalid predicate results, ordinary predicate failures, short/exact budgets and immediate terminal stopping agree between drivers without coercion, extra predicate calls or overspend.
- [x] Offline Judgment within retries preserves independent replay progress and full judgment/input evidence across both drivers.
- [x] Altered candidate Loop bounds, predicate references or routes produce located structural findings before execution; matching structure with altered predicate behavior cannot silently pass.
- [x] Hand-authored expected routes and repeat counts independently constrain behavior, rather than treating driver agreement alone as evidence of the intended Loop semantics.
- [x] Loop counter/routing evidence, strict final state, terminal/spend, ordered events, exact log bytes and digests agree under the same-ID/separate-fresh-log contract; repeated checks with fresh equivalent inputs reproduce the evidence.
- [x] Real temporary-filesystem failures prove audit stopping, no later work and no passing report after incomplete persistence. Existing evidence-location and run-freshness protections remain intact.
- [x] Existing admission, reference/generation/conformance, diagnosis and business-driver behavior remains green; unsupported Gate/Fork/resume behavior remains fail-closed.
- [x] Focused public-seam tests and mypy run during implementation; final verification includes the full offline suite, diff checks and independent Standards/Spec review against the approved baseline. Preserve unrelated user changes, use scoped commits and refresh Graft after substantial code changes.

## Approved public test seam

Authored spec + explicit bindings + independently supplied candidate + named typed cases → typed conformance report + real persisted logs.

Tests and callers use the same public interface. Hand-authored expected counts/routes, independent offline Judgment inputs and deliberately altered candidates are fixtures. Private compiler/dispatch mocks are not the acceptance seam. Use real temporary-filesystem failures to prove audit stopping.

No separate broad prefactor is planned. Any small necessary behavior-preserving prefactor lands first within this ticket; do not split reference execution, generation and checking into separately claimed milestones.

## Out of scope

Gate or Fork execution, parallel scheduling/reducers, pause/resume, durable checkpoints, persistent spec serialization, spec/bundle identity and approvals, arbitrary Judgment vocabularies, generalized judgment-source redesign, live calls, questionnaire/UI, role/data/SOUL/skill generation, packaging, Hermes writes or activation changes, universal correctness and savings claims.

Gate/resume requires coordinated planning with artifact identity and approval work. Parallel execution needs its own reducer, scheduling and evidence contract. Neither blocks this slice, and neither is authorized by it.

## Comments

Adam approved the proposed single-ticket breakdown with no blockers, the strict-boolean predicate contract, per-node/per-run repeat bounds without re-entry resets, the public observable-behavior test seam and review baseline: “approved”. Implementation and review evidence landed in `597d315` and `c0a2760`; see `docs/loop-ticket12.md` (423 offline tests passed, 3 optional skips; mypy clean; independent Standards/Spec review). Adam subsequently confirmed acceptance and closure: “confirm 12”. Tickets 01–12 are accepted and closed. Later roadmap work remains unapproved.
