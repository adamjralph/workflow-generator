# Workflow Generator — approved direction and remaining roadmap

## Status and authority

**Current reconciled status:** [`CURRENT.md`](CURRENT.md). Initial browser authoring
is delivered (tickets 13–14); tickets 17–18 partially cover role/data milestones;
tickets 20–23 deliver LinkedIn offline plumbing/replay, not live parent completion.
Ticket 13's bookkeeping is closed under Adam's 2026-09-22 triage authorization.
Ticket 19 is accepted for the operator-pinned live path (default-oldest live selection remains untested with invalid inventory); ticket 28 is accepted and pushed for one Transform-only parallel wave. The [D2 Gate identity/continuation contract](docs/gate-identity-contract.md) and [ADR 0012](docs/adr/0012-gate-identity-and-local-operator-continuation.md) are accepted. Adam accepted tickets 29 and 30: the bounded same-process Gate path and committed-pause fresh-process restart complete the restricted offline P17 promise after focused/type/full validation and independent Standards/Spec reviews. Ticket 30's accepted work remains uncommitted and unpushed. P17 does not imply arbitrary side-effect exactly-once execution, person-level authentication, or a live workflow run. See `CURRENT.md` and `HANDOFF.md` for evidence and approval boundaries.
M2–M6 below are capability definitions, not wholly unstarted work or newly authorized scope.

Adam approved the next sequence after ticket 09:

**Prove the smallest complete generation/conformance loop for Transform/Decision
before expanding node support or building the questionnaire.**

This roadmap orders work; it does not authorize every milestone for implementation.
Tickets 01–12 are accepted and closed. M1 is complete for its restricted target;
M2 now includes restricted Intervention Judgment and bounded Loop + Route execution.

**Plan the whole journey; implement in bounded vertical slices.** The
[whole-product delivery map](.scratch/workflow-generator/map.md) connects the remaining
capabilities, proposed ticket breakdown, independent work and decision blockers.
Its P13–P32 identifiers are proposals, not published or approved implementation issues.
Review that map before narrowing the next frontier. Later milestones still need
agreed contracts, test seams and review baselines. No time or percentage-complete
estimate is implied.

Current implemented state and next-session instructions: [HANDOFF.md](HANDOFF.md).
Full proposal: [.scratch/workflow-generator/spec.md](.scratch/workflow-generator/spec.md).
Closed domain decisions: [CONTEXT.md](CONTEXT.md), [ADRs](docs/adr/).

## Completed foundations

| Work | Evidence/status |
|---|---|
| Foundation promotion and shared parallel accounting | Tickets 01–02 accepted |
| Read-only diagnosis, four metrics, role/run reports and measured baselines | Tickets 03–06 accepted |
| Inherited type errors and judgment-validation hardening | Ticket 07 accepted |
| Typed in-memory workflow declarations and structural admission | Ticket 08 accepted |
| Plain reference execution for Transform/Decision + Route | Ticket 09 accepted and closed |
| In-memory graph generation and case-scoped structural/behavioral conformance | Ticket 10 accepted and closed |
| Restricted offline Intervention Judgment + Route execution/conformance | Ticket 11 accepted and closed |
| Bounded Loop + Route execution/conformance | Ticket 12 accepted and closed |

Diagnosis is usable through terminal/plugin commands; this does not mean the
visual workflow generator is complete. The foundation's existing graph business
workflow is not a generated arbitrary-spec artifact.

## M1 — smallest complete generation loop (accepted)

**Authored spec → plain reference → generated graph → conformance report.**

- Keep ticket 09's Transform/Decision + Route target and deterministic binding/state
  contract. Unsupported declarations still fail closed.
- Generate a graph execution artifact from that admitted slice; run it offline.
- Compare the actual candidate artifact's declared structure and observable
  behavior against the authoritative plain reference, not an artifact compared to
  itself or a second execution secretly delegated to the reference driver.
- Demonstrate both conforming execution and deliberate structural/behavioral
  mismatches that fail closed with typed findings.
- Preserve shared accounting/audit mechanics and existing business-driver behavior.

**Done when:** a hand-authored branching example generates, runs and passes the
agreed slice-level checks; altered candidates fail; failure/budget behavior agrees.
This proves the loop for the restricted target, not full-product conformance.

Accepted and closed: [ticket 10](.scratch/workflow-generator/issues/10-generate-and-check-reference-slice.md).
Evidence: [generation/checking contract and review](docs/generation-ticket10.md),
**336 passed, 3 optional skips**, mypy clean; independent review findings resolved.
The artifact is in-memory; paired runs use the same ID in separate fresh logs for
exact event/byte/raw-log-digest comparison. The independently supplied candidate
is checked against the authoritative plain reference. Public test seam and review
baseline `3efdbd096cbdf3385570c3ecd179354c55c3aa84` are approved;
persistent spec serialization remains deferred.

## M2 — expand the executable language and its checks together

Add separately scoped vertical slices for:

- **Accepted:** restricted Intervention Judgment through the existing source boundary;
  conformance uses independent offline sources. Arbitrary vocabularies remain future work.
- **Accepted:** bounded Loop + Route execution and conformance.
- Gate pause/rejection/resume, coordinated with M3's spec/bundle approval identity.
- Forks, joins, reducers, shared step accounting and gates between parallel waves.

Each addition must extend reference execution, graph generation and conformance
checks together. Do not let graph behavior become the implicit specification.

**Done when:** all five node types and declared parallel/resume behavior are
executable and checked, including failure paths and no re-spending on resume.

## M3 — artifact identity, approvals and safe regeneration

- Version generated bundles in the tool's own store/project directory.
- Bind approval to exact spec and bundle digests, re-derived at the gate.
- Changed designs/artifacts cannot inherit approval; rejection stops execution.
- Regenerate marked regions while preserving the user layer/hand-edits.
- Define the replay evidence and artifact lifecycle needed for trustworthy checks.

**Dependency:** D2 now agrees a private internal spec/bundle identity protocol
without settling a public persistent spec format. If implementation requires
reopening the format/community decision, bring it to Adam first.
M2 Gate work and this milestone should be planned together, not claim separate
completion while either half is missing.

## M4 — real workflow inputs, roles, agents and skills

- Read role-registry contracts and check compatible accepts/produces/reviews.
- Link data sources through explicit controlled boundaries.
- Identify required agents and generate SOUL artifacts outside Hermes.
- Reuse existing skills; require explicit human approval before creating missing
  capabilities, with recorded evidence.
- Enforce declared tool permissions and verify denied operations in fresh sessions
  under a separately authorized integration-test plan.

**Done when:** a real example can be assembled from compatible data/role/skill
contracts, with inspectable artifacts and demonstrated permission boundaries.

## M5 — questionnaire and visual front door

- Static multiple-choice questionnaire authors the same typed spec.
- One bounded, user-selected regular-model call checks completeness; not Jev.
- Show the graph, including parallelism, and before/after changes.
- Choose UI or TUI and wire the common core into the intended plugin/internal
  surfaces; keep core tests at the spec seam, with a few surface smoke tests.

**Done when:** a user can design, inspect, generate and check a workflow without
hand-authoring Python declarations. Avoid duplicating core logic in the surface.

## M6 — end-to-end product proof and second target

- Carry diagnosis baselines into the design/build/measurement workflow and report
  observed before/after results without inventing savings.
- Dogfood the generator's own design/build/review flow with declared budgets and
  the four measurement units.
- Add opt-in reviewer selection with a different model and separately surfaced cost.
- Add the Kanban target after pydantic-graph, documenting/rejecting unsupported
  shapes and preserving the Hermes read-only boundary. Artifact emission is not
  permission to activate or write a live board/profile.
- Exercise the complete proposed journey and document remaining operational limits.

**Done when:** the proposed internal workflow-building journey works end to end,
with conformance evidence, approvals, permission checks and measured outcomes.
This does not automatically establish public distribution or production readiness.

## Deferred, not hidden completion tasks

- Internal versus community product decision, naming, distribution and packaging.
- Concrete persistent workflow-spec serialization.
- Non-Hermes runtime targets.
- Gated writes/activation changes inside Hermes.

These remain owned by Adam. Do not add them merely to make a milestone appear
complete. The complete proposal is substantially larger than the current numbered
ticket list; later milestones need refinement and sizing before any delivery estimate.
