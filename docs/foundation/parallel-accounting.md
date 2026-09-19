# Ticket 02 — concurrency contract and evidence

## Scope

`agent_lab` remains the sole runtime. Both drivers call `workflow.step`; the
plain driver is the reference. No diagnosis, metrics, plugin, generator, general
spec engine, serialization decision, or Hermes access is included.

- `RunAccounting`, injected by `Deps`, owns budgets by run id. Every concurrent
  branch of a run **must share that owner**, including branches with distinct
  judgment sources (`dataclasses.replace(deps, judgment=...)` preserves it).
  A short thread lock reserves a step before work starts. Exceptions do not
  refund work. A changed cap is rejected. Unrelated run ids have independent caps.
- Budgets in frozen branch states are point-in-time snapshots, not counters.
  At a join, refresh from the owner. Fresh-process continuation must start from
  the joined state, never a stale branch snapshot. This is in-process reservation,
  not distributed/durable execution accounting or crash recovery.
- `RunLog.append_next` allocates and appends under one advisory file lock, in
  completion order. It reads existing events for that run, so fresh handles and
  resumes continue numbering and other runs do not shift it. Model work is
  outside this lock. `step(..., seq=...)` remains call-compatible but ignores the
  caller's sequence; `next_seq` is advisory only. Explicit `RunLog.append` remains
  an import/replay primitive, not the concurrent runtime writer. Do not mix it
  with active runtime writers. This uses the local Linux filesystem's `flock`.
- Branches return frozen states through `reduce_list_append`; only the join
  calls `collect_findings(base, results, deps)`. It keeps the common notes prefix
  once, sorts all contributed note suffixes (duplicates retained), and refreshes
  budget. It rejects foreign-run or changed-prefix inputs. It deliberately does
  **not** choose a branch's stage, terminal, judgment, or draft: callers inspect
  branch outcomes and own routing. `GraphState.current` is a linear-route holder,
  not a parallel result channel.
- The existing business route stays linear. Synthetic pydantic-graph fan-out
  exercises the return-value join; overlapping invocations exercise both existing
  drivers. No arbitrary workflow API or additional execution engine is added.

## Measured red → green

At the agreed typed-state / Deps / driver seams, all data and judgments synthetic:

| Defect / criterion | Red on promoted core | Green regression |
| --- | --- | --- |
| Sequence collision | expected `[0, 1]`, got `[0, 0]` | `test_concurrent_events_have_run_level_sequence_in_append_order` |
| Two concurrent spends | expected `[2, 2]` at completion, got `[1, 1]` | `test_two_concurrent_steps_spend_two_from_one_run_budget` |
| Hard cap while work is in flight | second step had terminal `None`, not `FAILED_BUDGET` | `test_parallel_work_cannot_exceed_cap_while_first_call_is_in_flight` |
| Three findings | reducer received three states, shared holder retained only `('pricing',)` | `test_three_findings_survive_read_await_join`: `('legal', 'ops', 'pricing')`, budget 3, shared holder untouched |
| Driver conformance | inherited reference tests retained | `test_overlapping_drivers_replay_identical_events_and_digests`: identical events, exact log digest and draft digests, 12 spends |

The sequence and two-spend regressions were run before their respective fixes in
this checkout. The cap and read/await/write reproductions were run against an
isolated `git archive cddadc6 agent_lab` in `/tmp`, not the sibling lab. The
historical harness is retained as `parallel_red.py`; it intentionally uses the
unsafe holder pattern for the findings reproduction. The fixed regression
replaces that wiring with return values and the core findings collector. This
is a correction of the data channel, not an attempt to make stale assignment safe.

Reproduce all four **expected failures** without changing this checkout:

```bash
ROOT="$PWD"
tmp=$(mktemp -d)
git archive cddadc6 agent_lab | tar -x -C "$tmp"
cp docs/foundation/parallel_red.py "$tmp/test_parallel_red.py"
(cd "$tmp" && AGENT_LAB_JUDGMENT=stub "$ROOT/.venv/bin/python" -m pytest -q)
```

Run final regressions:

```bash
AGENT_LAB_JUDGMENT=stub .venv/bin/python -m pytest lessons/lesson_02_workflow/test_parallel.py -q
AGENT_LAB_JUDGMENT=stub .venv/bin/python -m pytest -q
.venv/bin/python -m mypy agent_lab
```

Results: **10 parallel tests passed; 75 full-suite passed, 2 optional live-Jev
skips**. The model boundary uses barriers/events with bounded waits: both calls
must enter before either finishes, so serializing whole steps fails rather than
passing a loose wall-clock threshold. Separate log handles, stale snapshots at
a join, fresh-owner continuation, independent runs, and invalid joins/caps are
also covered. Driver equivalence uses the same controlled completion schedule;
no promise of identical chronological logs across different schedules is made.

Regular mypy runs report the same **11 inherited errors in 3 files**, no new
errors and no suppressions. See the foundation README for the baseline details.

## Independent review

Two parallel, read-only worker reviews used `git diff cddadc6...HEAD` at
implementation commit `7e1d517` (including the intervening authorized ticket-01
closure commit). Standards read CONTEXT, ADRs, tracker conventions and foundation
docs; Spec read ticket 02, not the general product spec as a build target.

- **Standards:** zero hard violations or actionable smells. One non-blocking
  performance observation: allocating each event scans the complete log under
  lock, so cumulative parsing is quadratic as the log grows. Retained for this
  bounded-step correction; no speculative indexing/storage machinery added.
- **Spec:** zero actionable findings. Reviewer independently reproduced the four
  red failures and the 75/2 green suite. Explicit qualification: findings safety
  comes from replacing the unsafe data channel, not making shared assignment safe.

No relevant corrective findings remained. Final verification reruns the individual
parallel/workflow files, full offline suite and mypy after recording this review.
Ticket 02 remains **claimed**. Acceptance boxes and closure belong to Adam.
