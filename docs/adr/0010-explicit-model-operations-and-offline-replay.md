---
status: accepted
---

# Explicit model operations, not hidden network calls in deterministic bindings

Ticket 19 needs model-backed writing and editorial review, while ADR 0007 currently
maps Transform exclusively to deterministic work. We retain the five
node kinds and extending Transform with an explicitly declared model-operation
binding: deterministic request preparation, a bounded live/recorded source, and
deterministic response application. Live execution is not deterministic;
conformance uses independent recorded sources and verifies exact request identity
through both drivers without model calls. Existing callable Transforms remain
deterministic; Judgment remains the narrow typed classifier, not a prose writer.

Accepted by Adam for ticket 21 ("approve all", then "proceed"). This narrowly amends ADR 0007 and CONTEXT §2.7 for declared model
operations. It does not authorize arbitrary side effects, autonomous agent loops,
new node kinds or a new runtime. The approved contract and limits are in
[the ticket 19 execution contract](../designer-ticket19-execution-contract.md).

## Considered options

- Hide a model call inside an ordinary Transform callable: conceals spend and
  nondeterminism and permits accidental live calls during checking. Rejected.
- Use Judgment for prose generation: changes its classifier meaning and vocabulary
  without supplying an appropriate operation/source contract. Rejected.
- Add a sixth model/agent node: exceeds the fixed-node design for this bounded slice.
- Generate and review outside the graph, then check a graph that only imports the
  outputs: checks post-processing, not the requested model-backed workflow.

## Consequences

Admission, both independent drivers, actual-candidate inspection and conformance
must recognize model operations explicitly. A digest binds recorded input/output
but does not prove model quality or provider authenticity. Provider integration
must enforce call limits without Hermes writes. Ticket 21 implements the Generator
slice with offline transport evidence; live authentication/model availability is not
verified. Guardian review and completed-pair replay remain tickets 22 and 23.
