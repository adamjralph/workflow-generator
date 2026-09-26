# Current project state

**Authority:** if any other document disagrees with this one, this one wins and the
other sentence is stale. `HANDOFF.md` carries next-session instructions; the
[roadmap](ROADMAP.md) and [delivery map](.scratch/workflow-generator/map.md) order
future work.

**First-stop release scope — accepted by Adam 2026-09-26.** The
[expected-outcome verification pillar](docs/outcome-verification-pillar.md): declare
what each agent must produce, check the observed outcome against that declaration,
try a bounded remedy, alert on failure. Internal-only first stop; LinkedIn is one
acceptance scenario, not the release definition. The standard is **behaves as
declared**, explicitly not "was the work good." Pillar decisions V2–V5 are open and
scope acceptance authorizes no implementation.

**Next up:** [issue 33](.scratch/workflow-generator/issues/33-unambiguous-fresh-session-context.md)
— make fresh-session context unambiguous and cheap. Drafted and approved as a draft;
needs its own implementation go. Today's mandated fresh read is 49,336 chars; the
issue projects ~4,460. It touches `AGENTS.md`, which needs a separate protected-file
approval.

Ticket 32 / bounded Loops in parallel branches was implemented against Adam's frozen contract and **committed/pushed** as `ac27f28ba322dbd18ece9c21a542d61806abba9d` (local and remote `main` read back equal). [Ticket](.scratch/workflow-generator/issues/32-check-bounded-loops-in-parallel-branches.md); [evidence](docs/ticket-32-executor-evidence.md). Final-source validation: 188 focused passed; full offline suite 2,399 passed / 3 optional skips (exit 0); mypy clean in 43 source files; independent Standards/Spec follow-ups reported no blockers. No live provider run. **Adam has not separately accepted ticket 32.** Independently re-verified 2026-09-26: full offline suite 2,399 passed / 3 skipped (exit 0), mypy clean. Ticket 31 / P14 Decision routes is accepted and published at `19985ee300da0b900e1dd1ae780fb120445584d3`; its final-source evidence was 124 focused, 2,367 full passed / 3 skips, mypy clean. [Ticket 31](.scratch/workflow-generator/issues/31-check-decision-routes-in-one-parallel-wave.md); [evidence](docs/ticket-31-executor-evidence.md).

Ticket 30 / the restricted offline P17 Gate path is **accepted and published**. At the last local check, `main` HEAD was `cd7d250d4525a3f4b012eceab9f97ed44e91268c`; inspect Git status and remote anew before any publication claim. The accepted implementation supports a retained exact bundle and committed Gate pause, owner-only local OS-account decision, and fail-closed fresh-process continuation through both checked drivers. It does **not** establish arbitrary mid-step exactly-once side effects, person-level authentication, a Fork Gate, or a live workflow/provider run.

Final-source evidence for ticket 30: 161 focused Gate tests passed; mypy was clean in 43 source files; the full offline suite passed 2,330 tests with 3 skips (exit 0); independent Standards and Spec reviews returned no blockers on the reviewed candidate. See [ticket 30](.scratch/workflow-generator/issues/30-restart-and-fail-closed-gate-continuation.md), [contract](docs/ticket-30-restart.md), and [evidence](docs/ticket-30-executor-evidence.md). Tests were **not rerun** for this documentation archive.

Ticket 29's bounded same-process Gate path and ticket 28's Transform-only parallel wave were also accepted and published; ticket 19 was accepted only for an operator-pinned live Generator→Guardian pair, not default-oldest selection. The [roadmap](ROADMAP.md), [delivery map](.scratch/workflow-generator/map.md), contracts, ADRs, and issue files govern future scope. Acceptance does not itself authorize a new implementation, live run, publication, or push.

For the next session, use [HANDOFF.md](HANDOFF.md). The former full status log is preserved byte-for-byte in [CURRENT.history-through-2026-09-25.md](CURRENT.history-through-2026-09-25.md). It contains superseded checkpoints; do not interpret their old pending instructions as current. Read it only when historical evidence is needed.
