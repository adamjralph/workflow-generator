# 03: Diagnose one Kanban run, end to end

**What to build:** An operator can point the tool at a single Kanban run and see its cost in **calls/run**. A runtime-neutral run-attribution adapter (Kanban first) reads the link from the run to the session usage it caused; the measurement is stored as an immutable, digest-addressed diagnosis record; a minimal TUI runs the diagnosis and shows the figure. This is the first complete vertical path: Hermes data → adapter → record → artifact store → surface.

**Blocked by:** 02.

**Source:** `spec.md` → "Diagnosis"; `CONTEXT.md` §9.1, §10.5; ADR-0002, ADR-0009.

**Status:** ready-for-agent

- [ ] Given a Kanban run id, the tool reports that run's calls/run, using the summed per-usage rows — never the `api_call_count` rollup.
- [ ] The Kanban adapter implements the runtime-neutral contract `run_id → session ids, role, workflow identity`, with no Kanban assumption leaking into the measurement logic.
- [ ] For a run present in the 2026-09-18 baseline, the adapter reproduces that run's calls figure from the existing join.
- [ ] The diagnosis record is written to the artifact store as an immutable, digest-addressed version; re-running creates a new version rather than overwriting.
- [ ] A minimal TUI runs the diagnosis and displays the calls/run figure.
