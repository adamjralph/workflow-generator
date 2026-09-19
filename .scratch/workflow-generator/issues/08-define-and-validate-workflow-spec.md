# 08: Define and validate the in-memory workflow spec

**Type:** task
**Status:** claimed
**Blocked by:** none (tickets 01–07 are accepted and closed).
**Authorization:** Adam authorized implementation and confirmed the scope, public
validation seam and review baseline `b90ea2e9154eb1503cd20ce314be6c7be57dd630`.

**What to build:** A typed, runtime-independent, in-memory workflow spec and a
public validation boundary. A caller can describe a workflow with the five fixed
node types, typed edges, a step budget and declared terminals, then obtain either
a validated spec or typed findings locating invalid declarations. This is the
first generation-core slice, not a compiler or a conformance checker.

**Sources:** [product spec](../spec.md), especially “The core is the spec plus the
conformance check,” “The five node types,” and “Testing Decisions”;
[CONTEXT.md](../../../CONTEXT.md) §2.7, §9.2–9.5, §10.1, §11.1–11.2;
[ADR 0004](../../../docs/adr/0004-spec-is-a-typed-directed-graph.md),
[ADR 0007](../../../docs/adr/0007-node-types-compile-through-a-fixed-mapping.md),
[ADR 0008](../../../docs/adr/0008-conformance-pins-the-plain-driver-as-reference.md).

## Scope and acceptance criteria

Adam approved this scope and the validation seam. Concrete declaration rules and
claim boundaries are documented in [ticket 08 evidence](../../../docs/spec-ticket08.md),
not attributed retroactively to the existing ADRs.

- [x] The public in-memory contract supports exactly Judgment, Decision, Gate,
  Transform and Loop. Unknown node types and malformed declarations are rejected
  rather than coerced into a supported type.
- [x] The spec declares an entry node, uniquely identified nodes, typed edges,
  a positive integer step budget and at least one terminal. Duplicate identities,
  missing entry nodes and dangling node/terminal references produce findings.
- [x] Node declarations capture their distinguishing contracts: Judgment's typed
  options, Decision's routing cases, Gate's human-decision outcomes, Transform's
  deterministic operation reference, and Loop's finite positive retry bound and
  exit-predicate reference. Validation does not invoke operations, predicates,
  judgment sources or approval gates.
- [x] Edge declarations distinguish conditional routing from parallel fan-out and
  join structure; a multi-edge node is not silently interpreted as either.
  Parallel branches and multiple convergence points can be represented without
  inventing a sixth node type or adopting the foundation's fixed Stage enum.
- [x] Routing references are checked against declared options/outcomes and
  destinations. Missing required routes and contradictory routes produce findings.
- [x] Cycles must be governed by a declared bounded Loop; an unrestricted cycle
  is rejected. Structural validation does not claim to prove that a predicate
  will become true or that the workflow will succeed within its budget.
- [x] Findings have stable machine-readable categories and identify the relevant
  declaration. An invalid spec cannot also be reported as valid. Results are
  deterministic for identical input, without silent graph repair.
- [x] Offline tests through the public spec boundary cover all five node types,
  a linear example, branching, parallel fan-out/join with multiple convergence
  points, and a bounded retry. Negative cases cover each rejection above.
- [x] A hand-authored fixture represents the foundation's existing business route
  using the documented node mapping, without implementing compilation or
  asserting driver equivalence for generated workflows.
- [x] Existing diagnosis/runtime tests and mypy remain green. Tests need no
  network, model credentials, live Hermes state or sibling-repo imports.

## Test seam and claim boundary

Proposed seam: an in-memory candidate spec enters one public validation boundary;
callers observe a validated spec or typed findings. Tests assert these outcomes,
not private implementation details or a serialized file shape. Exact Python
names and internal module layout are implementation choices.

A valid spec means its declarations satisfy this ticket's structural rules. It
is **not** a conformance verdict: no emitted artifact is compared with the spec.
It is also not a correctness, security, termination-success or cost-savings claim.
The existing Deps seam remains the runtime seam; this ticket adds no second
execution engine.

## Explicitly out of scope

- On-disk serialization, canonical encoding, spec digests and persistence.
- Compilation, emission, behavioural conformance and execution of the spec.
- Changing the existing approval store or implementing spec/bundle digest binding.
- Questionnaire, completeness-check model calls, diagrams, UI/TUI or plugin changes.
- Role-registry discovery/type checking, SOUL generation, skill creation and data
  linking. Operation references are declarations, not proof of available capability.
- Packaging, naming, community scope and other runtime targets.
- Any Hermes writes, configuration activation or activation-gate bypass.

The deferred community decision does not block this in-memory slice; it still
blocks the concrete spec format and packaging. No persistent schema is to be
introduced indirectly through snapshots, golden JSON or digest fixtures.

## Approval before claiming

Adam authorized ticket 08 and confirmed scope, the public validation test seam
and review baseline `b90ea2e9154eb1503cd20ce314be6c7be57dd630`. Implementation
is claimed; acceptance/closure remains a separate user decision.

## Comments

Adam requested this draft after accepting and closing ticket 04. Tickets 01–07
are complete. This ticket prepares the in-memory boundary for later, separately
authorized compilation and structural/behavioural conformance tickets; those
follow-ons are not authorized by this ticket.

Implementation uses `agent_lab/spec.py`; focused public-boundary tests are in
`tests/test_workflow_spec.py`. Declaration rules, red/green evidence and claim
limits are recorded in `docs/spec-ticket08.md`. No Hermes state or config was
changed. Implementation commit: `98f555a`.

Final verification: **67 focused tests passed**, **238 full-suite tests passed,
3 optional skips**, and **16 files mypy-clean**. Independent parallel review:
Standards **0 violations**, one optional finding-code typing improvement addressed;
Spec **0 findings**. Implementation is complete; ticket remains claimed pending
Adam's acceptance/closure.
