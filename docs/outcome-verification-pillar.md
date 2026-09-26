# The expected-outcome verification pillar

**Status:** **V1 accepted by Adam on 2026-09-26** — this is the first-stop release
scope. V2–V5 remain open (see the decisions table). Acceptance of scope is not
authorization to implement: no ticket is created by this document, and each
implementation slice still needs its own go. Adam's framing: "behaves as declared,"
explicitly not "was the work good."

## Why this document exists

The project's original intent, in Adam's words (2026-09-26):

> An internal checker that could verify whether a workflow had executed and whether
> the agents had done what they were expected to do. If they hadn't done it, it
> could get them to do it or at least alert.

That intent was never written as a ticket or a milestone. The build instead grew a
spec engine, two independent drivers, a conformance checker, parallel waves, loops,
gates and a browser front door. Those are real and tested, but they answer a
different question. This document names the missing pillar, records what already
exists toward it, and proposes it as the first internal-only release scope.

## The four questions, and what currently answers them

| Adam's intent | Current answer | Status |
|---|---|---|
| "whether a workflow had executed" | Diagnosis reads run attribution from the Kanban DB; conformance checks an execution against the plain reference; offline Check replays a recorded pair | **Substantially built** |
| "whether the agents had done what they were expected to do" | Nothing. Conformance compares two executions of the *same spec* to each other. That is self-consistency, not compliance with a declared expectation. Diagnosis measures *cost*, not *outcome* | **Missing** |
| "get them to do it" | Nothing, deliberately. The engine has no retries, no fallbacks, no re-dispatch, no repair | **Missing by design** |
| "or at least alert" | Only in-run terminal states (`NEEDS_REVIEW`, `FAILED_VALIDATION`, `FAILED_BUDGET`). Nothing is ever delivered to Adam; there is no notification path in the codebase | **Missing** |

The two missing halves are the pillar. Everything else is scaffolding that makes the
pillar affordable to build: we already have typed state, budgets, per-role
attribution, durable evidence, replay, and a second independent driver to check the
verifier itself.

## The seed that already exists

`agent_lab/judgment.py` implements a `JudgmentSource` protocol with three
interchangeable implementations — `JevSource` (live), `RecordedSource` (offline
byte-identical replay), `StubSource` (tests) — all returning one validated `Judgment`
(typed choice + confidence). Invalid output raises and becomes a recorded
`FAILED_VALIDATION`.

That is structurally exactly "ask a model to assess something and return a typed
verdict, replayably." Its current limits are scope, not architecture:

- the executable vocabulary is restricted to three `Intervention` values;
- it is not wired to any declaration of what an agent was *supposed* to produce;
- nothing consumes its verdict to remediate or to notify.

CONTEXT §2.5 already decided that judgment belongs *inside* the finished workflow and
that agents talk to our Python, not to the model directly. The pillar is the
completion of that decision, not a departure from it.

## Proposed pillar: declared expectations, checked outcomes

**One sentence:** a workflow declares what each agent or step must produce; after
execution the system checks the observed outcome against that declaration, tries a
bounded repair when it can, and tells Adam when it cannot.

Five components, each independently ticketable:

1. **Expectation declaration.** Each checked step carries a typed, inspectable
   statement of what it must produce (required artifact, required fields, allowed
   values, or an explicit judgment criterion). Declared in the spec, bound like every
   other spec element, and visible before the run. No prose-only expectations.
2. **Observed outcome.** What actually happened. Mostly assembled from what exists:
   run log, terminal state, produced artifacts, per-role attribution.
3. **Verdict.** Pass / fail per declaration, with the specific unmet expectation
   named. Built on the existing `JudgmentSource` boundary so it is replayable and
   testable offline; deterministic checks are plain code, model judgment only where a
   criterion genuinely needs judgment.
4. **Bounded remedy.** On failure, one bounded attempt to get the agent to complete
   the work — the failure and the unmet expectation attached to the redispatch, the
   attempt charged against the run budget, no silent loop, no unbounded retry. After
   the bound, stop and escalate. This matches Adam's standing preference for
   deterministic routing over open-ended model handoffs and for agents doing work
   directly rather than shuffling tickets.
5. **Alert.** When remedy fails or does not apply, the failure reaches Adam outside
   the run: what was expected, what happened, what was tried, what is needed. The
   delivery channel is an open decision (see below).

### What this pillar explicitly does not claim

- It does not prove semantic correctness of the work, only compliance with a declared
  expectation. A badly written expectation passes a bad run.
- It does not make live model calls part of the default test suite.
- It does not write into Hermes. Read-only remains the boundary.
- It does not establish "the agent did the right thing" in general — only "the
  declared outcome was or was not met."

## Proposed first-stop release: internal only

Adam's direction (2026-09-26): if an internal-only release is buildable, that is an
acceptable first stop. This is the closeout assessment's recommendation
(`docs/closeout-assessment-2026-09-22.md`) with LinkedIn demoted from the release
definition to one acceptance scenario.

**In scope for the first stop:**

- The pillar above, end to end, on a fixture-backed workflow and at least one real
  workflow.
- The existing engine: typed spec, two drivers, conformance, bounded loops, parallel
  waves, restricted offline Gate.
- Read-only diagnosis with before/after measurement, carried into the generated run
  so before/after is attributable rather than asserted.
- The existing browser designer as the authoring surface for the supported subset.
- Offline replay of every acceptance scenario.

**Out of scope for the first stop, explicitly deferred:** packaging, naming, public
or community distribution, non-Hermes runtime targets, persistent public spec format,
Hermes writes, role/skill emission (P23–P24) and permission proof (P25). Deferring
any of these is Adam's call, not a silent omission.

**Acceptance is a demonstrated journey, not a ticket count:** declare expectations →
run → observed outcome checked → one deliberate unmet expectation triggers a bounded
remedy → a second, unrepairable one raises a real alert → before/after measurement
attributed → full offline regression, typing, browser checks and independent review.

## Relaxations Adam named on 2026-09-26

Recorded because ticket 19's contract text still carries the old constraints:

1. **Call budget.** The two-call ceiling and no-retry rule apply to the ticket-19
   proof. Adam's direction: use as many calls as the work needs, within sensible
   limits. Remediation in the pillar needs its own call budget, which must be
   declared and charged, not unbounded.
2. **Source immutability.** Sources stay read-only as a default, but for building and
   testing Adam is willing to relax it, on the basis that nothing important is lost
   and nothing is published.
3. **Selection rule.** Oldest-eligible-by-`date_created` is a product rule for real
   runs, not a constraint on building or testing. The operator pin should not be
   hard-coded.
4. **Automatic path is testable.** Verified from the live draft folder on 2026-09-26:
   18 Markdown files, 10 with `date_created`, **8 without**; oldest dated is
   `20-years-to-get-here-first-post.md` (2026-09-08). The automatic path is
   **data-blocked, not code-blocked**: the approved rule fails visible on missing
   metadata rather than guessing. Either add truthful dates or exercise the automatic
   path against a fixture folder, which is already an approved test seam.
   Note the honest consequence: the true automatic path's first target is Adam's
   hospital-rebuild personal draft, which is why the public-use gate exists.

Ticket 19's execution contract needs an explicit amendment recording these, so the
next session does not read the old limits as current.

## Decisions this proposal needs from Adam

| # | Decision | Why it blocks |
|---|---|---|
| V1 | Accept the pillar as the first-stop release scope | **Accepted 2026-09-26.** Recorded in README/ROADMAP/HANDOFF; each implementation slice still needs its own go |
| V2 | Where an alert is delivered (file under a project root, a report the browser shows, or a message through a channel outside Hermes) | The codebase has no notification path; this is a new boundary and Adam owns it |
| V3 | Remediation bound and budget: how many repair attempts, charged how | Prevents open-ended spend and unbounded loops |
| V4 | Whether the first real acceptance scenario is the LinkedIn workflow or a different one | Determines whether live cost is needed at all for the first stop |
| V5 | Amend ticket 19's contract with the relaxations above | Stale contract text otherwise misleads the next session |

Existing parked decisions (D3 Judgment vocabulary, D4 role composition, D5 permission
proof, D7 Kanban shape) remain parked and are not needed for the first stop.

## Relationship to the current roadmap

This pillar sits where M6's "dogfood and prove the journey" meets M2's remaining
runtime work, but it is *not* a claim that M2 is complete. Gate-between-waves (P18)
and regeneration (P19) stay outline work. The pillar can be built first because it
consumes the engine that already exists rather than extending it: expectations,
verdicts, bounded remedy and alert delivery need no new node type, no new driver and
no live call to be tested.
