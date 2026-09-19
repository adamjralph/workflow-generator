# 02: Fix parallel accounting in the core

**What to build:** Parallel branches in the core no longer collide on event sequence numbers or lose budget, so a declared step cap is real and the append-only log stays replayable in order. Branch results travel by return value through reducers instead of accumulating in shared state.

**Blocked by:** 01.

**Source:** `spec.md` → "Concurrency and accounting corrections"; `CONTEXT.md` §5; `spikes/parallel-capability/FINDINGS.md`.

**Status:** ready-for-agent

- [ ] Two concurrent branches produce strictly monotonic, non-colliding sequence numbers for the same run.
- [ ] Two steps spent across concurrent branches are counted as two; a step cap cannot be exceeded by parallel work.
- [ ] Three parallel branches each contributing a finding all survive into the join — no read-await-write loss.
- [ ] The plain state-machine driver and the pydantic-graph driver still produce identical events and digests.
- [ ] A regression test reproduces each measured defect (fails on the unfixed code) and passes after the fix.
