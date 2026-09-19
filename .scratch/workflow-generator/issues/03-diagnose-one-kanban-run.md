# 03: Diagnose one Kanban run, end to end

**What to build:** An operator can point the tool at a single Kanban run and see its cost in **calls/run**. A runtime-neutral run-attribution adapter (Kanban first) reads the link from the run to the session usage it caused; the measurement is stored as an immutable, digest-addressed diagnosis record; a minimal TUI runs the diagnosis and shows the figure. This is the first complete vertical path: Hermes data → adapter → record → artifact store → surface.

**Blocked by:** 02.

**Source:** `spec.md` → "Diagnosis"; `CONTEXT.md` §9.1, §10.5; ADR-0002, ADR-0009.

**Status:** resolved

- [x] Given a Kanban run id, the tool reports that run's calls/run, using the summed per-usage rows — never the `api_call_count` rollup.
- [x] The Kanban adapter implements the runtime-neutral contract `run_id → session ids, role, workflow identity`, with no Kanban assumption leaking into the measurement logic.
- [x] For a run present in the 2026-09-18 baseline, the adapter reproduces that run's calls figure from the existing join.
- [x] The diagnosis record is written to the artifact store as an immutable, digest-addressed version; re-running creates a new version rather than overwriting.
- [x] A minimal TUI runs the diagnosis and displays the calls/run figure.

## Answer

Accepted and closed at Adam's explicit approval. Implementation: `fcfb06c`;
review fix and final verification: `39a2bd2`.
Final suite: **95 passed, 2 optional live-Jev skips**; the 11 inherited mypy
errors remain unchanged.
See `docs/diagnosis-ticket03.md` for the adapter/store contracts, historical
10-call run and offline fixture provenance, red/green evidence, verification,
and review. Test seams and review baseline `02e4f6d` were confirmed by Adam.
Tickets 04–06 remain out of scope.
