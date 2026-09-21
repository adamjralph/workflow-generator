# 16: Try custom support requests against a composed workflow

**What to build:** Let a user enter a support request in the browser, execute the currently composed triage workflow offline, and inspect its visited route, assigned team, priority, and deterministic handling summary. Clearly distinguish this custom execution from the supplied-case conformance check.

**Blocked by:** 15 — Compose and check offline request triage.

**Status:** accepted and closed

Adam explicitly accepted ticket 16 ("accept"). Implementation: `0b87473`.
Verification: `docs/designer-ticket16.md` — 808 passed, 3 expected skips,
44 real Chromium tests, and clean mypy.

## Approved contract

Adam approved this as the second vertical slice after supplied-case composition/checking. Reuse ticket 15's strict request fields, finite operation catalog, graph admission, and execution bounds; do not introduce a second triage model.

## Acceptance criteria

- [x] The browser accepts request ID, category (`billing`, `technical`, `general`), urgency (`normal`, `urgent`), and short description, using the same strict field rules as the supplied cases.
- [x] A valid custom request executes the actual generated graph for the current authored Spec through the existing core. The browser displays the submitted input, visited route, selected team, priority, and deterministic handling summary.
- [x] A custom execution is labeled as a run, not a conformance PASS. It neither replaces nor expands the evidence claim of the separately displayed supplied-case conformance check.
- [x] Invalid request fields or invalid designs fail visibly before execution; bounded execution, runtime failures, and audit/evidence failures cannot appear as successful runs.
- [x] Editing the workflow clears stale custom results and invalidates in-flight responses. Changing request fields also prevents results for an older input from appearing current.
- [x] Repeated runs do not leak retained state between requests and preserve the existing fresh-run logging/accounting guarantees.
- [x] Custom-request rendering treats request ID and description as text, not markup, executable code, or instructions.
- [x] Existing exact loopback/Host/Origin/token and bounded-request protections cover custom execution. HTTP cannot select arbitrary code, input files, or output roots; any run evidence uses the caller-selected protected output root.
- [x] Public-seam, HTTP, and real-browser tests cover successful requests across the category/urgency combinations, independently expected outputs, invalid requests, execution failures, and stale responses after workflow/request edits.
- [x] The full offline regression suite and type checking pass, with expected optional skips documented; ticket 15's composition and supplied-case checking remain usable.

## Boundaries

Offline execution only: no AI/model calls, free-text interpretation, sending, external support-ticket creation, live integrations, or Hermes writes/activation. No bulk imports, persistent public Spec format, packaging, Parallel, Gates, or broader workflow support. This ticket adds custom inputs to the accepted triage slice, not a new runtime or a claim of semantic correctness.
