# 14: Compose workflows through the browser questionnaire

**Type:** task
**What to build:** A user composes a bounded request-routing workflow through multiple-choice questions: choose safe Transform operations, add Decisions, select Route destinations, inspect the structurally changing graph, and generate/check the actual executable graph through the existing core. This replaces the fixed demo shape with composition, not a programming editor.

**Blocked by:** None outstanding. Builds on delivered ticket 13; parallel execution and Gates are not prerequisites.

**Status:** resolved

**Acceptance:** Accepted and closed by Adam: “sounds good. Accept ticket 14.”

**Scope approval:** Adam approved one vertical slice, approved the bounded request-routing demo with “yes”, and then explicitly approved the concrete contract and review baseline with “approve”. This is published issue 14, not provisional planning item P14.

## Approved scope

- Catalog: receive request, add a fixed score adjustment, compare score against a selected threshold.
- Shape: 1–6 nodes, at most two Decisions; acyclic Route edges only.
- Destinations: another node or ACCEPTED/REVIEW terminal.
- Questionnaire editing only; structural changes appear in the graph used for generation.
- Invalid edits show findings and disable Generate/check. Deleting a referenced node requires repairing incoming routes.
- Budget is the longest executable path, displayed explicitly.
- Typed offline cases have independently expected routes and final scores, alongside the existing safety and failure tests.
- Preserve ticket 13's strict inputs, protected caller-selected evidence root, exact loopback/origin/token request boundary, actual core checking, visible failures and stale-result invalidation.

## Approved concrete contract

- State is a frozen, strictly typed integer score; booleans, strings and fractional values are not coerced to integers.
- Exactly one receive Transform is the entry and leaves the score unchanged. The 1–6 node bound includes receive and Decisions, but excludes terminals.
- Adjustment choices are -10 and +10. Threshold choices remain 10, 50 and 100. A Decision routes below threshold or at_or_above; equality takes at_or_above.
- Transforms each have one done Route. Decisions each have both labeled Routes. All nodes must be reachable from receive, every destination must exist, and every path must terminate. Sequential branch reconvergence is allowed; it is not a Fork/join or parallel execution.
- Node identities are stable while editing. No silent destination reassignment on deletion; dangling routes remain visible invalid draft state until repaired. Invalid drafts cannot execute, including via direct HTTP requests.
- The budget counts node visits including receive and Decisions, excluding terminals: the longest entry-to-terminal path, at most six. Editing recomputes it; the browser cannot override it.
- Offline cases are deterministic and bounded. For every syntactic entry-to-terminal path, derive the integer input interval implied by its Decisions and preceding adjustments. For each nonempty interval select its finite endpoints and one interior representative when available; use an adjacent integer for a one-sided interval and zero for an unconstrained interval. Deduplicate inputs. With at most two binary Decisions there are at most four paths and twelve cases. Display any infeasible routes and the actual case scope; do not claim exhaustive correctness.
- Tests independently hand-author expected routes, terminals and final scores for representative linear, branching, reconvergent and two-Decision designs, including equality after adjustment and infeasible paths. Expected outcomes must not be obtained by running the candidate or reference driver. Case derivation has its own independently expected fixtures.
- Public test seams remain answers → typed spec/bindings/cases/view and answers → actual generated candidate/common conformance report/real evidence. Trusted tests may inject an altered candidate; browser requests cannot supply executable code or candidate factories.
- Approved review baseline: ecc32fe2d0edec05a90e0f358b30a54fdc53485b (HEAD at publication). Unrelated working-tree changes are excluded from this implementation.

## Acceptance criteria

- [ ] A browser user creates and checks both a linear workflow and a branching workflow with operations before and after a Decision, without writing Python.
- [ ] Adding/removing nodes and changing destinations changes the authored spec and displayed graph structurally; display and execution derive from the same design.
- [ ] The approved catalog, typed state, node/Decision bounds, routing rules and longest-path budget are enforced before work, including for direct requests.
- [ ] Missing destinations, cycles, unreachable nodes, incomplete routes, unsupported fields/operations and invalid types produce visible findings and no execution.
- [ ] Deleting a referenced node does not silently rewire the workflow; repairing its routes restores a checkable design.
- [ ] Generate/check invokes existing generation and independent reference/conformance checking on the actual candidate and displays case inputs/scope, verdict, findings and available evidence.
- [ ] Independent expected routes, terminals and final scores constrain the demo's intended behavior, including score adjustments, both Decision outcomes and equality boundaries.
- [ ] Deliberately altered structure and candidate behavior fail through the public check seam; generation success alone never becomes a passing conformance result.
- [ ] Every edit immediately invalidates old results, including late in-flight responses and edits leaving an invalid draft.
- [ ] Validation, generation, checking and evidence-write failures remain visible; incomplete evidence cannot yield a pass.
- [ ] Existing protected-root and local request-boundary guarantees remain enforced. Browser requests cannot choose output roots, submit code or read arbitrary files.
- [ ] Real-browser tests prove structural composition → graph → real generation/check, route repair and stale-result invalidation; public-seam tests cover the bounded contract and negative cases.
- [ ] Existing offline tests and type checks stay green; independent Standards/Spec review uses the explicitly approved baseline. Preserve unrelated edits and use scoped commits.

## Answer

Implemented and accepted. Adam tried the browser UI, then explicitly accepted ticket 14. All acceptance criteria above are accepted as delivered; the unchecked boxes are the original implementation checklist, not outstanding work.

Evidence: `docs/designer-ticket14.md` (repository-relative). Verification recorded there: 614 passed, 3 expected optional skips; mypy clean across 22 source files; independent Standards/Spec review completed with the budget finding fixed and rechecked. These are recorded implementation results, not a new test run at closure.

Adam subsequently authorized the scoped ticket-14 commit. Acceptance does not authorize live calls, Hermes writes or additional implementation scope.

## Out of scope

Drag-and-drop; arbitrary expressions or browser-supplied code; Loop/Judgment/Gate/Fork authoring or execution extensions; resume; role/data/skill composition; model completeness calls; live calls; persistent public spec serialization; bundle distribution; approval-bound artifact lifecycle; Hermes writes or activation; public/multi-user hosting; universal correctness or savings claims. No broad prefactor is authorized; any necessary small behavior-preserving preparation belongs first within this slice.

## Comments

Published after Adam approved the breakdown and bounded demo; subsequently marked ready-for-agent after his explicit approval of the concrete contract and review baseline. Ticket 13 is delivered; its stale ready-for-agent wording is not an implementation dependency and was left untouched.
