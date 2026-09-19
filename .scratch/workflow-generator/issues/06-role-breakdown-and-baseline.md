# 06: Per-role breakdown, per-run detail, and the baseline

**What to build:** A diagnosis report broken down per role and per run, compared against the before-number taken through the same join, so that any later claim of improvement is falsifiable. A claim of improvement is never emitted without a measured before from the same join.

**Blocked by:** 05.

**Source:** `spec.md` → "Metrics and improvement"; `CONTEXT.md` §5; `cost-baseline.md`.

**Status:** ready-for-agent

- [ ] The report breaks cost down per role and per run in the four units.
- [ ] It presents a before-number taken through the same join and a comparison against it.
- [ ] Run against the baseline data, the before-number reproduces 214 calls and 1,132,524 fresh input tokens across 23 runs.
- [ ] The report is persisted as an immutable, digest-addressed artifact.
- [ ] No improvement claim is emitted without a measured before from the same join.
