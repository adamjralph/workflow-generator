# Current project state

**Authority:** When documents disagree, CURRENT.md wins; contradicting sentences
are stale. The compact status index lives in [state.json](state.json); current HEAD
comes directly from Git when the guard runs, not from tracked status files.
Run `python3 scripts/project_state.py check` at session start; run
`python3 scripts/project_state.py measure` for the mandated-read budget.

**Issue 33:** Context cleanup implemented locally with approved AGENTS.md edit.
Guard and injected-failure checks passed; `python3 scripts/project_state.py measure`
reported 5,812 chars (2026-09-26). Awaiting Adam's acceptance. For publication
status, inspect Git and remote; no HEAD is recorded in tracked status files.

**Release scope:** Expected-outcome verification pillar V1 accepted, not authorized
for implementation; V2–V5 open. Tickets 01–18, 20–31 accepted/published; ticket 19
accepted only for operator-pinned live path (default oldest-draft still untested).
Ticket 32 implemented/pushed, awaiting Adam's acceptance. D3, D4, D5, D7 open.

**Next action:** `python3 scripts/project_state.py check`

Earlier evidence and status preserved in
[CURRENT.history-2026-09-26.md](CURRENT.history-2026-09-26.md) and
[CURRENT.history-through-2026-09-25.md](CURRENT.history-through-2026-09-25.md).
Archives are historical, not part of the fresh read.
