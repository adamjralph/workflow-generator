# 09: Compile a deterministic spec slice to plain reference execution

**Type:** task
**Status:** ready-for-human
**Blocked by:** 08 (accepted and closed).
**Authorization:** Adam approved implementation, the execution policies, frozen
Pydantic state/Transform-result contract, public test seam and review baseline
`e6c1c9bc3d7920c518f210e05bcc271b685eebb8` in the implementation conversation.

**What to build:** The first executable vertical slice of the generation core.
A caller supplies an in-memory spec and explicit deterministic bindings, compiles
it to a plain reference execution, and runs it offline to a declared terminal
with a bounded step count and recorded events. Support Transform and Decision
nodes connected by Route edges only. Reject everything else explicitly before
work begins; do not imply that every spec admitted by ticket 08 is executable.

**Sources:** [product spec](../spec.md), “The core is the spec plus the conformance
check,” “Node-type mapping,” “Runtime drivers,” and “Run log and budget”;
[CONTEXT.md](../../../CONTEXT.md) §10.1, §11.1–11.2;
[ADR 0004](../../../docs/adr/0004-spec-is-a-typed-directed-graph.md),
[ADR 0007](../../../docs/adr/0007-node-types-compile-through-a-fixed-mapping.md),
[ADR 0008](../../../docs/adr/0008-conformance-pins-the-plain-driver-as-reference.md);
[ticket 08 API and limits](../../../docs/spec-ticket08.md).

## Proposed execution contract

These are proposed policies for this slice, not new decisions attributed to the
ADRs. Approve them and settle the state/result details below before claiming.

- Compilation reuses ticket 08 validation, then checks target support and resolves
  every operation/value reference against caller-supplied bindings. References
  are opaque keys, not import paths or expressions. No dynamic import, eval,
  plugin discovery, model call or binding invocation happens during compilation.
- Every declaration is checked, including unreachable declarations. Judgment,
  Gate, Loop and Fork remain valid spec constructs but are unsupported by this
  target slice. Unsupported or unbound declarations return located typed compile
  findings, not a partially runnable plan.
- A Transform binding consumes a typed state snapshot and returns a new snapshot
  plus one declared outcome. A Decision binding reads the snapshot and returns
  one declared case without changing the state. The selected label follows the
  spec's unique Route; there is no implicit default or coercion.
- Execution uses the compiled declarations/bindings, not later mutations of the
  caller's spec or binding map. Explicit bindings are trusted local code, not a
  sandbox. Determinism and absence of external side effects are binding contracts,
  not properties that this tool can mechanically prove for arbitrary Python.
- Each node invocation, including a Decision, reserves one step before invoking
  its binding. Compilation and reaching a terminal do not spend steps. Failed
  invocations still consume their reserved step; a refused invocation does not
  execute or increase spend beyond the cap. Steps are not model calls.
- This target requires declared `FAILED_VALIDATION` and `FAILED_BUDGET` terminals.
  Missing safety terminals are compile findings, not silently inserted graph
  repairs. Other declared terminal names remain runtime-independent.
- Binding exceptions, malformed results and undeclared outcome/case values stop
  execution at recorded `FAILED_VALIDATION`. Budget exhaustion stops at recorded
  `FAILED_BUDGET` before the next binding runs. Ordinary declared terminal routes
  stop immediately; no subsequent binding executes.
- Each completed or refused node attempt records its node identity, selected
  route or failure, terminal when present, and step accounting in the append-only
  run log. Reuse per-run sequence allocation; do not allocate a second counter.
- A run is fresh and single-pass. Resume, reusing a completed run identity and
  parallel execution are unsupported here and must not silently restart work.
  Repeated offline execution uses independent run identities/logs; compare the
  declared trace fields, excluding the deliberately different run identity.
- Audit I/O failures must be surfaced explicitly and stop further work. Never
  claim a terminal was persisted when the log could not be written. Process
  interruption and crash-durable execution are not promised by this slice.

## Acceptance criteria

- [ ] A public spec-to-reference compilation interface returns either a runnable
  in-memory plan or typed located findings; invalid specs, unsupported constructs,
  unresolved bindings and missing required failure terminals produce no plan.
- [ ] A hand-authored Transform → Decision example executes different routes for
  different typed inputs, reaches the specified terminals and exposes the final
  state, used steps and recorded trace. Nodes use arbitrary spec identities, not
  the foundation's fixed business Stage enum.
- [ ] Transform outcomes and Decision cases are checked at runtime. A binding
  returning an undeclared label or malformed result, or raising an ordinary
  exception, records a failure terminal and prevents later work.
- [ ] A cap shorter than the selected route stops before overspending; an exact
  cap succeeds. Tests distinguish zero-cost routing to a terminal from a node
  invocation, and prove that work beyond the cap did not occur.
- [ ] Repeated execution with identical inputs and deterministic bindings gives
  identical final state, route/terminal trace and step accounting (apart from run
  identity). No wall-clock/random data is introduced into those trace fields.
- [ ] Operation references are only looked up in explicit bindings. A missing key
  or import-looking reference cannot trigger implicit discovery or execution.
  Changing the original binding map after compilation cannot redirect the plan.
- [ ] Log records are append-only and use the foundation's per-run sequence
  allocator. A logging failure stops the run visibly rather than returning an
  unqualified success. Failure records are inspected through the public log API.
- [ ] The existing foundation business workflow, plain/graph driver equivalence,
  diagnosis behavior and all ticket 08 admission behavior remain unchanged.
  Reuse foundation budget/accounting and logging primitives; do not build a
  competing scheduler, approval store or event writer.
- [ ] Tests are offline at the agreed seam. Focused tests and mypy run throughout;
  the full suite runs at final verification, followed by documented two-axis
  review against an explicitly confirmed baseline.

## Proposed test seam and foundation integration

The feature seam is **spec + bindings + typed input → reference result and recorded
trace**, including compilation findings. Tests exercise this public interface;
no tests against compiler internals, private dispatch functions or call-count
mocks. Tiny deterministic bindings supplied by the caller are fixtures, not
substitutes for internal implementation. Existing `RunLog` read methods expose
recorded evidence.

Keep the plain state-machine execution authoritative per ADR 0008. Extend/extract
shared foundation mechanics where necessary rather than pretending the fixed
six-node business route can execute arbitrary spec identities. Preserve the
existing `Deps` seam and plain/graph behavior; do not force generic spec state
through business-specific fields or introduce a parallel budgeting/logging stack.
Any new public dependency surface must be agreed before tests are written.

## Decisions to confirm before implementation

1. Approve the restricted target, all-declaration rejection policy, safety-terminal
   requirements, step semantics and failure behavior above.
2. Agree the concrete typed input/state and Transform-result contract, including
   validation of returned state and protection against mutation. Keep it an
   in-memory Python contract; do not settle persistent spec serialization here.
3. Confirm the public execution seam and how foundation mechanics are reused
   without breaking existing `Deps` callers. Exact internal layout is not a
   user-facing design decision, but a new runtime seam is.
4. Confirm a review baseline when authorizing implementation.

## Explicitly out of scope

- Judgment/model integration, approval gates or spec/bundle digest binding.
- Loop execution, parallel forks/joins, reducers, resume or durable checkpoints.
- Pydantic-graph emission, generated files, regeneration and conformance verdicts.
- Spec serialization, canonical encoding, spec/bundle digests and packaging.
- Questionnaire, UI/TUI, profile/role discovery, SOUL/skill generation or data linking.
- Hermes writes, live calls, activation changes, sandboxing or cost-savings claims.

This establishes a reference execution slice, not full structural/behavioural
conformance. No artifact is emitted or compared, and no claim of byte-identical
spec/bundle replay or proven workflow correctness is made.

## Comments

Adam requested this draft after accepting and closing ticket 08. The next human
action is approval/refinement of this contract and test seam, not implementation.
Later tickets may extend the reference target and introduce the graph emitter and
conformance comparison; this ticket does not authorize those follow-ons.

Adam subsequently approved the four implementation decisions in the implementation
conversation. The draft/proposed language above is retained as the original
proposal; that approval now authorizes this slice, not the out-of-scope follow-ons.

## Answer

Implemented the approved public compilation/execution seam in
`agent_lab/reference.py`. Foundation accounting reservations and append-only
`RunLog` sequence allocation are reused; existing business drivers remain unchanged.
The hand-authored example and failure/immutability/freshness cases are in
`tests/test_reference.py`. API, limits, red/green evidence and two-axis review:
[reference-ticket09.md](../../../docs/reference-ticket09.md).

Verification: 26 focused tests; 264 full offline tests passed, 3 optional skips;
mypy clean across 17 files. Review against approved baseline `e6c1c9b` found
0 Standards violations and 0 Spec findings; one optional duplication improvement
was addressed. Ready for Adam's acceptance; no follow-on work is authorized.
