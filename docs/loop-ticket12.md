# Ticket 12 — bounded Loop execution and conformance

Loop is supported alongside Transform, Decision, restricted Intervention Judgment
and Route through `compile_reference`, `generate_graph`, and `check_conformance`.
Gate, Fork and resume remain unsupported. No live calls are needed or authorized.

Bind `exit_predicate` by its exact opaque string in `bindings`. The callable receives
a detached frozen typed-state snapshot and must return an actual `bool`. Compilation
copies declarations/maps and checks unreachable declarations without invoking bindings.

Every Loop visit first reserves one budget step. True selects `exit`; false selects
`repeat` while allowance remains, otherwise `exhausted`. `max_iterations` bounds
repeat traversals, not predicate calls. Per-node counters persist across re-entry
and start afresh for each run. Loop leaves retained workflow state unchanged.
Invalid results/exceptions stop at FAILED_VALIDATION; budget refusal stops without
calling the predicate. Audit I/O errors remain visible and stop subsequent work.

Each Loop event includes `repeat_count` (consumed allowance after this route) and
`max_iterations`, alongside the existing route, target, failure and spend fields.
Candidate inspection reconstructs the actual predicate reference, bound and routes.
Conformance compares ordered events, exact bytes/digests, strict state, terminal and
spend using the same run ID in separate fresh logs. A pass applies only to the supplied
cases and supported target; it is not semantic correctness or universal conformance.

## Verification and review

The approved seam is authored spec + explicit bindings + independently supplied
candidate + named typed cases → report and real logs. Initial route tests failed
with `unsupported_node` before implementation. Tests pin hand-authored expected
routes/counts, exit precedence, budgets, strict booleans, snapshot isolation, copied
bindings/declarations, independent counters, offline Judgment replay, structural and
behavioral differences, and real temporary-filesystem audit failures in both drivers
and both checker phases. An older unsupported-Loop assertion now expects an unbound
predicate finding. Existing protection/freshness and unsupported-target tests remain.

Independent parallel review used baseline `5038a372780171b892b057be150baf7fb2f0dd8d`
and implementation commit `597d315`:

### Standards

Zero documented violations. One optional repeated-switch smell: binding reference
selection is repeated in admission, execution, generation and structural inspection.
Retained for this bounded extension rather than adding a broader declaration-interface
refactor; the control flows remain independently inspectable.

### Spec

Zero confirmed violations or scope creep. Reviewer suggested checker candidate-phase
audit failure coverage; added a real filesystem regression for that combination.

Final verification: full offline suite **423 passed, 3 skipped**; mypy **zero errors
in 19 source files**; diff whitespace checks clean. Graft refreshed. Skips are the
two opt-in live tests and optional real-Hermes loader test. No dependencies changed.
