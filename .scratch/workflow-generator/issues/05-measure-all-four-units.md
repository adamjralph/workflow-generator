# 05: Measure in all four units

**What to build:** The diagnosis reports all four agreed units and separates the two blind spots, so cost becomes legible in the terms the project fixed up front. Auxiliary and review traffic is reported apart from the worker's own loop, and reasoning tokens are reported apart from output tokens.

**Blocked by:** 03.

**Source:** `spec.md` → "Diagnosis"; `CONTEXT.md` §2.8, §5; `cost-baseline.md`.

**Status:** claimed

- [x] The diagnosis reports context/call, tokens/run, and cache hit rate alongside calls/run.
- [x] Auxiliary/review traffic is separated from the worker's own loop in the output.
- [x] Reasoning tokens are reported separately from output tokens.
- [x] A session counts as workflow cost only when a recorded run names it; interactive chat sessions are excluded.
- [x] Re-running the 2026-09-18 baseline reproduces its published figures in these units.

## Comments

Adam authorized ticket 05 and confirmed diagnosis/adapter/CLI-plugin test seams
and review against `35f45fb`. Implemented; acceptance remains Adam's.
Evidence, formulas, baseline fixture provenance and reproduction command:
`docs/measurement-ticket05.md`. No ticket-06 work or Hermes writes included.
Implementation `3106982`; independent Standards and Spec reviews: zero findings
on either axis. Final full suite: 131 passed, 2 optional live-Jev skips; mypy
retains the same 11 inherited errors, with no new diagnosis errors.
