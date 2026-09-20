# 10: Generate and check the deterministic reference slice

**Type:** task
**Status:** ready-for-human
**Blocked by:** ticket 09 explicit closure and the contract decisions below.
**Authorization:** Adam approved the direction and ordering, not yet the concrete
artifact/API/comparison contract or implementation. Refine in a targeted
`to-tickets` pass before claiming.

## Goal

Prove the smallest complete loop:

**authored spec → plain reference → generated graph → passing conformance check**.

Keep the same Transform/Decision nodes and Route edges as ticket 09. Do not expand
the executable language before proving that generation and checking work together.

Sources: [roadmap](../../../ROADMAP.md), [handoff](../../../HANDOFF.md),
[product spec](../spec.md), [ticket 09 API](../../../docs/reference-ticket09.md),
[ADR 0007](../../../docs/adr/0007-node-types-compile-through-a-fixed-mapping.md),
[ADR 0008](../../../docs/adr/0008-conformance-pins-the-plain-driver-as-reference.md),
[ADR 0001](../../../docs/adr/0001-conformance-is-structural-and-behavioural.md).

## Proposed scope

- Reuse ticket 08 admission and ticket 09 target restrictions, explicit binding
  lookup and typed state/result rules. No imports/eval/discovery from references.
- Produce an executable pydantic-graph candidate for that restricted slice.
- Execute the candidate through graph control flow, not by calling the whole plain
  reference runner and presenting that as independent graph execution.
- Reuse foundation budget, event allocation and failure mechanics; shared node
  semantics are appropriate, a second scheduler/event writer is not.
- Check actual candidate structure against the admitted spec and compare offline
  reference/candidate behavior under an agreed trace/state/accounting contract.
- Return a typed report with located mismatches; unsupported or divergent candidates
  fail closed. Do not infer full conformance from one successful happy-path run.
- Use a hand-authored branching example and deliberately altered candidates to
  prove the check can detect incorrect structure and behavior.

## Decisions to confirm before tests or implementation

1. **Artifact representation:** in-memory executable graph, generated Python files,
   or a smaller intermediate artifact? Pick the minimum that honestly proves
   generation and permits checking the actual candidate. Do not silently select
   persistent spec serialization, packaging or a canonical spec/bundle digest.
2. **Public seam/API:** how spec, explicit bindings, state type/input and candidate
   enter generation/checking; what the typed result/report exposes. The checker
   must accept a candidate independently of generation so divergence is testable.
3. **Comparison contract:** required structural fields, final-state equality,
   ordered route/terminal events, step spend and budget refusals. Decide how
   independent run IDs/logs are handled. Any normalized trace or digest must be
   named honestly; it is not automatically a digest of the original log bytes.
4. **Evidence and limits:** what runs/inputs the report covers, what can be checked
   before execution, and how compilation, candidate-execution and audit failures
   appear. No universal behavioral-correctness claim from finite examples.
5. **Implementation size:** keep one vertical ticket if bounded; split generation
   and checking only if necessary, retaining the end-to-end milestone as the goal.
6. **Review baseline:** propose current committed HEAD in the next session and
   obtain Adam's confirmation. Approval of the roadmap is not approval of a SHA.

## Proposed acceptance evidence

- An admitted Transform → Decision example produces an executable graph candidate,
  takes distinct routes for distinct typed inputs and agrees with plain execution.
- Structural deviations (such as wrong route/terminal/budget) return typed findings.
- Behavioral deviation is caught even when declared structure appears to match.
- Binding exceptions, malformed states/labels, short/exact budgets and immediate
  terminal stopping are covered, with no extra work or overspend.
- Repeated deterministic offline runs agree under the approved comparison rules.
- Unsupported/unbound declarations produce no runnable candidate or passing report.
- Audit failures stop visibly; evidence uses the public RunLog API and foundation
  sequence allocation, not a competing counter or writer.
- Existing diagnosis, admission, reference and business-driver tests remain green.
- Focused TDD and mypy throughout; full offline suite and two-axis review against
  the confirmed baseline before completion.

## Out of scope

Judgment/model calls, Gate/Loop/Fork execution, resume/durable checkpoints,
questionnaire/UI, role/data/SOUL/skill generation, live integration/activation,
Hermes writes, packaging, persistent spec serialization, full spec/bundle approval
binding and universal workflow correctness or savings claims.

## Comments

Adam approved proving this restricted loop before expanding node types and asked
for a next-session handoff and roadmap. A targeted `to-tickets` pass should sharpen
this draft and outline later milestones, not invent detailed contracts for the
entire remaining product. Ticket 09 already has full-suite and two-axis review
coverage; no additional broad review gate is required merely to begin planning.
