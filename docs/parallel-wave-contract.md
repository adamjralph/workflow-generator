# Parallel waves (P13) — accepted contract

**Status: accepted by Adam on 2026-09-22; implementation ticket
[28](../../.scratch/workflow-generator/issues/28-execute-and-check-one-parallel-wave.md).
No live call is authorized by this document, and no dependency or production change
is implied.** Repository baseline for the frozen proposal and its two independent
reviews: `00807380b120f343780b26f697843dacfe054066`. The implementation review
baseline is recorded in the ticket.
This document answers the decision gate **D1** in
[the whole-product delivery map](../.scratch/workflow-generator/map.md) and drafts
the boundary of proposed slice **P13** ("one Transform-only Fork/join wave").
Unrelated working-tree edits are not part of this proposal and were not touched.

Requested by Adam after the offline transport investigation: draft the concrete
parallel-wave contract (branch state isolation, reducer binding and cost,
reservation granularity and refusal, failure selection/cancellation, canonical
event ordering versus actual completion evidence) for approval.

Two independent reviews (Standards and Spec, baseline above) were run against this
document; every finding they raised is applied here, and the items they confirmed
correct are unchanged.

---

## 1. What already exists, and what this adds

Already accepted and unchanged by this proposal:

- `Fork` is an admitted declaration on the spec edge type
  (`agent_lab/spec.py:99-108`): `source`, `outcome`, `branches` (≥ 2), `join`.
  Admission already validates reference integrity, distinct branches, a separate
  join (`:194-204`), and that every path in the branch region converges at the
  join before terminating (`_joins`, `:229-259`).
- One run-level step owner exists and already serializes concurrent branches
  (`agent_lab/accounting.py:22-36`): per-step reservation under a lock, an equal
  `max_steps` requirement across branches of a run, and `snapshot()` to refresh a
  stale branch budget at a join. Ticket 02 accepted this as shared parallel
  accounting.
- The generated graph driver (`agent_lab/generation.py:83-150`) emits one step and
  one decision node per spec node, with one decision branch per target — the
  declared outcomes plus the implicit `FAILED_VALIDATION` / `FAILED_BUDGET`
  targets (`:132-141`). The framework it emits into supports broadcast forks, joins
  with reducers, steps that hand off to a join, and structured concurrency (anyio
  task group, `pydantic_graph/graph_builder.py:33,484,700-741,958`).
- The reference driver (`agent_lab/reference.py:192-240`) is a sequential walk
  that dispatches on `Route` edges only.
- Safety terminals are already required for **every** spec, at compile time and
  regardless of Fork: `compile_reference` emits `missing_safety_terminal` when
  `FAILED_VALIDATION` or `FAILED_BUDGET` is absent (`agent_lab/reference.py:297-299`),
  because the emitter maps those targets to terminals
  (`agent_lab/generation.py:132-141`). This proposal adds no rule there and must not
  weaken it.
- Conformance compares structure plus behaviour — state, terminal, used_steps,
  parsed trace, raw bytes and raw log digest (`agent_lab/conformance.py:197-210`).

Three existing gaps must be closed by this slice, and are named here so they are
not discovered mid-implementation:

- A Fork spec cannot compile at all today: `compile_reference` rejects every
  non-`Route` edge as `unsupported_edge` (`agent_lab/reference.py:294-296`), so
  `check_conformance` returns before comparing anything
  (`agent_lab/conformance.py:131-132`).
- `_structure` asserts `isinstance(edge, Route)` (`agent_lab/conformance.py:59`), so
  the first compiled Fork spec would raise an untyped `AssertionError` instead of
  producing a `structural_mismatch`. §6 replaces that assertion with a typed Fork
  field.
- Neither driver accepts a reducer mapping: both take `bindings` plus the optional
  keyword mappings `judgments` and `model_operations`
  (`agent_lab/reference.py:243-247`, `agent_lab/conformance.py:103-109`), and
  admission emits `unbound_reference` for any non-model Transform whose `operation`
  is missing from `bindings` (`reference.py:292-293`). `reducers` must be threaded
  through the same seam as `model_operations` (§3, §8), as an optional keyword that
  changes nothing when the spec has no Fork: unused, and every existing finding
  unchanged.

This proposal adds exactly: Fork execution in both drivers, one caller-supplied
deterministic reducer per wave, declared-order determinism, a deterministic budget
refusal, and the conformance comparisons a wave needs. It adds no sixth node kind,
no new runtime, no async binding contract and no persistence.

## 2. Decisions requested (D1)

| D1 question | Proposed answer | Section |
|---|---|---|
| Synchronous-binding concurrency mechanism | Branch work stays synchronous and is dispatched to worker threads (`asyncio.to_thread`) per branch step, bounded by a `wave_concurrency` run parameter declared beside `bindings`, default `min(branch_count, 4)`, range 1-16; reference stays sequential | §5 |
| Reservation granularity and refusal | Granularity stays **one step**, but a wave is admitted only if the remaining budget covers the statically computed worst-case wave cost; refusal happens once, at dispatch, before any branch step or model call | §4 |
| Reducer cost | The join is declared as a framework join whose reducer is a private item collector; the caller reducer is invoked once, from the join node's single step, which is charged exactly one reserved step on the success path and on the failure path alike | §3, §4 |
| Failure selection and cancellation | **Complete-all-then-select**: no sibling cancellation; every branch path converges on the join carrying either a result or a failure; the wave fails closed on the first failing branch in declared order after all branches have stopped | §5 |
| Canonical event ordering vs actual completion evidence | Logs are appended durably at completion (actual order, unchanged mechanics); the **canonical projection** is the compared artefact; raw interleaving and per-event sequence numbers within a wave are recorded evidence and explicitly non-normative | §6 |
| Branch regions within one wave | **Pairwise disjoint** (a decision, not a by-product): without it, an event on a shared node cannot be attributed to a branch subsequence, and the wave's worst case would double-count it | §7 |

## 3. Declarations, bindings and state

**Reducer binding.** A new caller-supplied mapping, keyed by join node id:

```python
reducers: Mapping[str, Callable[[S, tuple[S, ...]], TransformResult]]
```

It receives a detached snapshot of the fork-entry state and the branch results in
**declared branch order**, and returns the same `TransformResult` every other
Transform returns, so the join's declared outcomes route exactly like any other
node's. The caller must supply a deterministic reducer. The public mapping API does
not create fresh callable instances per driver or per case: each driver owns its
supplied reducer mapping, and callable state may persist across cases. Conformance
checks the *observed* guarantee separately for each driver: if supplied cases
present identical captured reducer inputs at the same join but produce different
admitted outputs, it reports a `behavioral_mismatch`, even if both drivers agree
with each other or later steps mask the difference. The captured inputs are the
detached fork-entry state and declared-order branch states before reducer mutation;
the admitted output includes join state, outcome, target and failure. A passing
report does **not** establish callable purity, statelessness, or consistency for
unsupplied inputs. A single invocation or cases with distinct captured inputs
cannot exercise this repeated-input check. Reducer factories and callable-state
isolation are outside this slice.

**Join declaration.** `Fork.join` must name a `TransformNode` in `spec.nodes`, and
the `reducers` mapping (keyed by join node id) is **authoritative** for it: the
compiler and both drivers resolve a join node's binding from `reducers[node.id]`,
never from `bindings`. `operation` stays a required field of `TransformNode`
(`agent_lab/spec.py:34`) and remains the binding key for every other Transform
(`reference.py:232-234`, `generation.py:122,195`); for a join it is a label only,
it need not appear in `bindings`, and `unbound_reference` (`reference.py:292-293`)
must not be emitted for it. The join node must not declare a model operation (§7),
and the reducer is not a second call after any other binding. The framework's
accumulation machinery is used only as a private item collector
(`ReduceFirstValue` and `cancel_sibling_tasks` are never used): items
arrive in completion order, are re-ordered in the join step, and the join step runs
once, when every branch of that fork run has stopped
(`pydantic_graph/graph_builder.py:700-741`, `pydantic_graph/join.py:203-235`). No
caller code runs per item, and the caller reducer runs exactly once.

**Branch identity per item.** Whatever the emitter's wiring, each branch delivers
exactly one item to the join, that item names its branch (declared index), carries
either the branch's converged state or its failure record, and the hand-off itself
reserves **no** step. Naming the branch is what makes completion order irrelevant.

**Branch state.** Each branch executes through its own branch-scoped execution
holder: its own `state`, its own `repeat_counts`, and a budget view refreshed from
the shared accounting. Branch entry states are detached copies of the fork-entry
state, produced by the same round-trip strict validation used at every existing
boundary (`reference.py:62-68`); the same rule applies to the reference driver's
2nd..Nth branch. Branch steps never read or write the run-level state object
(`generation.py:86` builds one `_Execution` and `reference.py:99,138` writes its
`state` for every step today, so this is a real change, not a restatement), and
branch-local mutations cannot reach a sibling or the run. The only path from branch
states into the run is the reducer's returned state. The reducer receives detached
copies, so mutating its inputs cannot change the caller's state object.

**Unchanged boundaries.** The step owner, budget and log remain shared per run id;
branch work never holds the accounting lock; model operations remain the only
declared network path and are unchanged by this slice.

## 4. Budget: deterministic admission, then per-step draw

Today, two concurrent branches contend for the same step counter, so *which*
branch is refused when the cap runs out depends on which branch happens to ask
first. That would make the reference and the graph driver disagree on the refusal
evidence, and make a repeated run of the graph driver differ from itself.

Proposed rule, replacing contention-driven refusal for waves:

1. **Static worst case.** For each branch, compute the conservative static upper
   bound of the steps that branch can spend before reaching the join. For this
   slice that is exact: the branch region contains only Transform nodes, each
   visited once, so `worst(branch)` = the number of nodes in the branch region
   (the region is the walk `_joins` already performs, stopping at the join and
   excluding it, so `sum(worst) + 1` does not double-count the join). Admission
   must expose that region — as one shared helper used by both `_joins` and the
   drivers — because neither driver carries fork structure today (§1). Regions
   containing `Loop` nodes arrive with P14 and need their own rule; see §10.
2. **Admission before work.** `required = sum(worst(branch)) + 1` (the reducer's
   step). At fork dispatch, if `remaining_steps < required`, the wave is refused
   **before any branch step and before any model call**: typed `FAILED_BUDGET`
   with detail `wave_budget_refused`, naming `required`, `remaining_steps` and each
   branch's worst case. Nothing is spent, nothing is refunded, and both drivers
   produce the same refusal because both compile through the same admission path
   (`generation.py:186-188` reuses `compile_reference`).
3. **Draw.** Otherwise branches draw steps one at a time exactly as they do today
   (`RunAccounting.reserve` unchanged, one reservation per step visit). Because
   admission guaranteed the worst case fits, a mid-wave denial cannot occur; the
   only remaining ways a branch stops early are declared outcomes and validation
   failures. Each step's event records **that step's own reservation value** as its
   `used_steps` — not the shared field read at append time, which under overlap can
   already have been advanced by a sibling (`reference.py:147,163` reads
   `self.budget.used_steps`). In a linear run the two are identical, so non-wave
   evidence is unchanged; the run's total spend remains the shared accounting
   authority and is compared separately (§6).
4. **Reducer step.** The join reserves one step before it runs, on the success and
   the failure path alike; under (2) this reservation cannot be refused, because
   the branch worst cases plus this step are exactly what `required` covered — so
   refusal here is unreachable by construction, and should it ever happen the join
   step records a `FAILED_BUDGET` failure event and no reducer runs. On the success
   path the join step invokes the caller reducer once. On the failure path it does
   not invoke the reducer: it records the wave's failure event and returns the
   selected terminal. Running the join step on both paths is what keeps "no hidden
   or free work" true and gives the two drivers the same run-level event set for a
   failed wave (§5, §6).

Consequence: spend is the actual number of steps, `used_steps` totals agree between
drivers, and refusal evidence is a function of the spec and the current spend only
— never of completion order. The cost is conservative admission: a wave whose
worst case exceeds the remaining budget is refused even if its actual cost would
have fit. That trade is taken deliberately in exchange for determinism.
Block reservation (reserving the whole worst case up front and releasing the
remainder at the join) would give the same guarantee with a new accounting
primitive; it is rejected here as more machinery for the same observable rule.

## 5. Execution: overlap, failure selection, evidence

**Reference driver.** Sequential, branches in declared order, one branch at a time.
This is the authoritative semantics ADR 0008 pins; it does not overlap and does not
pretend to. When a branch fails, the reference records that branch's failure and
continues with the remaining branches — it does not stop at the branch's failure
terminal (`reference.py:198` ends the walk at any terminal today), which is what
makes complete-all-then-select observable in both drivers.

**Graph driver.** Branches overlap. A branch step's blocking work runs in a worker
thread (`asyncio.to_thread`), matching the accepted concurrency precedent in
`lessons/lesson_02_workflow/test_parallel.py:28,103`. Concurrency is bounded per
wave by `wave_concurrency`, a **run parameter declared beside `bindings`** (not a
spec field: a scheduling parameter must not change the spec digest, admission or
the compared artefact), default `min(branch_count, 4)`, accepted range 1-16
(outside it the run configuration is rejected before any work), values above the
branch count accepted and producing no extra concurrency. The value is recorded as
observed evidence and is not part of the compared artefact. Making bindings async
instead would change the binding signature for every existing spec; running
branches serially would fail P13's stated overlap evidence. Both are rejected.

**Failure selection.** No sibling cancellation is used, and the framework's
cancellation helper (`ReducerContext.cancel_sibling_tasks`, `ReduceFirstValue`) is
never invoked for generated waves. Every branch path — including the implicit
`FAILED_VALIDATION` and `FAILED_BUDGET` targets — converges on the join carrying
either a result or a failure record. When every branch has stopped:

- if any branch failed, the wave terminates at the **first failing branch's own
  failure terminal, in declared order** (`FAILED_VALIDATION` for a validation or
  binding failure, `FAILED_BUDGET` for a budget failure), the reducer is **not**
  invoked, and no branch state is merged — the run's state is the fork-entry state.
  The failing branch's own step event already records its failure exactly as any
  step does today (`reference.py:143-150`); the join step then runs as the wave's
  closing step, is charged its one step (§4.4), records one run-level event whose
  transition and terminal are the selected terminal and whose detail names the
  first failing branch index (`failure: wave_branch_failure`), and returns that
  terminal. Both drivers therefore end a failed wave with the same step events, the
  same run-level event and the same spend;
- otherwise the reducer is invoked once with the branch results in declared order.

This is what makes the two drivers agree: both run every branch to completion, and
both select the first failure and the terminal in declared order, without depending
on who finished first. Fail-fast cancellation is rejected: the set of events from a
run would then depend on completion order, and no durable cancellation contract
exists.

A branch failure is therefore carried as that branch's item to the join, never as a
run end: ending a task ends the run and would cancel the remaining siblings
(`pydantic_graph/graph_builder.py:700-706`). The hand-off is a node that returns the
join node rather than a `builder.end_node` destination: a node returning
`Join.as_node(item)` produces a join item (`pydantic_graph/join.py:203-235`,
`pydantic_graph/graph_builder.py:958`). Inside a wave the emitted
decision for a branch node routes the join target and the two failure targets to
that hand-off; the run's terminal label is produced by the join step, so the
graph's output type stays `str` (`generation.py:83-150`) and the exact wiring shape
(one hand-off node per branch, or a direct hand-off from the converging step) is
the implementer's choice.

**Audit.** Events are appended durably when they happen (`append_next`, unchanged
lock semantics). Audit I/O failure still stops the run with `AuditError` and
produces no result. Nothing is buffered: no wave may trade away durability of work
already performed, and no unacknowledged durability window is introduced.

## 6. Conformance changes for waves (explicit amendment to ADR 0008)

ADR 0008 requires the emitted artifact to produce "same events, same digests" on a
recorded run. With genuine overlap that cannot mean identical byte order: two runs
of the *same* driver may interleave branch events differently. For wave cases the
comparison becomes:

- **Structure.** Fork edges are compared as a field of their own —
  `(source, outcome) → (tuple(branches), join)` — alongside the existing route
  fields, replacing the `assert isinstance(edge, Route)` at
  `agent_lab/conformance.py:59`. The branch sequence is an **ordered tuple**, not a
  frozenset: branch order is normative here (it fixes reducer input order and which
  failing branch is selected), and `_strict_equal` (`:23-39`) compares tuples
  positionally. An altered branch sequence, branch set or join is a
  `structural_mismatch`.
- **Behaviour, compared:** typed result state, terminal, the run's total
  `used_steps`, the **per-branch event subsequence** of each branch (declared
  order, taken from the projection's normalised groups, so per-event spend is never
  compared verbatim), the **canonical projection** of the whole log, the assertion
  that reducer input arrived in declared order, and the wave-refusal record when a
  wave was refused.
- **Canonical projection, defined.** The wave's boundary records are the
  run-level event of the fork-dispatch step and the run-level event of the join
  step — the latter present on the success path and on the failure path alike
  (§4.4, §5). Branch events are attributed to a branch by the node ids of that branch's
  region (unambiguous once §7's disjointness rule holds) and are laid out grouped
  and in declared branch order between those two boundaries; run-level events keep
  their relative order. Two completion-order-dependent facts are normalised:
  the sequence number `seq` is regenerated in the projection's order
  (`agent_lab/runlog.py:25-35`), and each step's own reservation value is compared
  as per-branch visit counts plus the run total instead of per event (§4.3). Every
  other field — node, stage, transition, terminal, target, failure, judgment and
  assessment digests, repeat counts — is compared verbatim. The compared value is
  the digest of that projection.
- **Recorded, not asserted:** the raw interleaving, the raw `seq` values and the
  per-step reservation values of wave events. They remain in the evidence files as
  the actual completion record; the projection is derived from them and never
  replaces them.
- **Weakened guarantee, stated explicitly:** for wave cases, raw byte and raw digest
  equality across the two drivers (and across repeated runs of one driver) is no
  longer required. The raw logs are still written, retained and digest-recorded;
  the canonical projection digest carries the comparison. Non-wave cases keep the
  existing byte-level comparison unchanged.

Rebuilding a first-section ordering from normalised data would be manufacturing
evidence; deriving a declared-order projection from recorded per-branch sequences
is not: every canonical event is a recorded event, only its placement between the
wave's dispatch and join events, its sequence number and its per-event spend
rendering are defined.

## 7. Admission findings (fail closed before any work)

New typed findings, in addition to the existing fork checks:

- `join` node is not a `TransformNode`;
- a model-operation `Transform` anywhere in the wave — a branch region node or the
  join — since the out-of-scope boundary in §10 is otherwise documented but not
  enforced, and a breach costs network access and money;
- no reducer binding supplied for a declared join, or a reducer supplied for a
  node that is not a join;
- one join claimed by more than one Fork;
- a Fork, its join, a node in its branch regions, or its reducer that `entry`
  cannot reach: an admitted wave that can never run would silently carry an unused
  reducer, which is precisely the "unsupported or unreachable shape" the map
  requires to be rejected before work (this is stricter than the general policy
  that permits unreachable non-wave nodes, `generation.py:142-143`);
- a Fork nested in another Fork's branch region (out of scope for this slice);
- two branches of one Fork sharing a node: branch regions must be pairwise disjoint
  so that an event can be attributed to exactly one branch subsequence and the
  wave's worst case counts each node once (§2, §4.1, §6);
- a Fork region containing a node kind outside this slice's admitted set
  (Transform only; Decision/Loop arrive with P14, Judgment with P15);
- a branch region that can reach a terminal before the join (already rejected by
  `_joins`; retained as a regression guard).

Each is rejected at admission, before any binding is invoked, and therefore before
any spend. No finding is added for the safety terminals: the compile-time
`missing_safety_terminal` gate already covers every spec (§1).

## 8. Public test seam

Authored spec + `reducers` + bindings + `wave_concurrency` + an independently
supplied candidate + typed cases → conformance report and real logs, at the same
seam the existing slice uses (`agent_lab/conformance.py:103-218`). Cases:

1. Hand-authored expected branch states, reducer output and spend for a two- and a
   three-branch wave, independently of driver agreement.
2. **Overlap proof without timing:** branch bindings rendezvous on a
   `threading.Barrier` with a short timeout; the bounded-concurrency driver
   completes and records overlap, `wave_concurrency=1` records the barrier
   timeout, and an out-of-range value is rejected before work. Observed overlap is
   evidence, never a pass/fail duration criterion.
3. Declared-order reducer input under adversarial completion order (branches
   deliberately finishing out of order).
4. Detached state: a branch attempting to mutate the run-level or sibling state
   cannot; reducer input mutation cannot change caller state.
5. Uneven branches, including a branch with a single node.
6. Multiple branch failures select the first in declared order and terminate at
   that branch's terminal with the fork-entry state; a single failure does not
   invoke the reducer; the failing branch's and the join step's events are both
   recorded and both charged, with the hand-authored spend of the failed wave.
7. Invalid reducer output (wrong type, undeclared outcome) fails closed.
8. Budget: refusal at exactly `remaining == required - 1` before any branch step
   and any model call in both drivers, and admission at exactly
   `remaining == required` completing with no denial and the hand-authored spend.
9. Audit I/O failure stops the run and yields no passing result.
10. Adversarial candidates: reordered branch sequence, extra branch, changed join,
    changed reducer output — each fails as `structural_mismatch` or
    `behavioral_mismatch`, never silently.
11. No network: the whole path executes with no IPv4/IPv6 network sockets
    available; local AF_UNIX sockets needed by asyncio remain available.
12. Every §7 rejection, each failing before any binding is invoked.
13. The join-binding exemption of §3 in both directions: a wave whose join node's
    `operation` is absent from `bindings` compiles and runs, resolving the reducer
    through `reducers[join_id]` and emitting no `unbound_reference` for that node;
    a stray `bindings` entry under the same operation name is ignored, while a
    spec with no Fork still rejects an unbound non-model Transform exactly as
    before.
14. Repeated identical captured reducer inputs across supplied cases with divergent
    admitted join outputs fail conformance for each affected driver, including when
    the two drivers diverge in lockstep or a later step masks the join difference.
    A deterministic reducer passes this check; it is not a proof of purity for
    arbitrary caller-owned callable state or inputs not supplied as cases.

## 9. Mapping to P13's stated acceptance evidence

| P13 requirement | Where this contract answers it |
|---|---|
| Hand-authored expected outputs, spend, not driver agreement alone | §8.1 |
| Barrier-based overlap proof, not timing | §5, §8.2, §8.3 |
| No shared-state lost updates; mutation cannot escape | §3, §8.4 |
| Missing/invalid bindings, unsupported or unreachable shapes rejected before work | §7, §8.12 |
| Short/exact budgets, multiple failures, invalid reducer output, audit I/O failure | §4, §5, §8.6-8.9 |
| Altered branch order, join/reducer configuration, candidate behaviour cannot pass silently | §6, §8.10 |
| Exact persisted evidence agreement under an approved deterministic contract | §4.3, §6 |

## 10. Out of scope, deliberately

Nested or sequential waves (P14-P16), any Gate or resume inside a wave (P17-P18),
Judgment inside branches (P15), model operations inside branches (rejected at
admission, §7), waves under `Loop` bodies, cross-wave reducers, and any claim that
a passing wave proves semantic correctness, savings or production readiness.

Both items below were approved by Adam on 2026-09-22 with the contract ("I'll accept
A2 through B7"), so they are decided rather than handed forward:

- **Loops inside a wave (P14)**: the worst case uses a conservative multiplier over
  the region cost that counts the extra `exhausted` visit of a `Loop` node — up to
  `max_iterations + 1` visits (`agent_lab/reference.py:127-132`). P14's contract must
  use `max_iterations + 1`, not `max_iterations`, which would under-estimate and
  re-open the mid-wave denial this contract removes.
- **The `wave_concurrency` cap value**: default `min(branch_count, 4)`, maximum 16,
  range 1-16. These values are fixed by the decision rather than left to
  implementation tuning; the run-parameter declaration surface and the range were
  already part of the decision.

Also out of scope: spec/bundle identity and approval work, which belongs to D2.
