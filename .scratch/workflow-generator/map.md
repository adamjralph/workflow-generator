# Workflow Generator — whole-product delivery map

## Notes: authority and destination

Adam requested a whole-product dependency map and proposed ticket breakdown after
accepting ticket 12. Plan broadly; implement in bounded, independently verifiable
vertical slices. A small implementation slice is not a small planning horizon.

This map is a **proposal for discussion**, not authorization to implement. P13–P32
are provisional planning identifiers, not issue numbers. Current reconciled status
is in [CURRENT.md](../../CURRENT.md). Issues 01–19 and 20–27 are accepted/closed
(19 for the operator-pinned live path; default oldest remains untested); 28 is
ready-for-agent and unimplemented. P26's initial scope was delivered
as [ticket 13](issues/13-build-browser-workflow-designer.md) and extended in ticket 14.
Ticket 13's closure was reconciled under Adam's 2026-09-22 triage authorization.
Later outlines may split after contract design; this is not a delivery estimate.

**Historical first checkpoint (delivered):** Adam chose the visual designer: multiple-choice
answers → inspect a graph → generate and check an already-supported workflow.
**Selected first surface:** browser UI, not TUI. This decision and the initial
P26 contract are settled; do not reopen them as a new implementation frontier.
Adam also approved the initial Transform/Decision + Route scope: safe prebound
operations, answer-based editing, real offline generation/checking, no drag-and-drop
or persistent spec format. Ticket 13 records the approved scope and demo contract;
it is delivered. The current implementation frontier is ticket 28; D2 lifecycle
contract drafting is also authorized, but its substantive semantics remain open.

Authoritative records: [CONTEXT](../../CONTEXT.md), [ADRs](../../docs/adr/),
[roadmap](../../ROADMAP.md), [handoff](../../HANDOFF.md). The historical
[product spec](spec.md) supplies user stories, but its stale status, introduction and
out-of-scope wording do not override those decisions.

### Destination: one complete user journey

1. Diagnose an existing workflow and retain its measured baseline.
2. Author a typed spec through a questionnaire; inspect the graph and proposed changes.
3. Bind compatible roles, data and skills through controlled boundaries.
4. Generate an inspectable runnable artifact; check it against the independent plain reference.
5. Approve the exact spec/bundle pair; execute, pause and resume without repeating completed work.
6. Modify and regenerate without losing hand-edits or inheriting stale approval.
7. Compare attributable before/after measurements, including auxiliary/review and reasoning usage.

The design-only front door is useful before the entire journey exists. The core is
still the spec plus conformance, not the surface. Conformance is case-scoped structural
and behavioral evidence, not semantic correctness, guaranteed savings or production readiness.

## Decisions-so-far: completed capability

**D1 is settled.** Adam accepted the parallel-wave contract and
[ADR 0011](../../docs/adr/0011-parallel-waves-are-declared-order-deterministic.md) as
drafted on 2026-09-22 and selected P13 as the next implementation over the
then-stale `ready-for-agent` browser-designer ticket 13 (now closed):
[ticket 28](issues/28-execute-and-check-one-parallel-wave.md). The contract is
authoritative for wave concurrency, budget admission, reducer/join cost, failure
selection and evidence semantics. Its §10 records the two items handed forward: P14's
loop multiplier and the `wave_concurrency` cap value inside the accepted 1-16 range.

Adam then approved the remaining decision items ("I'll accept A2 through B7",
2026-09-22): the `wave_concurrency` values are fixed (`min(branch_count, 4)` default,
16 maximum, range 1-16), P14's wave worst case counts `max_iterations + 1` visits per
`Loop` node, drafting the D2 identity/approval lifecycle contract is authorized,
the offline transport/header-root-cause thread is closed without a lower-level
transport or evidence-boundary design, and parent ticket 19's readiness decisions 1
and 4 are approved (fail-visible ambiguous/invalid metadata, a missing usable
`date_created` blocks selection, ties by exact filename ascending, the six proposed
public test seams and baseline `35b9a5d7ac8784c062d25ec91f367e6c6d9ffb93`). D3, D4, D5
and D7 remain parked.

Latest acceptance: **ticket 27 is accepted and closed** by Adam ("accept").
Versioned secret-safe first-header-section shape observations now survive Codex/
Vertex adapter failures and durable exchanges/receipts without additional reads or
changes to validation, limits, request identity or retries.
[evidence](../../docs/designer-ticket27.md),
[ticket](issues/27-observe-rejected-header-shape.md).
Final offline suite: 1,892 passed, 3 expected skips; mypy 35 files clean.
Independent Standards: 0 violations, 1 optional readability note; Spec: 0 blocking
deviations. Root cause remains unresolved. Parent 19 stays open.
Adam subsequently approved one Generator-only observation at
`/home/hermes/workflow-evidence/live-smoke-05`. It failed at `0080738` with
`missing_http_content_type`, HTTP 200, after about 1.11 seconds. Diagnostics:
2,651 first-section bytes, 35 field lines, Transfer-Encoding present and
Content-Type/Content-Length/Content-Encoding absent. Exact provider payload was
unchanged from smoke 04. One reserved attempt, no copy/Guardian/Check, unknown
usage. See private `SMOKE.md`. All five live permissions are consumed; no further
live attempt is authorized. The response was not headerless, but its author and
body remain unknown. Preserve all stores and guards.

Previous acceptance: **ticket 26 is accepted and closed** by Adam ("accept").
Codex and Vertex now compare expected media types case-insensitively and distinguish
missing/empty content-type fields with fixed diagnostics. Parameter policy and
historical receipts/replay remain unchanged; [evidence](../../docs/designer-ticket26.md).
Final offline suite: 1,836 passed, 3 expected skips; mypy 35 files clean.
Independent Standards: 0 violations, 1 optional duplication note; Spec: 0 findings.
No live calls or real credential reads occurred. This does not confirm the cause
of any prior smoke failure or authorize another observation. Parent 19 remains open.
Adam subsequently authorized one fresh smoke at
`/home/hermes/workflow-evidence/live-smoke-04`; it failed at Generator with
`missing_http_content_type`, HTTP 200, after about 1.29 seconds. One reserved
attempt, no copy/Guardian/Check, usage unknown. Authorization is consumed. See
private `SMOKE.md`; all four stores and guards must remain unchanged. Any further
live observation or offline implementation scope needs separate agreement.

Previous acceptance: **ticket 25 is accepted and closed** by Adam ("1. Accept").
It adds five secret-safe header-rule diagnostic codes without changing acceptance
policy; [evidence](../../docs/designer-ticket25.md). Final offline suite: 1,727
passed, 3 expected skips; mypy 35 files clean. Implementation and acceptance:
`1e5e8e8`. Adam separately authorized one fresh no-retry smoke at
`/home/hermes/workflow-evidence/live-smoke-03`. It failed at Generator with
`unsupported_http_content_type`, HTTP 200 (one attempt, no Guardian, usage unknown).
The authorization is consumed; see private `SMOKE.md`. Missing versus unexpected
content type and the exact value remain unknown. The subsequent offline investigation
and compatibility correction are delivered in accepted ticket 26. Parent 19 remains open.

Previous acceptance: **ticket 24 is accepted and closed** by Adam ("accept"). It hardens
provider HTTP headers/framing and sanitized diagnostics;
[latest evidence](../../docs/designer-ticket24.md). Final recorded suite: 1,654 passed,
3 expected skips, including real Chromium; mypy 35 files clean. Tickets 20–23 remain
accepted and deliver capture, Generator, independent Guardian and offline Check.
Two separately authorized live smokes captured successfully but stopped at Generator.
Smoke 01 returned `invalid_response`; smoke 02 at `31d408b` returned
`invalid_http_headers` with HTTP 200. Neither exact cause is confirmed. No retries
occurred. Private second-smoke evidence: `/home/hermes/workflow-evidence/live-smoke-02/SMOKE.md`.
The recommended secret-safe header-rule diagnostics are now delivered in ticket 25.
The third smoke authorization is separate and does not authorize further attempts.
Parent 19 remains open.
Older planning-frontier statements below are historical; published ticket numbers
are distinct from outline P-identifiers.

| Accepted work | Evidence | Important limit |
|---|---|---|
| Foundation and shared accounting | Tickets 01–02 | Not a general generated parallel engine |
| Read-only diagnosis, four units, reports/baselines | Tickets 03–07 | No inference of a spec from logs; no Hermes activation authority |
| Typed spec admission | Ticket 08 | Admission of five node types/Fork is not execution |
| Plain reference and generated graph conformance | Tickets 09–10 | In-memory artifact, caller bindings, supplied-case evidence |
| Offline Judgment through both drivers/checker | Ticket 11 | Restricted Intervention vocabulary |
| Bounded Loop through both drivers/checker | Ticket 12 | Route-only execution; no Gate/Fork/resume |

Current generation evidence: 423 offline tests passed, 3 optional skips; mypy clean
in 19 source files, as recorded at ticket 12. These are historical results, not a new
verification run. See [Loop evidence](../../docs/loop-ticket12.md).

## Proposed delivery graph

Dependencies below are required delivered capabilities, not suggested chronological
order. Completed foundations are omitted from blocking columns. Decision gates D1–D7
are defined under Fog. Multiple unblocked rows can be planned together; shared code
may still require coordination. Passing a slice does not authorize arbitrary combinations.

| ID | Proposed ticket / independently verifiable delivery | Blocked by | Readiness |
|---|---|---|---|
| P13 | One Transform-only Fork/join wave: authored spec → plain/graph execution → reducer → exact conformance evidence | D1 settled 2026-09-22 | [Ticket 28](issues/28-execute-and-check-one-parallel-wave.md) — ready-for-agent |
| P14 | Decision routes and bounded Loops within one wave's branches, including uneven branch progress and failures, checked through both drivers | P13; D1 counter extension settled 2026-09-22 (`max_iterations + 1`) | Outline; split if too large |
| P15 | Restricted offline Judgment in parallel branches with isolated replay and full input/judgment evidence | P13; replay ownership contract | Outline |
| P16 | Two sequential parallel waves with explicit joins, fresh branch state and one run-wide budget, checked end to end | P13 | Outline |
| P17 | Route-only Gate: version an executable spec/bundle pair in the artifact store, pause, approve/reject and resume through both drivers and conformance | D2 (contract drafting approved 2026-09-22) | Near-term design draft; likely sizing pressure |
| P18 | Gate between parallel waves: approved continuation executes only the remaining wave with preserved budget, state and evidence | P16, P17 | Outline |
| P19 | Regenerate an executable artifact into a new immutable version, preserve its user layer, re-check it and refuse old approval | P17; marker/conflict contract | Outline |
| P20 | A caller-declared Judgment vocabulary executes and replays through reference, graph and checking; invalid options fail closed | D3 | Independent design frontier |
| P21 | Select compatible role-registry contracts for one authored workflow, run fixture-backed bindings and reject incompatible compositions through the common spec seam | D4 for broader role/agent/skill scope | Bounded registry-derived fixture composition delivered in ticket 17; reuse it, do not rebuild |
| P22 | Bind one controlled read-only data source to a role-bound workflow; replay recorded inputs and verify both drivers' evidence | Broader compositions need separate cases | Bounded source capture/replay delivered in ticket 18 |
| P23 | Emit one runnable role/agent bundle with SOUL and reused skills outside Hermes; inspect and check that exact version | P17, P21; skill matching contract | Outline |
| P24 | For one unmatched capability, explicitly approve and audit new-skill creation, then emit/check a new role bundle | P23; creation approval contract | Outline |
| P25 | Enforce one role's declared tool permissions and prove a denied operation fails in a fresh session | P23, D5 | Authorization-blocked outline |
| P26 | Static multiple-choice authoring → typed spec → visual graph → generate/check for the accepted Route subset | D6 settled | Initial scope delivered in tickets 13–14; expanded parallel/Gate authoring remains P27 |
| P27 | Edit/inspect a parallel and gated design, show before/after structure, generate/check and present approval/continuation evidence | P18, P26 | Outline |
| P28 | One bounded, user-selected regular-model completeness check on questionnaire output, with visible failures and usage | P26; model budget/output contract | Outline; offline first |
| P29 | A measured internal dogfood workflow links an existing baseline to authored design, generated execution and attributable before/after results | P17, P22; generated-run attribution contract | Outline |
| P30 | Opt-in distinct-model review of a generated version; expose review findings and its separately attributed cost | P17; reviewer identity/usage contract | Outline; offline first |
| P31 | Emit and check one supported Kanban workflow outside Hermes; reject unsupported shapes rather than flattening them | P17, D7 | Outline |
| P32 | Demonstrate the selected internal product journey through the front door: diagnose, compose, check, approve, run, regenerate and measure | P19, P24, P25, P27, P28, P29 | Integration outline; decompose into scenarios |

P20 is not a blocker for P15: parallel replay can first use the accepted restricted
vocabulary. P14 and P15 do not automatically establish Judgment-inside-Loop parallel
composition. P16 does not establish nesting. P18 proves between-wave Gates, not
arbitrary Gates inside concurrent branches. Define supported composition tests before
claiming M2 complete; add bounded follow-on tickets where necessary.

P26 need not wait for all runtime features: the design layer can expose unsupported
shapes for inspection only, clearly distinguishing admission from runnable support.
P29 can initially be core-driven, without waiting for the surface. P30 is optional,
not a blocker for the default product journey. P31 is the second-target milestone,
not a blocker for the first-runtime product proof. P32 does not claim either of them.

### Demonstrable checkpoints

- **Checked parallel kernel:** P13, then P14–P16; supported combinations explicitly listed.
- **Approved executable lifecycle:** P17–P19; Gate and exact artifact identity delivered together.
- **Design-only front door:** P26, independently useful on the existing target.
- **Real workflow composition:** P21–P25; runtime permissions proved, not inferred from SOUL.
- **Internal product proof:** P27–P29 and P32 connect the capabilities into one observed journey.
- **Extensions:** P20, P30 and P31 add vocabulary, optional review and a second target respectively.

These are capability checkpoints, not claims that every milestone is fully specified
or that all tickets fit one context window already.

## Near-term frontier: proposed contracts, not settled decisions

### P13 — one complete parallel wave

**Demo:** A caller authors a Fork with two or more single-Transform branches and one
join; the generated graph overlaps branch work, combines all results exactly once,
and passes conformance against an independently executing plain reference.

**Proposed boundary:** One wave; each branch receives a detached copy of the same
fork-entry state. A caller-bound deterministic reducer receives successful results
in declared branch order and produces validated retained state. The join's relationship
to its declared Transform must be explicit: no hidden second invocation or free work.
No nested Forks, branch Decision/Loop/Judgment, Gate or resume in this first slice.

**Required acceptance evidence:**
- Hand-authored expected branch outputs, reducer result and spend, not driver agreement alone.
- Barrier-based overlap proof for actual graph work, without timing-only benchmarks.
- No shared-state lost updates; branch/reducer input mutations cannot change caller state.
- Missing/invalid bindings and unsupported or unreachable shapes rejected before work.
- Short/exact budgets, multiple branch failures, invalid reducer output and audit I/O failure.
- Altered branch order, join/reducer configuration and candidate behavior cannot pass silently.
- Exact persisted evidence agreement under an approved deterministic scheduling contract.

**Settled (D1, approved 2026-09-22):** thread-dispatch concurrency bounded by a
run-level `wave_concurrency` (default `min(branch_count, 4)`, maximum 16, range 1-16);
one-step reservation granularity with static whole-wave admission
(`sum(worst(branch)) + 1`, refused before any work); one reducer invocation from the
join step, charged one step on success and failure; complete-all-then-select with no
sibling cancellation and first-declared-failure selection; a canonical projection as
the compared artefact with raw completion order recorded as non-normative. See
[the contract](../../docs/parallel-wave-contract.md) and
[ADR 0011](../../docs/adr/0011-parallel-waves-are-declared-order-deterministic.md).
The earlier suggestions to reserve an entire wave and buffer events were proposals,
not decisions; buffering still may not weaken audit-failure stopping or introduce an
unacknowledged durability guarantee.

**Public seam:** authored spec + bindings/reducer + independent candidate + typed cases
→ report and real logs. Keep independent driver control flow and inspect the actual
candidate. No broad prefactor is assumed. Agree a review baseline before publishing.

### P17 — Gate and exact executable identity together

**Demo:** Author and emit a minimal Route workflow to a caller-named artifact store;
run to a Gate, record a human rejection or approval of the re-derived exact spec/bundle
pair, and continue only the approved version. Both drivers/checker reproduce the sequence
without re-running completed work or re-spending its budget.

**Required acceptance evidence:** Changed spec, changed executable bundle/bindings,
wrong-run or wrong-Gate approval, forged continuation, rejection, repeated resume,
missing/corrupt evidence and audit failure all fail closed. Persisted evidence must
show what was approved and what executed. No caller-supplied digest string is accepted
as proof of identity. Independent offline approval inputs constrain each driver.

**Still blocks readiness (D2):** Define reproducible identity for the current in-memory
artifact and trusted Python bindings, immutable executable representation, run/Gate
approval scope, continuation integrity and process-restart guarantees. Existing business
approval binds run/draft, not this pair. Do not claim Gate completion using that shortcut.

A private digest representation must be explicitly distinguished from a public persistent
spec format. If executable identity requires settling the deferred format/community
question, Adam must reopen it. If this complete slice is too large, first prototype the
identity/continuation contract, then re-slice complete observable behavior; do not publish
an identity-only layer ticket and imply it delivers Gate support.

### Other independent planning work

P20 still needs a bounded non-Intervention vocabulary contract. P21 and P26 have
delivered bounded role/surface scenarios (tickets 17 and 13–14); reuse them and scope
only their remaining generalization/integration gaps. Triage authorizes preparation,
not a claim that D2 identity or D5 permission semantics are settled.

## Fog: decisions, ownership and authorization

| Gate | Decision needed | Owner / proposed next action |
|---|---|---|
| D1 | Parallel reducer, scheduling, budget, join and evidence semantics | Settled 2026-09-22: contract accepted ([parallel-wave-contract.md](../../docs/parallel-wave-contract.md)) and published as [ticket 28](issues/28-execute-and-check-one-parallel-wave.md); no measurement prototype was needed |
| D2 | Executable spec/bundle identity and approval/continuation lifecycle; restart/durability scope | Drafting approved, semantics NOT settled; direct acceptance needed for identity/continuation guarantees |
| D3 | Typed vocabulary and confidence/probability validation, source compatibility | Propose one non-Intervention example and invalid-output behavior for approval |
| D4 | Role composition representation, registry compatibility and verification policy | Inspect representative read-only registry fixtures and agree one composition contract |
| D5 | Fresh-session permission verification without protected writes | Adam authorizes a concrete isolated integration plan; no live test is authorized now |
| D6 | Browser UI and initial bounded questionnaire/graph scenario | Settled and delivered in tickets 13–14; no repeat approval prompt |
| D7 | Supported Kanban mapping and independent local checking harness | Agree one supported shape and explicit unsupported-shape failures; never activate it implicitly |

Other decisions stay parked: public/internal distribution, naming, packaging and non-Hermes
targets. Gated Hermes writes are not needed to claim artifact emission and remain unapproved.
Live model calls require separate authorization even when a ticket has offline fixture coverage.

## Promotion and working method

1. Review this whole map with Adam: coverage, priorities, granularity and genuine blocking edges.
2. Follow CURRENT.md: P26's initial scenario is delivered; ticket 28 is the next
   approved implementation, with D1 settled. Draft D2 without inventing lifecycle
   semantics. Record approved domain changes through the normal ADR process.
3. Publish approved slices as individual local issue files in dependency order. Provisional IDs
   may change. Use `ready-for-agent` only with settled scope, semantics, public test seam,
   review baseline and authorization; unresolved outlines stay here, not in the runnable frontier.
4. Every runtime addition includes reference execution, actual graph execution and conformance.
   Other slices demonstrate their user-visible behavior through the shared core, with surface
   smoke tests where appropriate. Do not manufacture schema/API/UI layer tickets.
5. Before implementation, inspect actual blast radius with Graft. Only necessary bounded
   prefactors go first within a slice; wide refactors need separately justified expand–contract.
6. Preserve unrelated local changes. No implementation, live calls, Hermes changes, staging or
   commits are authorized by this planning map.

**Next review questions:** Is the whole journey covered? Which checkpoint matters first?
Are any dependencies artificial? Which outlines should merge or split? Do we settle parallel
and identity contracts first while also defining the first front-door scenario?
