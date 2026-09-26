# 33: Make fresh-session context unambiguous and cheap

**Type:** task
**Status:** draft for Adam's decision, 2026-09-26. Not approved, not started. Blocks
the pillar's implementation slices (V1 accepted 2026-09-26) because every future
slice pays this cost otherwise.
**Blocked by:** nothing technical. Needs Adam's go, and one protected-file approval
(`AGENTS.md`).
**Scope note:** documentation and tooling only. No engine, test or behaviour change.

## Why this exists

Measured on 2026-09-26 in this checkout. A fresh session is told by `HANDOFF.md` to
read five documents before acting:

| File | Lines | Chars |
|---|---|---|
| `AGENTS.md` | 60 | 3,359 |
| `CURRENT.md` | 11 | 2,855 |
| `ROADMAP.md` | 163 | 10,382 |
| `.scratch/workflow-generator/map.md` | 315 | 24,774 |
| `HANDOFF.md` | 66 | 7,391 |
| **Mandated subtotal** | | **49,336 (~13k tokens)** |
| `CONTEXT.md` (README calls it "start here") | 533 | 25,005 |
| **With CONTEXT.md** | | **74,341 (~20k tokens)** |

Outside that read path sit `HANDOFF.history-*.md` + `CURRENT.history-*.md`
(328,356 chars), `docs/*.md` (399,105), `issues/*.md` (191,144).

Volume is the smaller problem. The real defect is **shape**: a fresh agent receives
a reading list, not a state.

### Demonstrated failures, observed this session

1. **Append-only status loses recency.** `issues/19-*.md` is 311 lines of dated
   updates; the correction sits at line 5 and a stale claim at line 293. A
   top-to-bottom reader ends on the wrong paragraph. A fresh agent misreading
   `BUG_REPORT.md` concluded the live provider path was dead-ended, when the bug had
   been fixed on 2026-09-23. That is a real, reproduced error caused by document
   shape — not by carelessness.
2. **Two documents claim "start here".** `README.md` names `CONTEXT.md`;
   `HANDOFF.md` names `AGENTS.md`.
3. **Authority is unmarked.** Nothing states that `CURRENT.md` wins over `README.md`
   when they disagree. They did disagree.
4. **No cheap state check.** An agent cannot verify a belief against reality without
   running the suite.
5. **Stale claims survive in five places at once.** The 2026-09-26 reconciliation
   had to fix the same class of defect in `README.md`, `ROADMAP.md`, `map.md`,
   `BUG_REPORT.md` and `issues/19-*.md` separately.

## What to build

1. **One machine-readable state artifact.** `state.json` (or an equivalent
   front-matter block in one nominated file) holding: accepted tickets, published
   tickets, HEAD SHA, current next action, open decisions. Derived from Git where
   possible so it cannot drift silently. Agents query it; they do not reconstruct it.
2. **One entry file, the only read path.** It lists what to read by topic on demand
   and states explicitly: do not read the `*.history-*.md` archives or the full
   `docs/` set unless a named question requires it. Resolve the README/HANDOFF
   two-start-point conflict; one wins.
3. **A one-line precedence rule.** Written in the entry file and in `AGENTS.md`:
   when documents disagree, the named authority wins, and any contradicting sentence
   is stale by definition.
4. **De-append the ticket files.** Each ticket file gets a current-status header of
   at most 10 lines; dated updates move to a sibling `*.history.md`, which is never
   part of the read path. Never both forms in one file.
5. **Next action as an executable command, not prose.** So a fresh agent runs it
   instead of interpreting it.
6. **A staleness guard.** A scripted check (test or script) that fails when:
   `CURRENT.md`'s recorded HEAD differs from `git rev-parse HEAD`; a ticket marked
   accepted still carries a "still missing" claim that contradicts it; or a
   nominated file contains a known-superseded phrase. This is the missing cheap
   state check.
7. **A repeatable size measurement.** A command that reports the mandated fresh read
   in chars, so the budget becomes a number that can regress, not a vibe.

## Projected result (prototyped 2026-09-26)

A 1,225-char prototype `state.json` (HEAD, accepted/partial/awaiting-acceptance
tickets, release scope, open decisions, next action, authority, observed regression,
do-not-read list) plus `CURRENT.md` prose projects a mandated read of **~4,460 chars**
against today's **49,336**. The ≤6,000-char target is therefore achievable, not
aspirational. The prototype is not committed; it exists to size the change.

## Acceptance criteria

- [ ] A fresh session's mandated read measures **≤ 6,000 chars** via the new command.
- [ ] One entry file is unambiguously the read path; the two-start-point conflict is gone.
- [ ] The precedence rule is stated in the entry file and `AGENTS.md`.
- [ ] Every ticket file in the read path has a ≤10-line current header; history is archived, not deleted.
- [ ] The staleness guard passes on a clean tree and **fails on a deliberately injected stale claim** (prove both directions, not just green).
- [ ] No evidence is deleted; archives are moved and linked, and the move is recorded.
- [ ] `AGENTS.md` changes receive Adam's explicit approval before the write.

## Non-goals

- Not deleting history or evidence. Archives are preserved and linked.
- Not changing engine, tests or runtime behaviour.
- Not touching the private validation roots under `/home/hermes/workflow-validation-scratch/`.
- Not resolving V2–V5 of [the pillar](../docs/outcome-verification-pillar.md), which
  remain open decisions.
- Not committing or pushing anything without a separate scoped approval.

## Open questions for Adam

- O1: `state.json` as a generated artifact, or the front-matter of one nominated file? (Generated cannot drift; front-matter is one less moving part.)
- O2: Which file is the single entry point — the new one, `AGENTS.md`, or `HANDOFF.md`?
- O3: Guard as a pytest test in the suite, or a standalone script run at session start?
- O4: Is `CONTEXT.md` (25,005 chars) in or out of the default read path?
