# 10: Generate and check the deterministic reference slice

**Type:** task
**What to build:** A caller supplies a hand-authored Transform/Decision + Route
spec, generates an executable pydantic-graph candidate, runs it offline, and checks
its actual structure and observed behavior against the authoritative plain
reference. A branching example passes; deliberately altered candidates fail with
located typed findings. This proves the smallest complete generation/checking
loop, not the complete product.

**Blocked by:** None (can start immediately). Ticket 09 is accepted and closed;
Adam approved the contract, public test seam and review baseline below.
**Status:** resolved — accepted and closed
**Review baseline:** `3efdbd096cbdf3385570c3ecd179354c55c3aa84`

**Sources:** [roadmap](../../../ROADMAP.md), [handoff](../../../HANDOFF.md),
[product spec](../spec.md), [reference contract](../../../docs/reference-ticket09.md),
[admission contract](../../../docs/spec-ticket08.md),
[domain context](../../../CONTEXT.md),
[ADR 0001](../../../docs/adr/0001-conformance-is-structural-and-behavioural.md),
[ADR 0004](../../../docs/adr/0004-spec-is-a-typed-directed-graph.md),
[ADR 0007](../../../docs/adr/0007-node-types-compile-through-a-fixed-mapping.md),
[ADR 0008](../../../docs/adr/0008-conformance-pins-the-plain-driver-as-reference.md).

## Approved artifact and execution contract

- Generate an in-memory executable pydantic-graph artifact. No generated files,
  persistent bundle, persistent spec format, packaging or spec/bundle digest is
  selected by this slice.
- Each spec node maps to graph execution. Graph control flow selects subsequent
  nodes; the graph must not delegate execution to the whole plain runner.
- Inspect the candidate's actual executable topology/configuration, not a copied
  authoritative spec or an independently claimed manifest. Structure checked and
  structure executed must belong to the same candidate.
- Retain ticket 09's frozen Pydantic state, Transform-result, explicit binding,
  detachment, all-declaration checking and safety-terminal contracts. Check even
  unreachable declarations. References remain opaque keys, never imports/eval.
- Bindings are trusted deterministic local code, not sandboxed code. Compilation
  does not invoke them. Copy declarations and binding maps rather than allowing
  later caller mutation to redirect execution.
- Reuse foundation step reservations, Budget, append-only event allocation and
  fresh-run policy. Every attempted binding reserves one step; refusal invokes no
  binding and does not overspend. Terminal routing is free.
- Binding exceptions and invalid results record FAILED_VALIDATION; reservation
  refusal records FAILED_BUDGET. Terminal stopping prevents further work.
- A small internal prefactor may extract shared snapshot, node-invocation and
  audit mechanics first, preserving existing behavior. Keep the plain control
  loop authoritative and separate from graph control flow. No separate prefactor
  ticket or competing scheduler/event writer is needed.

## Approved public interface

The generation operation, named generate_graph, accepts a spec, state_type and
explicit bindings. It returns a runnable candidate or located compilation
findings, never a partially runnable candidate on failure.

The candidate's run operation accepts an initial state, run_id and RunLog. It
returns final state, terminal, used steps and the persisted trace, retaining the
reference execution's failure and freshness rules.

The checking operation, named check_conformance, accepts the authoritative spec,
an independently supplied candidate, state_type, reference bindings, named cases
and a caller-named evidence_dir outside Hermes. Each case supplies one typed
initial state. The checker compiles its own plain reference from the authoritative
spec and reference bindings; it never derives its reference from the candidate.
An altered candidate can be supplied without mocking the checker.

The typed report identifies cases attempted/completed, evidence locations and
located findings. Passing requires a nonempty case set, structural agreement and
agreement on every supplied case. A compilation failure, unsupported candidate,
structural/behavioral mismatch or incomplete execution cannot pass.

## Approved comparison and evidence contract

Before invoking bindings, compare entry, all node identities/types, operation/value
references, outcome vocabularies, routes, terminals and budget. Compare all
structure, including unreachable declarations. Ignore declaration ordering where
it has no execution meaning. Structural mismatch prevents behavioral execution.

For each named case, execute both drivers using the same run ID in two separate,
fresh logs. Run identity is scoped to a log under the existing reference contract.
This permits literal equality without defining a normalized-trace digest.

Compare strictly validated final state, terminal, used steps, every ordered event
field (including sequence, selected route, target, failure and budget values),
exact audit-log bytes and the existing RunLog.digest values. Read persisted
evidence through the public log interface. Digests describe original log bytes,
not spec or bundle identity.

Binding failures and budget refusals are comparable recorded outcomes. Audit
failures stop visibly and cannot yield a passing report or a claim of successful
persistence. Invalid inputs/fresh-run violations retain the existing explicit
error policy. Unexpected programming errors must not be hidden as ordinary
conformance mismatches. Crash durability and recovery are not promised.

A passing report is structural and behavioral evidence for this restricted target
and these supplied cases only. It does not prove arbitrary Python behavior,
universal workflow conformance, semantic correctness, savings or readiness for
production. Model replay and full-product artifact identity remain later work.

## Acceptance criteria

- [x] A hand-authored Transform → Decision spec generates an executable graph,
  exercises distinct routes for distinct typed inputs and passes checking against
  the plain reference, with arbitrary spec node identities.
- [x] Invalid specs, unsupported/unbound declarations (including unreachable
  ones), invalid state types and absent safety terminals produce no runnable
  candidate or passing report; compilation invokes no bindings.
- [x] Changed entry, node type/reference, route, terminal or budget produces
  located structural findings before either driver's bindings execute. Checking
  examines actual executable structure rather than a copied spec assertion.
- [x] A candidate with matching structure but altered binding behavior produces
  behavioral findings. The supplied candidate, not a regenerated replacement,
  is executed and checked.
- [x] Binding exceptions, malformed states/labels, short/exact budgets and
  immediate terminal stopping agree between drivers, with no extra invocation
  or overspend. Empty case sets cannot pass.
- [x] Final state, terminal, spend, ordered persisted events, raw log bytes and
  raw-log digests agree for conforming cases using same-ID/separate fresh logs.
  Repeated deterministic offline executions agree under these rules.
- [x] Input/state detachment, copied binding maps and fresh-run refusal remain
  intact. Audit failure stops later work and cannot yield a passing report.
- [x] Evidence uses real temporary files and public RunLog reading/digest
  operations; the foundation remains the only event sequence allocator.
- [x] Existing admission, reference, diagnosis and business plain/graph behavior
  remains green. Focused TDD and mypy run throughout; final verification includes
  the full offline suite, diff checks and two-axis review against the approved
  baseline, with scoped commits and graph refresh after substantial code changes.

## Approved public test seam

Spec + independently supplied candidate + explicit bindings + typed cases → typed
report + real persisted logs. Tests and callers use the same interface. Tiny
trusted deterministic bindings, hand-authored expected behavior and deliberately
altered candidates are fixtures; private dispatch/compiler mocks are not the
acceptance seam. Use real temporary filesystem failures to prove audit stopping.

Keep this as one complete vertical ticket, sized to one fresh implementation
context. Do not split generation from checking into independently claimed
milestones. Any necessary internal prefactor lands first with existing reference
behavior preserved, then the narrow generation/checking loop and its failure cases.

## Out of scope

Judgment/model calls, Gate/Loop/Fork execution, resume/durable checkpoints,
questionnaire/UI, role/data/SOUL/skill generation, live integration/activation,
Hermes writes, packaging, persistent spec serialization, full spec/bundle approval
binding, universal workflow correctness and savings claims.

## Comments

Adam initially approved proving this restricted loop before expanding node types
and requested the handoff and roadmap. The targeted to-tickets pass retained one
vertical ticket and outlined later milestones without turning them into invented
implementation contracts. Ticket 09 already had full-suite and two-axis review
coverage; no additional broad review gate was needed for this planning work.

Adam subsequently said “use the to-tickets skill guidance as we did last time.
approve all.” This approves the single-ticket granularity and blocking edges,
in-memory artifact, public interface/test seam, same-ID/separate-log exact-byte
comparison, ticket 09 acceptance and the full review baseline recorded above.
Implementation was unblocked by that approval; later roadmap milestones remain
outlines only.

Adam subsequently explicitly accepted ticket 10 after implementation, the review
fix and independent follow-up review. Ticket 10 is accepted and closed.

## Answer

Implemented `generate_graph` and `check_conformance` for the approved restricted
target. Commits: `568ad14`, `0855f25`, `03f1af3`.
Evidence: [public contract, verification and review](../../../docs/generation-ticket10.md).

- Focused tests: **98 passed**; full offline suite: **336 passed, 3 optional skips**.
- Mypy: **19 files clean**; diff checks clean; local Graft graph refreshed.
- Both review axes identified the same strict unordered-state comparison bug;
  fixed with public-seam regressions. Independent follow-up: Standards **0 new
  findings**, Spec **0 outstanding findings**.
- No live calls or Hermes writes. Acceptance does not expand the restricted
  conformance claim or authorize the remaining roadmap for implementation.

Next session: `/to-tickets` to refine the next complete vertical slice from M2,
with any new decisions surfaced for approval before implementation.
