# Ticket 03 — diagnose one Kanban run

## Scope and public seams

User authorized ticket 03 and confirmed the adapter, diagnosis/store entry point,
and terminal smoke-test seams. Review baseline: `02e4f6d`.

- `RunAttributionAdapter.attribute(run_id)` returns frozen `RunAttribution`:
  runtime, run id, session ids, role, workflow identity. No Kanban assumptions
  occur in `diagnose()`; an independent two-session runtime is covered in tests.
- `KanbanAdapter(hermes_home, board)` reads `task_runs.id` (board-scoped),
  `profile`, and `metadata.worker_session_id`, falling back to `session_id` exactly
  as the historical join does. `profile` is the recorded role, not a guessed alias.
  Identity is board + workflow template when recorded, otherwise board + task id;
  a missing template is not an inferred workflow graph.
- `HermesUsage(hermes_home)` reads only `profiles/*/state.db`, not snapshots or
  backups. It totals `session_model_usage.api_call_count` for the attributed
  sessions across profiles, including auxiliary rows. It never reads the sessions
  rollup. Missing attribution/usage, malformed metadata, invalid counters and
  unreadable/incompatible databases fail explicitly rather than returning zero or
  silently reporting partial cost. A recorded zero is valid.
- Both Hermes readers run in fresh Python processes, with SQLite URI `mode=ro`
  and `query_only`, and import no Hermes code. Paths are explicit; there is no
  credential/config discovery or model call.
- `DiagnosisStore` writes exact UTF-8 JSON bytes under
  `<store>/<sha256(runtime + workflow identity JSON)>/diagnoses/<sha256(bytes)>.json`.
  The record contains schema version 1, observation UUID/time, attribution and
  calls/run. Each diagnosis is a new observation, even if calls are unchanged.
  Exclusive hard-link publication exposes only complete bytes and never replaces
  a version; files are read-only. Loads rederive the digest. External tampering
  is detected, not repaired. This local diagnosis format is **not** the undecided
  workflow-spec serialization format.
- The terminal front door is deliberately a minimal line-oriented TUI: board and
  run-id prompts, followed by role, calls/run and artifact path. It uses the same
  diagnosis entry point, catches errors and cancellation, and makes no decisions
  about plugin packaging.

## Historical evidence and fixture provenance

Read-only inspection of the baseline script and the recorded pilot databases found:

| Field | Value |
|---|---|
| Board | `stillroom-research` |
| Run id | `2` |
| Task id | `t_fb59e5d1` |
| Profile / role | `stillroom-media-analyst` |
| Started at (Unix seconds) | `1789342543` (2026-09-14) |
| Worker session | `20260914_093544_993097` |
| Workflow template | NULL |
| Model / provider | `gpt-5.6-sol` / `openai-codex` |
| Main-loop usage (`task = ''`) | 9 calls |
| `title_generation` usage | 1 call |
| Sessions rollup | 9 calls (not authoritative) |
| **Summed calls/run** | **10** |

This is the sole media-analyst run in the 2026-09-18 baseline (published role row:
1 run, 10.0 calls/run). Source:
`~/Documents/life-os/Business/Stillroom/agent-team/verification/2026-09-18-cost-baseline/`
(`measure_cost_baseline.py`, `cost-baseline.md`). The original join selects the
worker session from run metadata and sums usage rows across profile databases.
The new terminal entry point was also executed against that recorded run and
reported **10**, writing only to a temporary `/tmp/ticket03-artifacts-*` store.

`tests/test_diagnosis.py::make_hermes` is a minimal transcription of those
attribution and call-count rows, not a synthetic claim to historical provenance.
It omits task text, conversations, credentials and unrelated usage fields.
An invented 999-call interactive session is added as a negative control. Tests
create their own SQLite files and never access real Hermes state or the vault.

## Verification

Tracer bullets were run red then green:

1. Historical attribution: failed with missing diagnosis package; then passed.
2. Summed calls and immutable rerun: failed with missing diagnosis entry point;
   then passed with 10 calls and two independently loadable versions.
3. Terminal wiring: failed with missing `__main__`; then displayed 10 and refused
   a store inside the configured Hermes home.
4. Store symlink escape: reproduced an unwanted write outside the store, then
   passed after checking the resolved artifact directory before creation.

Additional seam regressions cover the alternative runtime, missing/invalid
attribution, missing/invalid/zero usage, legacy links, template identity,
unknown runs/missing databases, and tampered artifacts.

```bash
.venv/bin/python -m pytest -q tests/test_diagnosis.py
.venv/bin/python -m mypy agent_lab
AGENT_LAB_JUDGMENT=stub .venv/bin/python -m pytest -q
```

Targeted result: **20 passed**. Regular typechecks report the same **11 inherited
errors in 3 files**, none in diagnosis; no green whole-project typecheck claim.
Final full offline suite: **95 passed, 2 optional live-Jev skips**.

## Standards

Independent worker review of `git diff 02e4f6d...HEAD` at `fcfb06c`:

- **Hard violation, store path protection:** containment alone permitted a
  workflow-directory symlink into a protected Hermes root when the artifact store
  was an ancestor of Hermes. This violated CONTEXT §9.3 / ADR-0002. **Fixed:**
  retain resolved protected roots and check the actual destination before any
  creation/write. The exact regression failed red, then passed. An independent
  follow-up confirmed the finding resolved, with no new actionable issue.
- **Judgement call, possible Primitive Obsession:** the internal fresh-process
  protocol uses `dict[str, Any]` / string operation tags rather than typed request
  models. Malformed manual requests can escape the subprocess's friendly error
  handling. Nonblocking and retained for now: callers construct both request
  variants locally; public return values are validated and subprocess failures
  become `DiagnosisError`. This is not an external-input security claim.

## Spec

Independent parallel worker review found **no confirmed ticket-03 findings**:
no missing/partial requirements, scope creep, or incorrectly implemented ticket
requirements. Historical reproduction was supported by the documented 9+1 fixture;
reviewer did not independently reread the real databases. Other units, breakdowns,
full boundary proof and role/baseline management correctly remain later tickets.

**Review summary:** Standards: 2 initial findings (1 hard violation fixed and
independently verified, 1 nonblocking heuristic retained); Spec: 0 findings.

## Boundaries

Only calls/run ships here. Context/call, tokens/run, cache hit rate, auxiliary
breakdowns and reasoning-token reporting remain ticket 05; role aggregation and
baseline management remain ticket 06. Ticket 04 owns the full read-only boundary
proof. Store checks reject default/configured Hermes roots and resolved path
escapes, but are not a sandbox against concurrent malicious filesystem changes.
Custom API callers must supply their Hermes roots via `protected_roots`; the TUI
does this automatically. Source/installation directories must never be chosen as
artifact stores. SQLite read-only mode is not a claim of forensic immutability of
SQLite-managed WAL/shared-memory bookkeeping. No Hermes source/config/authentication
or application records were edited. Reads across the board and profile databases
are not a cross-database transaction; diagnosing an active run is an observation,
not a promise of its eventual final cost. No snapshot deduplication or legacy
schema migration is attempted.

Ticket 03 remains claimed pending Adam's acceptance; 04–06 are not authorized by
this implementation. No generation, conformance engine or packaging was added.
