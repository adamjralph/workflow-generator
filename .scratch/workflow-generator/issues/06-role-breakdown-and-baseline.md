# 06: Per-role breakdown, per-run detail, and the baseline

**What to build:** A diagnosis report broken down per role and per run, compared against the before-number taken through the same join, so that any later claim of improvement is falsifiable. A claim of improvement is never emitted without a measured before from the same join.

**Blocked by:** 05.

**Source:** `spec.md` → "Metrics and improvement"; `CONTEXT.md` §5; `cost-baseline.md`.

**Status:** claimed

- [x] The report breaks cost down per role and per run in the four units.
- [x] It presents a before-number taken through the same join and a comparison against it.
- [x] Run against the baseline data, the before-number reproduces 214 calls and 1,132,524 fresh input tokens across 23 runs.
- [x] The report is persisted as an immutable, digest-addressed artifact.
- [x] No improvement claim is emitted without a measured before from the same join.

## Answer

Implemented at Adam's request with confirmed public test seams. Commits `ea50593`
and `c4af4d3`; usage, measurement contract and review evidence in
`docs/report-ticket06.md`. Runtime-neutral report core, Kanban CLI/plugin entry,
immutable report artifacts and measured same-method before/after comparisons.
Published 23-run baseline reproduced via offline real-adapter fixtures.

Independent Standards review found one runtime-neutrality breach and two
heuristic duplication concerns; all addressed and follow-up review cleared.
Spec review: zero findings. Final suite: 172 passed, 2 optional live-Jev skips,
including the real Hermes loader in isolated fixture homes. Mypy: zero errors.
Implementation is ready for Adam's acceptance; no live Hermes state was modified.
