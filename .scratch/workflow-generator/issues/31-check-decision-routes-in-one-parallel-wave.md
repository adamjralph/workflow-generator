# 31: Execute and check Decision routes in one parallel wave

**Type:** task
**Status:** accepted by Adam after local validation; scoped ticket-31 commit/push authorized.
**Blocked by:** Ticket 28 (accepted Transform-only wave; dependency already delivered). No new uncompleted ticket blocks contract review.

## What to build

A caller authors one Fork with Decision routes inside pairwise-disjoint branches. The plain reference walks branches in declared order; the generated graph runs branch work concurrently. Branches may take different-length routes before the same join. Both drivers select the same declared-order failure, preserve isolated branch state, invoke the join reducer once only on success, and produce case-scoped conformance evidence. Keep the P13 one-wave boundary, route-only outer execution, and deterministic no-network bindings.

## Acceptance criteria for a future implementation

- [x] Admit supported Transform/Decision branch DAGs whose every route converges on the join; reject cycles, outside entry into a branch/join, pre-join terminal paths, model operations, Judgment/Loop, nested/sequential waves, Gate, and unsupported shapes before invoking any binding.
- [x] Both drivers execute all branches to completion, including uneven chosen paths; the graph genuinely overlaps independent work within the accepted concurrency cap. Decision bindings use the existing strict result and route-label rules.
- [x] Admission charges the fork source as today, then before any branch work refuses when remaining steps are less than the sum of each branch's **maximum reachable node visits across all declared Decision outcomes** plus the one join step. No branch may exhaust budget mid-wave after admission; demonstrate just-short and exact-limit cases with hand-authored spend and refusal detail.
- [x] On one or multiple branch failures, complete all siblings, choose the first failing branch in declared order, retain fork-entry state, charge/record the closing join step, and do not invoke the reducer. Audit I/O failure still stops without a passing result.
- [x] Preserve raw completion evidence; compare a canonical projection that retains the chosen per-branch event sequence, Decision labels and failures. Distinct paths must not be flattened into static-region order or silently accepted by candidate mutations. Non-wave raw-byte comparison remains unchanged.
- [x] Supplied-case conformance exercises path alternatives, unequal branch lengths, reversed completion order, detached state, invalid binding output, failures, mutation of candidate routes/branch order, and no-network execution. Report observed-case reducer determinism only, not callable purity.
- [x] Focused and full offline tests, mypy, and independent Standards/Spec review on an agreed frozen baseline are recorded before acceptance; no live model/provider run.

## Boundary / decisions before ready-for-agent

**Frozen with Adam's explicit implementation go:** review baseline `3e1a30f2425617cdcd8508464cd2db7a27dbd8fe`. For each branch, compute the longest reachable acyclic path from its entry to the join, counting one visit per Transform/Decision and excluding the join. Sum those maxima and add one join step. Reject cycles, terminal paths before the join, and outside entry before work. The source step is already spent at dispatch. Refusal records `required`, `remaining_steps`, and declared-order `branch_worst`; exactly sufficient remaining budget admits the wave. A divergent-arm fixture (where region size exceeds either route) distinguishes this refinement from `len(region)`; a deep DAG fixture prevents an accidental Python recursion bound. The public seam is authored spec + bindings/reducer + independent candidate + typed cases → report and persisted logs, including path alternatives, failure and refusal evidence. This freezes the local implementation contract, not acceptance or publication.

## Answer

Implemented locally and checked at the public seam. [Executor evidence](../../../docs/ticket-31-executor-evidence.md) records **124 focused passed**, **2,367 full offline passed / 3 optional skips (exit 0)**, mypy clean in 43 source files, independent review findings and their corrections. Adam accepted ticket 31 and separately authorized the scoped commit and push. This does not authorize ticket 32, live calls or inclusion of sibling edits.
