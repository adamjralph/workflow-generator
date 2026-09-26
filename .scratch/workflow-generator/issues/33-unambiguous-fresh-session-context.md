# 33: Make fresh-session context unambiguous and cheap

**Type:** task
**Status:** implemented locally, awaiting Adam's acceptance (2026-09-26). Adam
approved implementation, protected `AGENTS.md` edit, and scoped commit/push.
**Decisions:** tracked `state.json` index; `HANDOFF.md` entry; standalone guard;
`CONTEXT.md` on demand. HEAD is read from Git, not stored in tracked files.
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
   tickets, current next action, open decisions. Read live HEAD from Git at check
   time, not from a tracked snapshot. Agents query the index, not reconstruct it.
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
   tracked status files assert a frozen HEAD rather than reading `git rev-parse HEAD`;
   a ticket marked accepted still carries a contradictory "still missing" claim;
   or a nominated file contains a known-superseded phrase. Git facts are checked
   against Git, not against a self-invalidating recorded SHA.
7. **A repeatable size measurement.** A command that reports the mandated fresh read
   in chars, so the budget becomes a number that can regress, not a vibe.

## Projected result (prototyped 2026-09-26)

A 1,225-char historical prototype `state.json` (HEAD, accepted/partial/awaiting-acceptance
tickets, release scope, open decisions, next action, authority, observed regression,
do-not-read list) plus `CURRENT.md` prose projects a mandated read of **~4,460 chars**
against the **49,336**-char 2026-09-26 baseline. The prototype was not committed;
it sized the change. Current measured entry budget: **5,789 chars**
(`python3 scripts/project_state.py measure`, 2026-09-26), including `AGENTS.md`.

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

## Resolved decisions

- O1: tracked `state.json` indexes status; current HEAD is read directly from Git by the guard, not stored in `state.json` or `CURRENT.md`. Adam approved replacing the impossible recorded-HEAD equality check with this Git-derived observation.
- O2: `HANDOFF.md` is the sole entry file.
- O3: Standalone `python3 scripts/project_state.py check` runs at session start.
- O4: `CONTEXT.md` is outside the default read path.
