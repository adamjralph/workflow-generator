# 28: Execute and check one Transform-only parallel wave

**Type:** task
**Status:** accepted by Adam (2026-09-25 05:40 AEST)
**Blocked by:** None for this ticket. Commit/push remains a separate Adam decision.

**Acceptance boundary:** Adam expressly accepted ticket 28 under the observed-case
contract after the final offline regression and two independent confirmations.
Conformance rejects divergent admitted reducer outputs for identical captured
inputs in supplied cases; it does not prove arbitrary callable purity or isolate
hidden mutable state. Acceptance authorizes neither a live workflow/model call
nor publication, commit or push.

**2026-09-25 05:36 AEST verification:** Corrected six-file hash
`24816c99411acf7e7e3bf2f300161b85511a7a2c551c0d1dbfe04471a3f2856b`
and nine-file contract-inclusive *review-time* hash
`a1b7d407e240e1ebcd5d1742a3be52bd8f54e2dbb72aa4647c586e169ba5b5e8`
were read back unchanged before this status note changed the issue's hash. New masked-join regression failed before correction;
final focused **252 passed**, mypy **35 files clean**, independent Standards/Spec
confirmation approved without blockers (`deleg_d6fdeb57`). Final-source full
regression **2,169 passed / 3 skipped**, exit **0** at
`/home/hermes/workflow-validation-scratch/v-Z4Ti6p/`. The three skips are two
opt-in live Jev tests and optional real Hermes plugin-loader check. This is
offline technical evidence, not a live workflow run or Adam's acceptance.

**2026-09-25 continuation:** Adam approved the narrow observed-case reducer
determinism boundary instead of a reducer-factory API. Contract §3/§8 and ADR 0011
now describe the supplied-case check, not callable purity or fresh callable state.
Independent confirmation of the amended contract and corrected implementation is
still outstanding. The prior Standards reviewer stopped on an approval denial
before source inspection; obtain specific permission before retrying that denied
step. No ticket acceptance, commit, push, publication or live model call follows.

**Verified implementation checkpoint:** Code/test manifest
`0a77b0bc3a1f517bc79f38ed2079701130f5ac527db5cb4283935ac82282ddb7`;
controller full suite **2,168 passed / 3 skipped**, exit 0 at
`/home/hermes/workflow-validation-scratch/v-rKzn37/`. Focused 251 and mypy
35-file pass plus limitations are in `docs/ticket-28-executor-evidence.md`.

**Scope approval:** Adam approved the D1 parallel-wave contract and ADR 0011 as
drafted on 2026-09-22 and selected this slice as the next implementation. The
contract is authoritative: [docs/parallel-wave-contract.md](../../../docs/parallel-wave-contract.md);
decision record: [ADR 0011](../../../docs/adr/0011-parallel-waves-are-declared-order-deterministic.md).
No live call is authorized.

**Review baseline:** `0e12a9a27cdd22252e9cb73c7b6f057a63e68d50` (repository HEAD
when published; the publication commit adds documents only).

## Goal

A caller authors a Fork with two or more single-Transform branches and one join; the
generated graph overlaps branch work, combines all results exactly once through a
caller-supplied deterministic reducer, and passes conformance against the
independently executing plain reference.

## Accepted boundary (contract §§2-7)

- Fork execution in both drivers: branch regions walked from the shared region helper,
  branch state detached from a detached fork-entry copy, and one caller-supplied
  `reducers` entry per join, keyed by join node id and authoritative over `bindings`
  (`operation` stays a required label that need not appear in `bindings`, and no
  `unbound_reference` is emitted for a join).
- `reducers` and `wave_concurrency` are optional keyword arguments on the existing
  binding seam (`compile_reference`, `generate_graph`, `check_conformance`); with no
  Fork they change nothing.
- `wave_concurrency`: run parameter declared beside `bindings`, default
  `min(branch_count, 4)`, accepted range 1-16, out-of-range rejected before any work,
  recorded as observed evidence and not part of the compared artefact. The reference
  driver stays sequential.
- Static admission: at fork dispatch the wave is admitted only if `remaining_steps`
  covers `sum(worst(branch)) + 1`, otherwise refused once as `FAILED_BUDGET` with
  detail `wave_budget_refused` naming `required`, `remaining_steps` and per-branch
  worst case, before any branch step or model call.
- Complete-all-then-select: no sibling cancellation; every branch path converges on
  the join; the wave fails closed on the first failing branch in declared order,
  terminates at that branch's own failure terminal with the fork-entry state, records
  the join step's closing run-level event (`failure: wave_branch_failure`), charges the
  join step one step, and does not invoke the reducer.
- Each step's event records that step's own reservation as `used_steps`.
- Evidence: durable append at completion unchanged; for wave cases the compared
  artefact is the canonical projection (branch events grouped in declared order between
  the fork-dispatch and join run-level events; `seq` regenerated; per-event spend
  normalised), while raw interleaving, raw `seq` and per-step reservations remain
  recorded and explicitly non-normative. Non-wave cases keep byte-level comparison.
- New admission findings (contract §7): join is not a Transform; model-operation
  Transform anywhere in the wave; missing reducer for a declared join; reducer supplied
  for a non-join node; one join claimed by more than one Fork; unreachable wave
  (Fork, its join, a branch-region node or its reducer not reachable from `entry`);
  Fork nested in a branch region; non-disjoint branch regions; branch-region node kind
  outside Transform; pre-join terminal (retained regression guard).

## Out of scope, rejected at admission where applicable

Nested or sequential waves (P14-P16), any Gate or resume inside a wave (P17-P18),
Judgment inside branches (P15), model operations inside branches, waves under `Loop`
bodies, cross-wave reducers, spec/bundle identity (D2), persistent spec format and live
model calls.

## Acceptance criteria

- [x] Hand-authored expected branch states, reducer output and spend for a two- and a
      three-branch wave, independent of driver agreement.
- [x] Barrier-based overlap proof without timing: bounded concurrency completes and
      records observed overlap, `wave_concurrency=1` records the barrier timeout, and an
      out-of-range value is rejected before work.
- [x] Declared-order reducer input under adversarial completion order.
- [x] Detached state: a branch cannot mutate run-level or sibling state, and reducer
      input mutation cannot change caller state.
- [x] Uneven branches, including a single-node branch, execute.
- [x] Multiple branch failures select the first in declared order, terminate at that
      branch's terminal with the fork-entry state, do not invoke the reducer, and both
      drivers record the same step events, closing run-level event and spend.
- [x] Invalid reducer output (wrong type, undeclared outcome) fails closed.
- [x] Budget: refusal at exactly `remaining == required - 1` before any branch step and
      any model call in both drivers, and admission at exactly `remaining == required`
      completing with the hand-authored spend.
- [x] Audit I/O failure stops the run and yields no passing result.
- [x] Adversarial candidates (reordered branch sequence, extra branch, changed join,
      changed reducer output) fail as `structural_mismatch` or `behavioral_mismatch`,
      never silently.
- [x] No network: the whole path executes without IPv4/IPv6 network sockets;
      local AF_UNIX sockets needed by asyncio remain available.
- [x] Identical captured reducer inputs across supplied cases with divergent admitted
      outputs fail conformance in either driver, even when both diverge in lockstep
      or downstream work masks the join difference; do not infer arbitrary purity.
- [x] Every contract §7 rejection fails before any binding is invoked.
- [x] Join-binding exemption in both directions: a wave whose join `operation` is absent
      from `bindings` compiles and runs through `reducers[join_id]` with no
      `unbound_reference`; a stray `bindings` entry under that name is ignored, while a
      spec with no Fork still rejects an unbound non-model Transform as before.
- [x] Offline regression and typechecking pass; independent Standards and Spec reviews
      run on the frozen implementation hash.

## Comments

Contract accepted by Adam on 2026-09-22 ("Approve as drafted"); P13 selected as the
next implementation over the `ready-for-agent` browser-designer ticket 13. Both
documents were reviewed by independent Standards and Spec agents on the frozen
contract hash before approval.
