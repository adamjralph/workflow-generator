# 15: Compose and check offline request triage

**What to build:** Extend the browser questionnaire beyond the score demo so a user can compose a useful offline support-request triage workflow, inspect its graph, and generate/check it against supplied requests. The workflow assigns a team and priority and produces a deterministic handling summary. This is one complete browser-to-core-to-visible-evidence slice, not separate UI and backend work.

**Blocked by:** None (can start immediately). Ticket 14, bounded browser composition, is accepted and closed.

**Status:** resolved

**Acceptance:** Adam explicitly accepted ticket 15 ("accept"). Implemented in
`178f3e0`; evidence: `docs/designer-ticket15.md`. All acceptance criteria below
are verified and accepted: 720 passed, 3 expected skips; mypy clean; independent
Standards/Spec review found no blocking findings. Ticket 15 is accepted and closed.

## Approved contract

Adam approved support-request triage, the two-ticket breakdown and dependency, and the concrete contract in conversation. Ticket 16 adds custom-request entry; this ticket uses supplied examples only.

- Inputs: request ID, category (`billing`, `technical`, `general`), urgency (`normal`, `urgent`), and short description.
- Trusted deterministic operations: assign team, assign priority, produce a handling summary.
- Decisions route on category or urgency; descriptions are data, never interpreted as instructions or classified from free text.
- Outputs: selected team, priority, handling summary, and visited route.
- Default demo: category selects the team, urgency selects priority, and branches reconverge before summary.
- Examples: all six category/urgency combinations, with independently specified expected outputs.
- Limits: acyclic workflows, at most 12 nodes and three Decisions. Every completing path must assign team and priority before producing its summary.

## Acceptance criteria

- [x] The questionnaire supports adding/removing the trusted triage operations and category/urgency Decisions, choosing destinations, and seeing structural graph changes. This remains questionnaire editing, not drag-and-drop or arbitrary browser-supplied code.
- [x] The default workflow routes all six supplied combinations through team assignment, priority assignment, and a deterministic summary. The browser visibly shows each input, visited route, team, priority, and summary.
- [x] Inputs use strict typed state and a finite operation catalog. Invalid fields, values, graph shapes, destinations, and over-limit designs fail visibly before generation/execution. Document and test concrete string bounds and catalog labels without adding new business behavior.
- [x] Admission enforces acyclic complete routing, the 12-node/three-Decision limits, and assignment of team and priority before summary on every completing path. Preserve bounded execution through the existing Budget/accounting seam.
- [x] Authored designs use the existing typed Spec, trusted bindings, generated graph, independently compiled plain reference, and common conformance checker. No substitute toy runner or self-comparison is used.
- [x] Tests independently specify expected routes and outputs for all six default examples, plus edited designs demonstrating actual changed behavior. Expected fixtures are not derived by calling the implementation under test.
- [x] The six supplied cases remain visibly listed when checking edited designs. PASS is explicitly case-scoped structural/behavioral conformance, not proof of correctness or free-text coverage.
- [x] Public-seam tests detect an altered candidate; validation, generation, execution, checking, and evidence-write failures remain visible and cannot produce passing evidence.
- [x] Every design edit clears stale results and invalidates in-flight responses, including edits that leave an invalid draft.
- [x] Existing exact loopback/Host/Origin/token and bounded-request protections remain enforced. Evidence goes only to the caller-selected protected output root; HTTP cannot choose arbitrary code, files, or output roots.
- [x] Automated core/HTTP tests and real-browser coverage demonstrate the complete slice; the offline regression suite and type checking pass, with expected optional skips documented.

## Boundaries

Offline only: no AI/model calls, external integrations, sending messages, creating external support tickets, or Hermes writes/activation. Hermes source, configuration, authentication, and live state remain read-only. No persistent public Spec format, packaging, Parallel, Gates, Loops, new Judgment vocabulary, or broad prefactor is authorized. Existing ticket-14 delivery is a foundation, not work to reimplement. Custom-request entry belongs to ticket 16.
