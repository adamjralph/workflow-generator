# 02: Fix parallel accounting in the core

**What to build:** Parallel branches in the core no longer collide on event sequence numbers or lose budget, so a declared step cap is real and the append-only log stays replayable in order. Branch results travel by return value through reducers instead of accumulating in shared state.

**Blocked by:** 01.

**Source:** `spec.md` → "Concurrency and accounting corrections"; `CONTEXT.md` §5; `spikes/parallel-capability/FINDINGS.md`.

**Status:** resolved

- [x] Two concurrent branches produce strictly monotonic, non-colliding sequence numbers for the same run.
- [x] Two steps spent across concurrent branches are counted as two; a step cap cannot be exceeded by parallel work.
- [x] Three parallel branches each contributing a finding all survive into the join — no read-await-write loss.
- [x] The plain state-machine driver and the pydantic-graph driver still produce identical events and digests.
- [x] A regression test reproduces each measured defect (fails on the unfixed code) and passes after the fix.

## Answer

Accepted and closed at Adam's explicit request. Implementation: `7e1d517`;
independent review and final verification: `c492e93`.

Criterion-by-criterion red/green evidence and review results are recorded in
`docs/foundation/parallel-accounting.md`. Final suite: **75 passed, 2 optional
live-Jev skips**; the 11 inherited mypy errors remain unchanged and unsuppressed.
No Hermes access or sibling modifications. Tickets 03–06 remain unstarted and
require separate authorization.
