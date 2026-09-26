# 32: Execute and check bounded Loops in parallel branches

**Type:** task
**Status:** locally implemented and verified; Adam authorized scoped commit/push if ready. Acceptance and live calls remain separate decisions. [Evidence](../../../docs/ticket-32-executor-evidence.md).
**Blocked by:** no local implementation blocker; acceptance remains with Adam. Ticket 31 (Decision routes), ticket 28's wave and ticket 12's route-only bounded Loop are delivered foundations.

## What to build

A caller authors one parallel wave with a bounded Loop in a branch and other branches that progress unevenly. The plain reference and generated graph both run the declared Loop's repeat, exit and exhausted routes with isolated per-branch repeat counts, then join once on success or close on the first declared-order branch failure. The conformance report checks the executed branch visits, state, spend and durable evidence, not just driver agreement.

## Local implementation checks

- [x] Admit a deliberately restricted, statically bounded shape: at most one Loop in each branch, no nested/overlapping cycles, no Fork or Gate within a Loop or branch, no model operations or Judgment, and every allowed repeat/exit/exhausted path converges on that branch's join. Reject unsupported cycles, alternate entry, and any path that can bypass the join before any binding runs.
- [x] Before dispatch, calculate a conservative worst-case **for every node visit in the branch**, not only the Loop node. Honor the accepted `max_iterations + 1` upper bound for visits to each Loop node; include repeat-body visits, Decision alternatives, all other branches and one closing join step. Refuse just-short budgets before branch work and admit exact-limit budgets without mid-wave step denial. Verify the bound against hand-enumerated paths rather than trusting agreement between drivers.
- [x] Both drivers support repeated branch-local visits and isolated repeat counters; `repeat`, early `exit`, and `exhausted` cases yield hand-authored expected state, terminal and actual spend. A loop in one branch cannot alter the run-level or sibling state/counter.
- [x] Complete all branches even on a failed Loop predicate or branch binding; select first failure by declared branch order, keep fork-entry state, record/charge join close, and never call reducer on failure. Invalid/non-boolean predicates and audit I/O failures fail closed.
- [x] Canonical projection preserves each branch's **recorded visit sequence** (including repeated node IDs, route labels, repeat counts, failures and actual visit order) while normalizing only accepted scheduling-dependent fields. Raw log remains intact. Mutated Loop bound, routes, candidate behavior or visit evidence must fail structural/behavioral checks; non-wave behavior stays unchanged.
- [x] Offline supplied-case conformance covers uneven completion, early exit versus exhaustion, exact/short budgets, multiple failures, mutation and no-network runs. Focused/full tests, mypy and independent Standards/Spec review use a frozen agreed baseline before acceptance.

## Frozen implementation boundary

Adam explicitly approved local implementation against baseline `19985ee300da0b900e1dd1ae780fb120445584d3`, with the authored-spec/conformance public seam. Admit at most one Loop in each pairwise-disjoint branch, whose sole cycle is its `repeat` edge and repeat body: every path from that edge returns to the same Loop, with no escape to the join and no other entry into the body. Exit/exhausted routes must converge on the branch join. Existing structural checks reject unbounded cycles, pre-join terminals, outside branch entry, nested waves, model operations, Gate and Judgment in branches. Before dispatch, compute the longest whole-branch route equivalent to an expanded `(node, repeat-count)` graph, pricing the repeated body algebraically up to `max_iterations`; sum branch maxima plus one closing join step (fork source is spent separately). Just-short refusals report `required`, `remaining_steps` and declared-order `branch_worst`; exact limits admit. Loop visits are at most `max_iterations + 1`; Decision/Transform body visits count on every repetition. The public seam is authored spec, independent plain/graph execution, supplied cases, report and persisted logs. Adam later authorized a scoped commit/push once verified; acceptance and live calls remain separate.
