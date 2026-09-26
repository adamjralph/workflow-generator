# Workflow Generator — next-session handoff

## Start here

Read `AGENTS.md`, [CURRENT.md](CURRENT.md), [ROADMAP.md](ROADMAP.md), the [delivery map](.scratch/workflow-generator/map.md) and the relevant issue/contract before acting. Check `git status --short` and HEAD first; this is a shared worktree. Use `graft map` then `graft ask "<specific question>" --source` for code navigation. [Ticket 31 Decision routes](.scratch/workflow-generator/issues/31-check-decision-routes-in-one-parallel-wave.md) is accepted and published. [Ticket 32 bounded Loops](.scratch/workflow-generator/issues/32-check-bounded-loops-in-parallel-branches.md) is implemented, verified and pushed, awaiting Adam's separate acceptance.

## Verified state and boundaries

- **2026-09-26 08:13 AEST read-back:** local `main` HEAD and remote `origin/main` both equal `19985ee300da0b900e1dd1ae780fb120445584d3`. Adam accepted ticket 31 and authorized its five-file scoped commit/push. A plain push first returned 403 because default GitHub identity is `stillroom`; `GH_CONFIG_DIR=/home/hermes/.config/gh-personal` resolves the documented `adamjralph` identity and pushed successfully. Do not change global credentials. Recheck Git state before subsequent work.
- Ticket 31's final-source [evidence](docs/ticket-31-executor-evidence.md): 124 focused passed; mypy 43 files clean; full offline suite 2,367 passed / 3 optional skips (exit 0); independent Standards/Spec review findings corrected. No live model/provider run. Passing conformance is case-scoped, not semantic correctness or purity.
- **2026-09-26 read-back:** ticket 32 [evidence](docs/ticket-32-executor-evidence.md): focused final-source 188 passed; mypy clean in 43 files; independent Standards/Spec follow-ups found no blockers after corrections; full offline suite 2,399 passed / 3 optional skips (exit 0). Adam authorized a scoped commit/push if ready. Local and remote `main` both read back `ac27f28ba322dbd18ece9c21a542d61806abba9d` after the four-file ticket-32 push. No separate acceptance or live call.
- Ticket 30/P17's restricted offline Gate restart was accepted and published in prior work; see [issue 30](.scratch/workflow-generator/issues/30-restart-and-fail-closed-gate-continuation.md), [D2 contract](docs/gate-identity-contract.md), [restart contract](docs/ticket-30-restart.md), and [executor evidence](docs/ticket-30-executor-evidence.md).
- Last final-source ticket-30 validation: focused 161 passed, mypy 43 files clean, full offline suite 2,330 passed / 3 skipped (exit 0); independent Standards/Spec no blockers. No tests or live provider/workflow calls were run for this documentation-only change.
- Preserve two existing **untracked** ticket-28 briefs at `.scratch/workflow-generator/ticket28-correction-brief.md` and `ticket28-executor-brief.md`. This handoff, `CURRENT.md` and `.scratch/workflow-generator/map.md` remain uncommitted, deliberately excluded from the scoped ticket-32 commit; preserve sibling edits. Do not sweep them into a commit, delete them, or reset sibling work. Private validation roots under `/home/hermes/workflow-validation-scratch/` remain outside Git.
- The accepted Gate path is committed-pause-only restart under local OS-account trust. It does not claim arbitrary mid-step exactly-once side effects, person-level auth, a Fork Gate, or a live provider/tool workflow run. A new implementation, independent delegation, live call, acceptance, commit, push, or publication needs its own appropriate decision; documentation is not authorization.

## History and next action

The full previous handoff, unchanged and with root-relative links intact, is [HANDOFF.history-through-2026-09-25.md](HANDOFF.history-through-2026-09-25.md). The former status log is [CURRENT.history-through-2026-09-25.md](CURRENT.history-through-2026-09-25.md). Their old “resume here” directions are historical. Read targeted sections only when tracing a past decision or failure.

**Next action:** ask Adam whether to formally accept ticket 32 after reviewing its [final-source evidence](docs/ticket-32-executor-evidence.md). The scoped code/test/issue/evidence commit is already pushed and read back; do not commit sibling documentation or launch a live call without separate approval. For any rerun use `/home/hermes/.hermes/profiles/astra-pinned/bin/workflow-generator-validation .venv/bin/python -m pytest -q --tb=short`: this session's default `TMPDIR` lies inside `.hermes`, while the wrapper provides a permitted external validation directory.

## Status reconciliation (2026-09-26)

`README.md`, `ROADMAP.md`, `.scratch/workflow-generator/map.md` and issue 19's
readiness line were reconciled to `CURRENT.md` and committed evidence. Before that
pass `README.md` still called ticket 28 "not started" and cited a 1,892-test
baseline; `ROADMAP.md` stopped M2 at Judgment + Loop; the map called ticket 32
"proposed"; issue 19 still said its live smoke and acceptance were missing. Treat
any future claim in those files that contradicts `CURRENT.md` as stale.

**V1 accepted by Adam on 2026-09-26**: the pillar is the first-stop release scope.
Recorded in [README.md](README.md), [ROADMAP.md](ROADMAP.md) and
[HANDOFF.md](HANDOFF.md), which point at
[docs/outcome-verification-pillar.md](docs/outcome-verification-pillar.md). Adam's
framing: verify that a workflow **behaves as declared** — explicitly not that the work
was good. Scope acceptance authorizes no implementation; each slice needs its own go.
V2–V5 remain open.

**Open fork, needs Adam's decision:** the live path is *demonstrated working* in its
bounded operator-pinned form — ticket 19's accepted run completed a real Codex
Generator → independent Vertex Guardian pair with an `Approved` verdict and a
passing offline Check. Two things remain genuinely open:

1. **Default oldest-draft selection has never been live-exercised.** It stays
   fail-visible on invalid inventory, and the oldest eligible file is dated
   2026-09-08. A default-mode live test needs truthful metadata/classification and,
   for sensitive sources, an explicit public-use decision first.
2. **Ticket 19 is not the product finish line.** P18 (Gate between waves), P19
   (regeneration), P21–P25 (role/skill emission and permissions) and P27–P32
   (integrated journey) are still outline rows. Most are blocked on unsettled
   decisions (D3, D4, D5, D7) rather than on code.

Do not repeat the earlier error of treating the provider path as dead-ended: the
Codex `missing_http_content_type` and empty-`output` incompatibilities were
diagnosed and corrected (`docs/codex-protocol-diagnosis.md`,
`docs/codex-compatibility-correction.md`), and the Vertex parser incompatibilities
(`extra_content.google.thought_signature`, `usage.extra_properties`, missing
mandatory review fields) were corrected across operations v3–v5. `BUG_REPORT.md`
retains its pre-correction 2026-09-22 framing; read the correction docs with it.
Live model calls still need their own explicit authorization each time.

## Scope proposal awaiting Adam's decision

**[Issue 33](.scratch/workflow-generator/issues/33-unambiguous-fresh-session-context.md)**
is the drafted cleanup: one machine-readable state artifact, one entry read path, a
stated precedence rule, de-appended ticket files, and a staleness guard that fails on
an injected stale claim. Today's mandated fresh read is **49,336 chars**; the issue
projects ~4,460. Needs Adam's go (and one protected `AGENTS.md` write approval).

[docs/outcome-verification-pillar.md](docs/outcome-verification-pillar.md) names the
project's original intent — verify that a workflow executed *and* that the agents did
what they were expected to do, try a bounded remedy, or at least alert — and proposes
it as the **internal-only first-stop release scope**, with LinkedIn demoted from the
release definition to one acceptance scenario. It records what already exists toward
the pillar (diagnosis, conformance, replay, the `JudgmentSource` boundary), what does
not (any expectation model, any remediation, any alert delivery), the four ticket-19
relaxations Adam named on 2026-09-26, and five decisions (V1–V5) that need his word.
**Not an implementation authorization; no ticket exists yet.** Read it before
scoping any further capability work.
