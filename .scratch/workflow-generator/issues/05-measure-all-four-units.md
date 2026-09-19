# 05: Measure in all four units

**What to build:** The diagnosis reports all four agreed units and separates the two blind spots, so cost becomes legible in the terms the project fixed up front. Auxiliary and review traffic is reported apart from the worker's own loop, and reasoning tokens are reported apart from output tokens.

**Blocked by:** 03.

**Source:** `spec.md` → "Diagnosis"; `CONTEXT.md` §2.8, §5; `cost-baseline.md`.

**Status:** ready-for-agent

- [ ] The diagnosis reports context/call, tokens/run, and cache hit rate alongside calls/run.
- [ ] Auxiliary/review traffic is separated from the worker's own loop in the output.
- [ ] Reasoning tokens are reported separately from output tokens.
- [ ] A session counts as workflow cost only when a recorded run names it; interactive chat sessions are excluded.
- [ ] Re-running the 2026-09-18 baseline reproduces its published figures in these units.
