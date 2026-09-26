# Workflow Generator — entry point

Run `python3 scripts/project_state.py check` before trusting project status. If it
fails, report the mismatch rather than trusting status claims. Read
[state.json](state.json), then consult [CURRENT.md](CURRENT.md)
only for status detail needed by your task. When documents disagree, CURRENT.md
wins; contradicting sentences are stale.

Next action: `python3 scripts/project_state.py check`

Use [AGENTS.md](AGENTS.md) for rules. Read issues/contracts for named work only.
`CONTEXT.md`, ROADMAP, delivery map, full docs/issues sets, and `*.history-*.md`
archives are on demand. Earlier handoff:
[HANDOFF.history-2026-09-26.md](HANDOFF.history-2026-09-26.md).

No commit, push, live call, publication, profile/credential or protected-source
write without its own approval. Preserve both untracked ticket-28 briefs and keep
private validation evidence outside Git.
