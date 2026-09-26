<!-- graft:start -->
## Graft — repo context graph

For any task, query the indexed graph in `graft/` before grepping or opening
source. New here? Run `graft map` first. Use literal identifiers in
`graft ask "<question>" --source`; its top node gives file:line spans and a
short crux. Use `--full` if truncated. Open source only at a needed span.
For exhaustive searches use `graft grep "<literal>"` (raw grep only for
unindexed files). For structure use `graft skeleton <file>` or
`graft callers <symbol> [--direction out] [--depth N]`. Browse `graft/INDEX.md`
when useful; scope monorepo queries with `--in <scope>/`. After large code
changes run `graft build` (deterministic; no API key).
<!-- graft:end -->

## Execution and collaboration

Adam coordinates this project with several models (including Astra, GPT-6-Sol and
DeepSeek-4.2-flash). Treat their work as shared project work: inspect the current
working tree and handoff, preserve sibling edits, and advance the next safe,
authorized step instead of stopping merely because another model touched a file.
A changed file is a reason to reread and patch against current content, not to
reset or overwrite it.

Use sensible low-risk assumptions and do routine read-only checks and local
validation without asking. If a consequential decision, ambiguous provenance,
private-source change, provider spend, independent delegation, publication, push,
profile/credential edit or protected write needs approval, ask Adam for that
specific decision. Do not interpret this collaboration preference as blanket
permission to bypass the project's explicit run/evidence guards or acceptance
criteria. Record assumptions and actual results; do not claim a passing run from
an attempted one.

## Status documents: one state, one authority, no append-only status

`HANDOFF.md` is the sole fresh-session entry; run `python3 scripts/project_state.py check`
first, then read `state.json`. `CONTEXT.md` is on-demand, not a default read.
`CURRENT.md` is the **authority**: if documents disagree, `CURRENT.md` wins and
the contradicting sentence is stale. `state.json` indexes status; current HEAD
is read directly from Git, never copied into tracked status files. `ROADMAP.md` and `.scratch/workflow-generator/map.md` order future work;
`README.md` is orientation and must never be the only place a status change is recorded.

A fresh session is told to read a reading list, then reconstruct a state. That is
where it goes wrong: append-only status means recency loses, so a corrected claim at
the top of a file is beaten by a stale one at the bottom. Concretely, `BUG_REPORT.md`
once read as a live blocker after its bug was fixed, and that caused a real
misdiagnosis. Do not add to that.

Rules:

1. **Never put both current status and dated history in one file.** A file carries a
   current header; its update log moves to a sibling `*.history.md`, which is not part
   of the read path.
2. **Update every affected document in the same change**, including `README.md`'s
   Status section and any `**Still missing:**` or readiness line inside the ticket
   file itself. Stale status is worse than missing status, because a fresh session
   acts on it and redoes settled work.
3. **Verify by grep, not by memory.** After changing a status, search for the
   superseded claim (`grep` for the old count, the old status word, the old SHA).
4. **Never state a test count, coverage claim or "next approved implementation" you
   did not observe in this checkout.** Cite the command and the date. Historical
   numbers belong only in dated evidence documents, where they are clearly labelled.
5. **State the next action as a runnable command**, not as prose an agent must
   interpret.
6. **Do not read the `*.history-*.md` archives or the full `docs/` or `issues/` sets
   by default.** Read them only when a named question requires the history.

Scope acceptance, a decision, or a passed review is not implementation authorization.
Each slice needs its own go, and live calls need their own explicit approval.

Leave the ticket-28 briefs (`.scratch/workflow-generator/ticket28-*.md`) untracked and
unmodified, and keep private validation evidence under
`/home/hermes/workflow-validation-scratch/` outside Git.

