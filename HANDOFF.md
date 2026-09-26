# Workflow Generator — next-session handoff

## Next action

**Do this first: implement [issue 33](.scratch/workflow-generator/issues/33-unambiguous-fresh-session-context.md)**
— make fresh-session context unambiguous and cheap. The draft is approved; the
implementation is not. It needs (a) Adam's answers to its open questions O1–O4 and
(b) his explicit go. It also touches `AGENTS.md`, which needs a separate
protected-file approval.

Why this before anything else: today's mandated fresh read is **49,336 chars**; issue
33 projects ~4,460. Every later slice pays that cost until it lands.

Verify the baseline before changing anything:

```bash
/home/hermes/.hermes/profiles/astra-pinned/bin/workflow-generator-validation \
  .venv/bin/python -m pytest -q --tb=short
```

A plain `pytest` from a session whose scratch root sits inside Hermes fails the
evidence-directory guard by design. Do not disable the guard. Last observed in this
checkout (2026-09-26): **2,399 passed, 3 skipped, exit 0**; `mypy agent_lab` clean in
43 files.

## Read this, in order — then stop

1. [AGENTS.md](AGENTS.md) — collaboration rules and the status-document rules.
2. [CURRENT.md](CURRENT.md) — **the authority.** If any other document disagrees with
   it, the other sentence is stale.
3. The issue or contract you are actually working on.

Do **not** read `HANDOFF.history-*.md`, `CURRENT.history-*.md`, the full `docs/` set or
the full `issues/` set by default. Read them only when a named question needs the
history. `HANDOFF.history-through-2026-09-25.md` and
`CURRENT.history-through-2026-09-25.md` are archives; their "resume here" directions
are historical.

Use `graft map` then `graft ask "<specific question>" --source` for code navigation.
Check `git status --short` and HEAD before acting — this is a shared worktree.

## Current state (2026-09-26)

- **HEAD `f29d4e7`.** Two commits this session (`fbc4e11` reconciliation + pillar,
  `f29d4e7` AGENTS.md rules) are **local only — not pushed.** No push was authorized.
  Remote `main` is behind at `ac27f28`.
- **Accepted and published:** tickets 01–18, 20–31. Ticket 19 is accepted for its
  bounded **operator-pinned** live path only; default oldest-draft selection has never
  been live-exercised (see below).
- **Implemented, verified, pushed, awaiting Adam's separate acceptance:** ticket 32
  (bounded Loops in parallel branches).
- **First-stop release scope — accepted 2026-09-26 (V1):**
  [the expected-outcome verification pillar](docs/outcome-verification-pillar.md).
  Declare what each agent must produce, check the observed outcome, bounded remedy,
  alert on failure. Internal-only first stop; LinkedIn is one acceptance scenario, not
  the release definition. The standard is **behaves as declared**, explicitly not "was
  the work good." Scope acceptance authorizes no implementation.
- **Open decisions:** pillar V2–V5 (alert destination, remedy bound, first real
  acceptance scenario, ticket-19 contract amendment); issue-33 O1–O4 (state artifact
  form, entry point, guard mechanism, `CONTEXT.md` in or out); standing D3, D4, D5, D7.

## Boundaries — what is not authorized

- No push, no publication, no live provider/model call, no Hermes read-write change,
  no profile or credential edit without Adam's specific approval for that action.
- **The live path is demonstrated working**, so do not treat it as dead-ended. Ticket
  19's accepted run completed a real Codex Generator → independent Vertex Guardian
  pair with an `Approved` verdict and a passing offline Check. The Codex
  `missing_http_content_type` and empty-`output` incompatibilities were diagnosed and
  corrected on 2026-09-23; the Vertex parser incompatibilities
  (`extra_content.google.thought_signature`, `usage.extra_properties`, missing
  mandatory review fields) were corrected across operations v3–v5. See
  [codex-protocol-diagnosis.md](docs/codex-protocol-diagnosis.md) and
  [codex-compatibility-correction.md](docs/codex-compatibility-correction.md).
  `BUG_REPORT.md` now carries a resolved-historical banner; it previously read as a
  live blocker and caused a real misdiagnosis.
- **Default oldest-draft selection remains live-untested.** It stays fail-visible on
  invalid inventory; the oldest eligible file is dated 2026-09-08 and is a personal
  health/rebuild draft, which is why the public-use gate exists. A default-mode live
  test needs truthful metadata and, for sensitive sources, Adam's explicit public-use
  decision.
- **Ticket 19 is not the product finish line.** P18 (Gate between waves), P19
  (regeneration), P21–P25 (role/skill emission and permissions) and P27–P32
  (integrated journey) are still outline rows, mostly blocked on unsettled decisions
  rather than on code.
- **Preserve the two untracked ticket-28 briefs** at
  `.scratch/workflow-generator/ticket28-correction-brief.md` and
  `ticket28-executor-brief.md`. Do not commit, delete, or reset sibling work. Private
  validation roots under `/home/hermes/workflow-validation-scratch/` stay outside Git.
- The accepted Gate path is committed-pause-only restart under local OS-account trust.
  It does not claim arbitrary mid-step exactly-once side effects, person-level auth, a
  Fork Gate, or a live provider/tool workflow run. Passing conformance is case-scoped
  structural/behavioural evidence — not semantic correctness, callable purity or
  production readiness.

## This document is itself overdue for issue 33's treatment

`HANDOFF.md` is the entry point but still mixes current state with dated evidence, which
is the defect issue 33 exists to fix. When issue 33 lands, this file should be reduced
to a current header plus a runnable next action, with the dated detail moved to a
sibling archive. Do not compound the problem by appending to it.
