# Workflow Generator handoff

## Current authorization and state

- Working branch: `main`. Ticket 01 was closed by Adam at `a158632`; foundation
  promotion is `cddadc6` (from source lab `ce34093`).
- **Ticket 02 is accepted and closed** at Adam's explicit request. Implementation
  is `7e1d517`; independent review and final verification are `c492e93`.
  Do not begin tickets 03–06 without new authorization.
- `agent_lab/` is the sole repo-local runtime; no sibling imports or changes.
- No Hermes source, configuration, authentication, or live-state access occurred.
  All new execution evidence uses synthetic offline data and temporary stores.

## Start here

1. `CONTEXT.md` in full, especially §2, §5 and §9–§11; all nine `docs/adr/` files.
2. `.scratch/workflow-generator/issues/02-fix-parallel-accounting.md`.
3. `docs/foundation/README.md` for provenance and inherited limitations.
4. `docs/foundation/parallel-accounting.md` for the concurrency contract,
   criterion-by-criterion red/green evidence and reproduction commands.
5. `README.md` for local setup and imports.

The product spec is not this build's target. Its generation half remains
unticketed; do not invent a spec format, packaging, naming, or community decision.

## Ticket 02 implementation

- Run-level `RunAccounting` is injected through `Deps`. Branches share one owner,
  even if they use distinct judgment sources. A short lock reserves before work;
  model work does not hold locks. Frozen state budgets are snapshots, refreshed
  at the join. Fresh continuation seeds its owner from the joined typed state.
- Runtime event numbering is allocated atomically with append, in log order.
  Caller sequence hints no longer allocate numbers. Separate log handles and
  resume continue per-run numbering.
- Branch findings are returned through reducers, then `collect_findings` joins
  note suffixes without overwriting common notes. It does not merge branch
  stages/artifacts or choose a terminal; the caller owns post-join routing.
- The existing business route remains linear; synthetic fan-out and overlapping
  invocations prove its shared core semantics, without adding a general engine.
- Plain remains the reference; both drivers still use `workflow.step`.

## Verification

- New concurrency tests: **10 passed**.
- `AGENT_LAB_JUDGMENT=stub .venv/bin/python -m pytest -q`:
  **75 passed, 2 optional live-Jev skips**.
- Mypy: the same **11 inherited errors in 3 files**, unsuppressed, no unrelated
  cleanup. No green typechecking claim.
- The four historical red failures are retained in
  `docs/foundation/parallel_red.py`, runnable against an isolated archive of
  `cddadc6`; they demonstrate colliding sequences, lost spend, exceeded cap,
  and one of three findings surviving the unsafe shared-holder write.
- Two independent parallel worker reviews against `cddadc6`: Standards found
  zero violations/actionable smells (one non-blocking log-scan performance
  observation); ticket-02 Spec found zero actionable findings. Details and the
  findings-data-channel qualification are in `docs/foundation/parallel-accounting.md`.

## Boundaries and remaining work

Diagnosis adapters, measurement, plugin/generator/spec/conformance engine,
metrics, and new serialization are **not implemented**. Budget reservations are
in-process, not distributed/crash-durable accounting. Parallel callers must
share the accounting owner and return values rather than mutate a shared holder.
The event writer uses local filesystem advisory locking; explicit-sequence
import/replay writes must not be mixed with active runtime writes.

The existing approval semantics still bind run/draft, not a spec/bundle pair.
No claim of production readiness, cost improvement, or general spec conformance
is made. Preserve the plain-reference rule and the read-only Hermes boundary.

## Decisions still owned by Adam

- Community vs internal use (deferred); blocks spec format and packaging.
- Product naming and distribution.
- Whether gated writes to Hermes are ever added.

Ticket 02 is resolved. The remaining diagnosis dependency order is
03 → {04, 05} → 06; none is authorized by this closure request. The historical measurement baseline and its paths
remain in `CONTEXT.md`; do not access live data to remeasure during ticket 02.
