---
status: accepted
---

# Parallel waves are declared-order deterministic

**Status: accepted (2026-09-22). Implementation ticket:
[28](../../.scratch/workflow-generator/issues/28-execute-and-check-one-parallel-wave.md).
No implementation is authorized by this record beyond that ticket.** Contract:
[parallel wave contract](../parallel-wave-contract.md).

A wave (one `Fork` and its declared join) may execute its branches concurrently in
the emitted graph while the plain driver stays sequential. If nothing else is
decided, concurrency leaks nondeterminism into the three things this project treats
as evidence: which branch is refused when the step cap runs out, which branch's
failure is reported, and the order of events in the log. Each of those would then
differ between the two drivers and between repeated runs of one driver, which is
exactly what [ADR 0008](0008-conformance-pins-the-plain-driver-as-reference.md)
exists to prevent.

So the wave contract fixes determinism at four points instead of letting the
scheduler decide them:

- **Admission is static.** Remaining budget must cover the branch region's
  worst-case step cost before dispatch, so refusal happens once, before any branch
  step or model call, and identical in both drivers.
- **Reducer input is declared order.** Branches run in whatever order they finish;
  the reducer sees the branch results in declared order and is invoked exactly once,
  as the join node's own single step.
- **Failure is complete-all-then-select.** Every branch path, success or failure,
  converges on the join. No sibling is cancelled. The wave fails closed on the
  first failing branch in declared order after all branches have stopped, so the
  event set and the spend do not depend on who finished first.
- **Actual order is recorded; canonical order is compared.** Events stay durable at
  completion, and the compared artefact for a wave is a declared-order projection
  of those recorded events, in which only the sequence number and the per-event
  step count — the two fields that genuinely depend on completion order — are
  rendered canonically.

This narrowly amends the "identical events and digests" rule for wave cases only:
ADR 0008, ADR 0001 (line 7) and CONTEXT §9.2 / §11.2, all of which state it. For
waves it means the same canonical projection, the same per-branch subsequences and
the same totals, not the same raw byte order. Non-wave cases keep byte-level
comparison.

## Considered options

- **Fail-fast cancellation of siblings** (the framework's `cancel_sibling_tasks`):
  the surviving event set depends on completion order, and no durable cancellation
  contract exists. Rejected.
- **Per-step contention with completion-order refusal**: correct totals, but the
  refusal and failure evidence differ between drivers and between runs. Rejected.
- **Reserve the whole worst-case block up front and release the remainder at the
  join**: same observable guarantee as static admission with a new accounting
  primitive. Rejected as more machinery for the same rule; revisit if a later slice
  needs mid-wave enforcement.
- **Buffer branch events and append canonically at the join**: restores
  byte-identical logs, at the cost of a real durability window in which work already
  paid for is not yet recorded. Rejected: evidence of performed work outranks byte
  equality, and the comparison power is retained by the canonical projection.
- **Serialise branches** to keep the existing byte-level comparison: no concurrency,
  so P13's overlap evidence cannot be produced and the delivered capability would be
  nominal. Rejected.
- **Async bindings**: makes branches overlap naturally, but changes the binding
  contract for every existing spec and driver. Rejected for this slice in favour of
  dispatching synchronous trusted bindings to worker threads.

## Consequences

Admission must compute a conservative static worst case per branch region and
refuse a wave that cannot fit; a wave whose actual cost would have fit can still be
refused, and that conservatism is the accepted price. The join step is charged one
step on the success and the failure path alike, and the statically required cost
already covers it. Conformance gains a fork
structure field, per-branch subsequence comparison and a canonical projection
digest, and loses raw-order equality for wave cases — recorded in the report rather
than left implicit. Branch state must be detached per branch, and the reducer's
inputs must be detached from all of them. Every step's event must record its own
reservation rather than the shared counter read at append time, or the wave
evidence is completion-order dependent again. The existing compile-time
`missing_safety_terminal` gate, which already requires `FAILED_VALIDATION` and
`FAILED_BUDGET` for every spec, must not be weakened: a failed wave terminates at
the first failing branch's terminal.

Admission also gains restrictions the contract records and this ADR does not
restate: pairwise disjoint branch regions within one wave, no unreachable wave, no
model-operation Transform anywhere in a wave, and no shared join between forks. The
contract is authoritative for them.

Nothing here authorizes nested waves, gates or resume inside a wave, Judgment in
branches, model operations in branches, or a persistent spec format.

The reducer-bound join is a declared variant of ADR 0007's Transform mapping, in
the sense of that ADR's own "Accepted amendment" section: it is a `TransformNode`
whose binding is the wave's reducer, its `operation` is a required label that need
not appear in `bindings`, it declares no model operation, it is invoked once, and
it introduces no sixth node kind.
