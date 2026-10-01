# Current project state

**Authority:** When documents disagree, CURRENT.md wins; contradicting sentences
are stale. The compact status index lives in [state.json](state.json); current HEAD
comes directly from Git when the guard runs, not from tracked status files.
Run `python3 scripts/project_state.py check` at session start; run
`python3 scripts/project_state.py measure` for the mandated-read budget.

**Issue 33:** Context cleanup accepted by Adam, with approved AGENTS.md edit.
Guard and injected-failure checks passed; `python3 scripts/project_state.py measure`
reported 5,812 chars (2026-09-26). For publication
status, inspect Git and remote; no HEAD is recorded in tracked status files.

**Release scope:** Expected-outcome verification pillar V1 accepted; only ticket 34
has an implementation go. V2–V5 open. Tickets 01–18, 20–34 accepted; ticket 19
accepted only for operator-pinned live path (default oldest-draft still untested).
Tickets 32–33 are committed;
local `main` matches its `origin/main` tracking ref. D3, D4, D5, D7 open.

**Next action:** `python3 scripts/project_state.py check`

**Latest accepted slice:** [Ticket 34](.scratch/workflow-generator/issues/34-check-declared-workflow-output.md)
implemented locally under Adam’s go: typed JSON file/fields/byte-limit declaration,
actual-file checks and saved run-attributed verdict through both existing drivers.
Passing/failing offline demonstrations, focused tests and full regression pass.
Adam accepted ticket 34 and authorized commit/push. Review findings were addressed by exact
saved-byte checksums and Adam’s approved configurable size limit. No repair, alerts,
browser changes or paid calls. For publication status, inspect Git and remote.
No next implementation slice is authorized.

**Validation boundary:** Focused regression: 202 passed; typing clean (45 files).
Full offline suite: 2,436 passed, 3 expected skips. Current evidence and repeatable
commands: [ticket 34 evidence](docs/outcome-ticket34.md). Earlier results are historical.

Earlier evidence and status preserved in
[CURRENT.history-2026-09-26.md](CURRENT.history-2026-09-26.md) and
[CURRENT.history-through-2026-09-25.md](CURRENT.history-through-2026-09-25.md).
Archives are historical, not part of the fresh read.
