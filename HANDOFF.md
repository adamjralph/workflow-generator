# Workflow Generator handoff

## Current authorization and state

- Working branch: `main`. Ticket 01 was closed by Adam at `a158632`; foundation
  promotion is `cddadc6` (from source lab `ce34093`).
- **Ticket 02 is accepted and closed** at Adam's explicit request. Implementation
  is `7e1d517`; independent review and final verification are `c492e93`.
  Ticket 03 was subsequently authorized by Adam, including its test seams and
  review baseline `02e4f6d`. **Ticket 03 is accepted and closed** at Adam's explicit
  approval. Implementation: `fcfb06c`; review fix and verification: `39a2bd2`;
  see `docs/diagnosis-ticket03.md`. Ticket 04 is now authorized, including the
  diagnosis/adapter/plugin seams and review baseline `c3260ab`. Its read-only
  proof and local plugin are implemented; normal activation requires Hermes
  config opt-in and remains an open acceptance issue. See
  `docs/read-only-ticket04.md`. **Ticket 05 is accepted and closed** at Adam's
  explicit request. Implementation: `3106982`; review and final verification:
  `7abde37`, against approved baseline `35f45fb`. See `docs/measurement-ticket05.md`.
  Adam requested cleanup ticket 07 for inherited mypy errors; it is recorded,
  not started. Do not begin tickets 06–07 without authorization.
- `agent_lab/` is the sole repo-local runtime; no sibling imports or changes.
- Ticket 03 read the historical baseline documents and pilot board/profile usage
  with read-only SQLite connections. No Hermes code/config/authentication or
  application records were edited. The historical run reproduced 10 calls/run;
  artifacts went to a temporary store outside Hermes. Automated tests are offline.

## Start here

1. `CONTEXT.md` in full, especially §2, §5 and §9–§11; all nine `docs/adr/` files.
2. `.scratch/workflow-generator/issues/02-fix-parallel-accounting.md`.
3. `docs/foundation/README.md` for provenance and inherited limitations.
4. `docs/foundation/parallel-accounting.md` for the concurrency contract,
   criterion-by-criterion red/green evidence and reproduction commands.
5. `README.md` for local setup and imports.
6. `docs/diagnosis-ticket03.md` for the new adapter, measurement, store, terminal
   entry point, fixture provenance, checks and explicit remaining limitations.

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

## Ticket 02 verification (historical)

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

## Ticket 03 verification

- `tests/test_diagnosis.py`: **20 passed**, using offline temporary databases.
- Final full suite: **95 passed, 2 optional live-Jev skips**.
- Mypy: the same **11 inherited errors in 3 files**, no diagnosis errors.
- Historical pilot run: `stillroom-research`, run `2`, reports **10 calls/run**
  (9 main-loop + 1 auxiliary), matching the original join and published one-run
  media-analyst figure; the rollup is only 9.
- Parallel review against `02e4f6d`: Standards found one path-guard violation,
  reproduced and fixed with independent follow-up, plus a nonblocking internal
  protocol-typing heuristic. Spec found zero ticket-03 findings. Details in
  `docs/diagnosis-ticket03.md`.

## Ticket 04 verification and open acceptance

- Implementation: `6271106`; evidence: `docs/read-only-ticket04.md`.
- Boundary tests: **10 passed**; diagnosis tests: **20 passed**; isolated real
  Hermes loader: **1 passed**. Final full suite with the loader opted in:
  **106 passed, 2 optional live-Jev skips**.
- Mypy retains the **11 inherited errors in 3 files**, no new diagnosis errors;
  plugin source typechecks as a script.
- Two-axis review against `c3260ab`: Standards found no violations and one
  nonblocking duplicated protected-root policy heuristic. Spec found one partial
  criterion: installation/registration works, but normal plugin activation still
  requires Hermes config opt-in. No extra implementation defect was identified.
- No live plugin installation, config activation, or authentication change was
  made. Ticket 04 remains claimed, **not accepted/closed**, pending Adam's decision
  on installation versus activation. Do not bypass the host activation gate.

## Ticket 05 verification

- Implementation: `3106982`; evidence: `docs/measurement-ticket05.md`.
- All four units, per-task worker/auxiliary/review separation, separate reasoning
  counters, and schema-1 artifact read compatibility are implemented. The plugin
  displays the same output through the unchanged terminal front door.
- Diagnosis and offline baseline tests: **45 passed**. Final full suite with the
  isolated real-loader opt-in: **131 passed, 2 optional live-Jev skips**.
- Mypy: the same **11 inherited errors in 3 files**, no new diagnosis errors.
- Historical baseline reproduced read-only: 23 runs, 214 calls (188 worker + 26
  auxiliary), 1,132,524 fresh input, 4,608,338 cache-read, 89,103 output; 9.3
  calls/run, 26,826 context/call, 49,240 fresh input/run, 80% cache hit. Newly
  exposed reasoning: 19,237. The newer September 19 run is excluded explicitly.
- Independent parallel review against `35f45fb`: Standards **0 findings**;
  Spec **0 findings**. No Hermes edits or host activation changes.
- **Ticket 05 is accepted and closed** at Adam's explicit approval. The inherited
  mypy cleanup was separately tracked in ticket 07 (subsequently authorized; see below).

## Ticket 07 — implemented, awaiting acceptance

- Adam authorized implementation and confirmed judgment/driver test seams and
  review baseline `70624c1`.
- All 11 inherited mypy errors cleared without suppressions: **14 files, zero errors**.
- SDK answer variants are checked; unreported token usage remains `None`, not zero.
  Malformed recordings and missing/invalid judgments produce recorded failure terminals.
- Offline suite: **158 passed, 3 optional skips**. No live calls or Hermes edits.
- Evidence and independent review results: [ticket 07](docs/typechecking-ticket07.md).

## Boundaries and remaining work

Ticket 03 adds `agent_lab/diagnosis/`: runtime-neutral attribution and calls/run,
fresh-process Kanban/Hermes readers, immutable digest-addressed diagnosis JSON,
and a minimal line-oriented terminal UI. Ticket 05 adds context/call, token counters/run, cache hit rate and per-task
worker/auxiliary/review breakdowns, preserving calls-only artifact readability.
Role/baseline management and the generator/spec/conformance engine remain unimplemented. Ticket 04 replaces live SQLite connections with checked temporary
DB/WAL copies, adds byte-preservation/admission tests, and provides a local
symlinked plugin. It does not bypass Hermes' config activation gate.
Diagnosis JSON does not settle workflow-spec serialization. Budget reservations are
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

Tickets 02, 03 and 05 are resolved. The remaining
diagnosis dependency order is 03 → {04, 05} → 06. Ticket 04 is authorized but
not yet accepted. Ticket 07 is implemented pending acceptance;
ticket 06 still requires new implementation authorization. Historical baseline
paths remain in `CONTEXT.md`.
