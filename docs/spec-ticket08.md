# Ticket 08 — in-memory workflow spec validation

Implementation authorized by Adam, including the public validation seam and
review baseline `b90ea2e9154eb1503cd20ce314be6c7be57dd630`.

## Public boundary

`agent_lab.spec.validate_spec(candidate)` accepts Python declarations and returns
`SpecValidation`: either an immutable `WorkflowSpec` with no findings, or no spec
and nonempty typed `Finding` values (`code`, `path`, `message`). `valid` is derived,
not an independently writable verdict. Expected declaration errors return findings;
programming errors are not hidden by a catch-all exception handler.

Callers may supply an in-memory dictionary with tuples for collections, or the
exported Pydantic declaration types. Dictionaries must include node/edge `kind`
discriminators. This is a Python admission API, **not a serialized file format**.
No parser, persistence, canonical encoding or digest is introduced. Tests do not
pin JSON output. Models and nested models are strictly revalidated at admission,
including objects made with unchecked `model_copy` or `model_construct`.

```python
from agent_lab.spec import Route, TransformNode, WorkflowSpec, validate_spec

result = validate_spec(WorkflowSpec(
    entry="copy",
    nodes=(TransformNode(id="copy", operation="project.copy"),),
    edges=(Route(source="copy", outcome="done", target="SUCCESS"),),
    budget=5,
    terminals=("SUCCESS",),
))
assert result.valid
```

Only the returned validated result is evidence of graph validation. Constructing
`WorkflowSpec` directly checks field shapes, not cross-declaration rules.

## Declaration rules

- Node and terminal identities share one namespace and must be distinct. Entry
  and edge sources name nodes; route destinations name nodes or terminals.
- Budget is a positive integer, not a boolean, string or fractional number.
  Names/references are nonblank strings, preserved exactly rather than repaired.
  Extra fields and unknown discriminators are refused. Collections are tuples.
- **Transform:** an inert `operation` reference and nonempty, distinct `outcomes`
  (default `done`). Outcomes may describe deterministic success/failure routing.
- **Judgment:** nonempty, distinct string `options` define a finite typed choice
  vocabulary. This declares the decision's possible values; it does not obtain
  a judgment, confidence or probability. Runtime judgment validation is unchanged.
- **Decision:** an inert `value` reference and nonempty, distinct routing `cases`.
  Case evaluation is not implemented. No arbitrary predicate/code is evaluated.
- **Gate:** fixed human-decision routes `approved`, `rejected`, `pending`, `invalid`.
  `invalid` represents invalid approval evidence, not consent. No approval is read
  or granted, and spec/bundle digest binding remains a later ticket.
- **Loop:** positive integer `max_iterations`, inert `exit_predicate` reference,
  and fixed `repeat`, `exit`, `exhausted` routes. Each repeat traversal must consume
  the declared bound in a future execution; this validator does not run counters.

Every node outcome has exactly one dispatch. Both missing and contradictory
routes fail; even identical duplicate dispatches fail rather than being deduped.
Outcomes not declared by the source node fail.

## Conditional routing, parallelism and bounded cycles

A `Route` chooses one destination for a source outcome. A `Fork` explicitly
broadcasts that outcome to at least two distinct branch node identities and names
an existing node as its `join`. Joins are edge metadata on existing nodes, not a
sixth node type. The join is separate from the fork source and branch entries.

Every branch's pre-join reachable declarations must be able to reach that join.
A branch cannot terminate early or escape down a route that cannot converge.
The traversal stops at the join: sequential waves may use a join as their next
fork source, so multiple convergence points are supported. This is a declaration
check, not a scheduler, reducer, cancellation protocol or runtime concurrency
proof. Branch-local failures can be returned to a join; early terminal/cancellation
semantics are not supplied by this slice.

Removing precisely the Loop `repeat` dispatches must leave a DAG. This checks all
cycles, including disconnected ones: merely putting a Loop somewhere in a cyclic
component does not legalize other cycles. Exit/exhaustion cannot supply an
unbounded bypass. The finite repeat bounds are obligations for a future compiler;
there is no claim that predicates become true or that the budget suffices for
success. Cycles are reported at an involved edge, in deterministic input order.

## Findings and limits

Stable categories:

- `invalid_declaration`: malformed field, missing field, extra field, unknown type.
- `duplicate_identity`, `missing_entry`, `unknown_reference`: identity/reference errors.
- `duplicate_outcome`, `unknown_outcome`, `missing_route`, `conflicting_route`: routing errors.
- `invalid_fork`, `invalid_join`: parallel declaration errors.
- `unbounded_cycle`: a cycle remains without bounded repeat edges.

Locations are tuples of field names and collection indices. Shape errors may
include the selected union variant in their location. Validation proceeds through
shape, references, routing, cycles and joins; an invalid phase stops later phases,
so findings are not an exhaustive inventory of all possible errors in a draft.

A valid spec is **not conformance** (there is no emitted artifact or reference
execution), **not correctness**, and not proof of least privilege or savings.
Operation/predicate/value references are never resolved, imported or executed.
Role-registry compatibility, compilation, runtime budget enforcement, serialization,
UI and Hermes integration are unchanged or out of scope. Unreachable declarations
and unused terminals are not pruned or rejected; the validator checks them too.

## Evidence

Tests use only the public `validate_spec` seam and returned declarations/findings.
Fixtures cover a linear route, Judgment/Decision/Gate branching, bounded retry,
two parallel waves and a hand-authored six-node foundation business route. The
latter follows ADR 0007 and `agent_lab/workflow.py`; it does not import the runtime
to manufacture expected output, nor claim equivalence for generated code. Generic
runtime failure/budget transitions remain runtime concerns, not executed here.

Red/green slices recorded locally: missing module → linear admission; invalid
references → identity checks; missing node types/routing → branching; rejected Loop
→ bounded-cycle validation; rejected Fork → explicit waves/convergence; imprecise
cycle location → involved-edge finding. Strictness and unchecked-copy regressions
were added against the completed admission boundary.

Reproduce:

```bash
.venv/bin/python -m pytest -q tests/test_workflow_spec.py
.venv/bin/python -m mypy agent_lab
AGENT_LAB_JUDGMENT=stub .venv/bin/python -m pytest -q
```

Final verification: **67 focused tests passed**; mypy: **16 files, zero errors**.
Full offline suite: **238 passed, 3 optional skips** (two live Jev tests and the
real Hermes loader check). No live calls or Hermes changes. `git diff --check`
passed and the local Graft graph was refreshed.

## Independent review

Two parallel independent reviews examined `git diff b90ea2e...HEAD` at implementation
commit `98f555a`.

### Standards

Zero documented-standard violations. One optional heuristic: possible Primitive
Obsession in the open-ended `Finding.code: str`. Addressed by defining the explicit
`FindingCode` Literal vocabulary; final tests and mypy passed after this change.

### Spec

Zero actionable findings: no missing/partial criteria, scope creep or confirmed
incorrect behavior. The reviewer independently reproduced focused/full tests and
mypy results. Validation remains distinct from conformance and correctness.

Review summary: Standards **0 violations, 1 optional improvement addressed**;
Spec **0 findings**. **Accepted and closed** at Adam's explicit approval.
Implementation and final verification commits: `98f555a`, `abfe1e8`.
