# 11: Execute and check recorded Judgment routes

**Type:** task
**What to build:** A caller authors a spec containing a Judgment node using the existing Intervention vocabulary, generates a runnable graph, and checks its routing and full recorded judgment evidence against an independently compiled plain reference, entirely offline. Conforming cases pass; altered choices, confidence/probability evidence, routes, or behavior cannot silently pass. This extends the accepted Transform/Decision + Route loop, not the full executable language.

**Blocked by:** None (can start immediately). Tickets 09–10 are accepted and closed; Adam approved this ticket's granularity, contract, public test seam and review baseline.

**Status:** resolved

**Implementation:** complete; accepted and closed by Adam. Verification and independent
Standards/Spec review: [`docs/judgment-ticket11.md`](../../../docs/judgment-ticket11.md).
**Review baseline:** `467f1b2f7e76f8288892650c0bdf70462df0598b`

## Approved contract

- Restrict executable Judgment options to the existing Intervention vocabulary. Arbitrary Judgment options remain valid conceptual declarations but are unsupported by this execution target. Reject unsupported options before execution, including unreachable declarations.
- Supply explicit Judgment bindings keyed by node identity: a judgment source plus a deterministic typed-state-to-assessment adapter. No implicit environment-selected source. Compilation checks required bindings without invoking adapters or sources.
- Obtain judgments through the existing judgment-source boundary, preserving existing business-source behavior. Judgment routes on its validated intervention, which must be among the node's declared options. No coercion or fallback routing.
- Preserve the full validated judgment in audit evidence, including choice, confidence, review-gap probability and source provenance. Judgment leaves workflow state unchanged; writing judgment results into arbitrary caller state is deferred.
- Retain the accepted frozen typed-state, detached snapshots, copied declarations/binding maps, all-declaration checking and safety-terminal contracts. Explicit bindings remain trusted local code, not a sandbox.
- Reserve one budget step before calling the source. Budget refusal records FAILED_BUDGET without calling the source or overspending. Invalid judgments and ordinary adapter/source failures record FAILED_VALIDATION. Terminal routing is free and stopping prevents later work.
- Conformance uses explicitly supplied recorded/stub sources with equivalent inputs for the two drivers. Do not call Jev live, share a consumable replay cursor, or normalize away differing judgment evidence. Independent executions must have independent replay progress where a source is stateful.
- Extend plain reference execution, graph generation and checking together. The plain control loop remains authoritative; graph control flow must not delegate to the whole plain runner.
- Inspect actual candidate execution configuration, including Judgment options and all declarations. Structural mismatches prevent behavioral execution. Execute the independently supplied candidate rather than regenerating a replacement.
- Retain same-run-ID execution in separate fresh logs, strict final-state comparison, terminal/spend comparison, every ordered persisted event field, exact raw log bytes and raw-log digests. Full judgment evidence participates in comparison.
- Preserve explicit freshness/input errors and audit stopping. Incomplete persistence cannot produce a passing report; unexpected programming errors must not be hidden as ordinary mismatches. Evidence stays in caller-named permitted locations outside Hermes.
- A passing check is structural and behavioral evidence for this restricted target and supplied cases, not semantic correctness or universal conformance.

## Acceptance criteria

- [x] A hand-authored Judgment workflow generates and executes through distinct declared Intervention routes and passes checking against the independent plain reference using recorded/stub sources offline.
- [x] Explicit node-identity Judgment bindings and deterministic assessment adapters work through the public APIs; compilation invokes neither. Missing or unsupported declarations/bindings, including unreachable ones, produce no runnable artifact or passing report.
- [x] Full validated judgment evidence is persisted and compared; Judgment does not modify retained workflow state or the caller's input.
- [x] Malformed or unchecked-invalid judgments, undeclared returned choices, ordinary source/adapter failures and recording/input mismatches produce recorded FAILED_VALIDATION outcomes with agreement between drivers.
- [x] Short/exact budgets, refusal before source invocation and immediate terminal stopping agree between drivers without extra calls or overspend.
- [x] Changed Judgment options or routing produce located structural findings before execution; matching structure with altered judgment choice, confidence/probability evidence or other behavior cannot silently pass.
- [x] Paired executions have independent replay progress and equivalent explicit offline inputs. Repeated checks reproduce exact evidence under the existing same-ID/separate-fresh-log contract.
- [x] Real filesystem failures prove audit stopping, no later work and no passing report after incomplete persistence. Existing evidence-location protection and freshness behavior remain intact.
- [x] Existing admission, Transform/Decision reference/generation/conformance, diagnosis and business judgment-source/driver behavior remains green.
- [x] Focused public-seam tests and mypy run during implementation; final verification includes the full offline suite, diff checks and independent Standards/Spec review against the approved baseline. Use scoped commits, preserve unrelated user changes and refresh Graft after substantial code changes.

## Approved public test seam

Authored spec + independently supplied candidate + explicit reference bindings/judgment sources + named typed cases → typed conformance report + real persisted logs.

Tests and callers use the same public interface. Hand-authored expected routes, recorded/stub judgments and deliberately altered candidates are fixtures. Private compiler/dispatch mocks are not the acceptance seam. Use real temporary filesystem failures to prove audit stopping. No live calls are authorized.

Any small shared-invocation prefactor lands first inside this ticket with existing behavior preserved. Do not split reference execution, generation and checking into separately claimed milestones or introduce an unrelated generalization of the judgment-source boundary.

## Out of scope

Arbitrary judgment vocabularies, generalized judgment-source redesign, storing Judgment output into arbitrary caller state, live Jev calls, Gate/Loop/Fork execution, resume, durable checkpoints, persistent spec serialization, spec/bundle identity and approvals, questionnaire/UI, role/data/SOUL/skill generation, packaging, Hermes writes or activation changes, universal correctness and savings claims.

## Implementation result

Implemented in `2e9848e`; strict-validation review fix in `cfa2151`.
All acceptance criteria have implementation/test evidence in
`docs/judgment-ticket11.md`. Final offline suite: **391 passed, 3 skipped**;
mypy: **zero errors** across 19 source files. Graft refreshed and diff checks clean.
Independent Standards review: no hard violations, two optional heuristics retained.
Independent Spec review: one coercion defect reproduced and fixed; follow-up
confirmed resolution. No live calls, Hermes writes, or unrelated user changes committed.

## Acceptance

Adam explicitly accepted the completed implementation and review results: “accept”.
Ticket 11 is accepted and closed. This does not authorize later roadmap work.

## Comments

Adam approved the single-ticket granularity and absence of blocking tickets, then requested an explanation of the restricted contract, public test seam and review baseline. The explanation distinguished the spec's arbitrary option declarations from the existing source's business-specific Intervention vocabulary, public observable-behavior testing from internal mocks, and the fixed starting commit for Standards/Spec review. Adam then explicitly confirmed: “yes, approved”. This approves publication of this restricted ticket. Later roadmap milestones remain outlines, not authorized implementation scope.
