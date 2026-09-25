# Workflow Generator — next-session handoff

## Start here

Read `AGENTS.md`, [CURRENT.md](CURRENT.md), [ROADMAP.md](ROADMAP.md), and the relevant issue/contract before acting. Check `git status --short` and HEAD first; this is a shared worktree. Use `graft map` then `graft ask "<specific question>" --source` for code navigation. The next bounded product slice has **not** been chosen or authorized by this archive cleanup; use the [delivery map](.scratch/workflow-generator/map.md) to propose one, and ask Adam when the decision changes scope or approval boundaries.

## Verified state and boundaries

- At this documentation pass, local `main` HEAD was `cd7d250d4525a3f4b012eceab9f97ed44e91268c`. Ticket 30/P17's restricted offline Gate restart was accepted and published in prior work; see [issue 30](.scratch/workflow-generator/issues/30-restart-and-fail-closed-gate-continuation.md), [D2 contract](docs/gate-identity-contract.md), [restart contract](docs/ticket-30-restart.md), and [executor evidence](docs/ticket-30-executor-evidence.md). Current remote state was not rechecked during this archive cleanup.
- Last final-source ticket-30 validation: focused 161 passed, mypy 43 files clean, full offline suite 2,330 passed / 3 skipped (exit 0); independent Standards/Spec no blockers. No tests or live provider/workflow calls were run for this documentation-only change.
- Preserve two existing **untracked** ticket-28 briefs at `.scratch/workflow-generator/ticket28-correction-brief.md` and `ticket28-executor-brief.md`. Do not sweep them into a commit, delete them, or reset sibling work. Private validation roots under `/home/hermes/workflow-validation-scratch/` remain outside Git.
- The accepted Gate path is committed-pause-only restart under local OS-account trust. It does not claim arbitrary mid-step exactly-once side effects, person-level auth, a Fork Gate, or a live provider/tool workflow run. A new implementation, independent delegation, live call, acceptance, commit, push, or publication needs its own appropriate decision; documentation is not authorization.

## History and next action

The full previous handoff, unchanged and with root-relative links intact, is [HANDOFF.history-through-2026-09-25.md](HANDOFF.history-through-2026-09-25.md). The former status log is [CURRENT.history-through-2026-09-25.md](CURRENT.history-through-2026-09-25.md). Their old “resume here” directions are historical. Read targeted sections only when tracing a past decision or failure.

**Next action:** inspect current Git and roadmap status, identify a small proposed next slice with its contract/test seam, and get Adam's decision before launching a new build. Validate whatever is actually changed; do not count historical tests as a new run.
