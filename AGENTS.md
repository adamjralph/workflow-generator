<!-- graft:start -->
## Graft — repo context graph

This repo is indexed in `graft/`: small linked markdown nodes that explain each
system and carry exact file:line spans, kept in sync with the code through git.

For ANY task here — understanding how something works, finding where code lives,
or scoping a change — get context from the graph before grepping or opening
source files. Re-ask freely (it's cheap) and reuse literal identifiers you
already have (symbol, error string, file name) as the query. New to this repo?
Run `graft map` first — a token-budgeted orientation (dir clusters, hubs,
hotspots), no LLM, no key.

- Run `graft ask "<your question>" --source` → ranked nodes with the relevant
  code spans inlined (each hit's ≤8-line crux by default; `--full` for whole
  definitions when the crux isn't enough). Match the tool to the task shape:
  for understanding or editing, the top node IS the answer — cite its
  `covers:` file:line spans and edit straight from `--source`. For
  exhaustive tasks ("every occurrence / every caller of this pattern"), ranked
  results are top-N, not complete — run `graft grep "<literal>"` instead
  (exhaustive over indexed files, grouped by enclosing symbol), falling back
  to raw `grep -rn` only for unindexed files.
- `graft skeleton <file>` → every definition's signature + span, ~10× cheaper
  than reading the file; use it to skim an API surface.
- `graft callers <symbol>` gives precomputed, exact edges — who calls this.
  Add `--direction out` for what it calls, or `--depth N` to walk
  transitively for the full blast radius. For structural questions, skip
  ranking and use this directly.
- Or browse: `graft/INDEX.md` lists every node; follow the links.
- Monorepos and folders of multiple repos rank fairly across sub-projects —
  hits carry `[scope/]` labels naming which one they're from. Narrow with
  `graft ask "<task>" --in <scope>/` once you know where you're working.

If a returned span is truncated ("+N more lines"), open the file at that exact
range before finalizing. Only open source files when a node genuinely lacks a
needed detail, and then at the exact file:line the node points to — never
re-read whole files.

After big code changes, refresh the graph with `graft build` (deterministic,
no API key, $0).
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

`CURRENT.md` is the **authority**. If any other document disagrees with it, `CURRENT.md`
wins and the other sentence is stale — that is the whole rule, and it is deliberately
mechanical so a fresh session does not have to adjudicate. `HANDOFF.md` carries
next-session instructions only; `ROADMAP.md` and `.scratch/workflow-generator/map.md`
order future work; `README.md` is orientation and must never be the only place a
status change is recorded.

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

