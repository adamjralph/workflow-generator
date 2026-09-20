# 17: Compose and run one role-compatible workflow

**What to build:** Select from a small offline role catalog in the browser, inspect how declared inputs and outputs connect, then generate, run, and check one compatible workflow. Incompatible connections fail visibly.

**Blocked by:** None (can start immediately).

**Status:** ready-for-human

Implemented in `a1384c5`; awaiting Adam's explicit acceptance. Full offline suite:
915 passed, 3 expected skips, including 68 real Chromium tests; mypy clean.
Independent review: no documented Standards violations or Spec findings; two
optional maintainability heuristics recorded in the delivery evidence.

## Approval and readiness

Adam approved this slice and its dependency breakdown after accepting ticket 16,
then explicitly approved the example and compatibility policy, followed by the
complete detailed contract and review baseline below ("approve"). The ticket is
fully scoped and has now been implemented and independently reviewed. Acceptance
and closure remain Adam's decision.

## Acceptance criteria

- [ ] The browser offers a small, agreed offline role catalog grounded in registry contracts and shows the selected roles' declared inputs and outputs.
- [ ] A user can compose and inspect one bounded compatible workflow through the existing questionnaire and Spec seam.
- [ ] Incompatible role connections fail visibly before execution under an explicit compatibility policy.
- [ ] Deterministic fixture-backed bindings execute the actual generated graph and display observable outputs and run evidence; these are not represented as real agent execution.
- [ ] The same authored workflow supports supplied-case conformance against an independently executing plain reference, with independently expected outcomes and deliberate mismatch coverage.
- [ ] Browser/API boundaries, stale-result handling, bounded execution, fresh-run accounting, protected evidence outputs, and visible failure behavior remain intact.
- [ ] Public-seam, HTTP, and real-browser tests cover the agreed successful composition and rejected compositions; offline regression and type checking pass.

## Approved example and compatibility policy

Adam explicitly approved Signal Generator → Signal Guardian, connected by
`evidence_handoff`: Generator declares that output, Guardian accepts it, and
Guardian declares that it reviews Generator. The registry was inspected read-only.

- The browser selects producer, output type, and consumer from a finite catalog,
  including an incompatible alternative.
- Compatibility requires exact declared output/input type equality; no inferred
  aliases or automatic conversions.
- Explicit fixture operation contracts select required inputs from registry lists.
  The lists alone establish neither all-inputs-required nor whole-role compatibility
  from a single matching type.
- Two deterministic fixture-backed Transform nodes execute, not agents or model
  Judgments. Show the handoff, fixture result, visited route, and evidence.
- Registry verification status is historical metadata, not current permission or
  execution-quality proof. Receipt references are metadata, not executable inputs.
- Independently expected examples and plain-reference/generated-graph conformance
  cover successful execution; wrong connections and altered candidates fail.
- One two-role connection only; no Gates, revisions, live sources, or source-path
  selection.

## Approved detailed contract

### Catalog and admission

Use a minimal repository-owned registry excerpt for Signal Generator, Signal
Guardian, and Studio Producer, preserving their declared artifact types and review
relationships. Omit model routes, account identifiers and unrelated receipt details;
record provenance without depending on the original absolute path at runtime.
Studio Producer is the incompatible consumer for `evidence_handoff`.

Only Generator's `bounded_writing_brief` → `evidence_handoff` fixture operation and
Guardian's `evidence_handoff` → `review_verdict` fixture operation are executable.
An exact registry match without an available fixture operation is shown as unsupported,
not executable. Admission also requires Guardian's declared review relationship for
this review operation. Unknown IDs, extra fields, mismatches and malformed catalog
contracts fail before any operation runs.

### Fixture behavior and limits

Offer two fixed synthetic cases in the browser, not arbitrary custom input yet:
`with_evidence` and `without_evidence`. Each brief contains a nonblank request ID
(up to 64 Unicode code points), nonblank text (up to 240 code points), and zero to
three distinct nonblank evidence labels (up to 64 code points each). Labels are
inert text, never fetched URLs or paths. No coercion or silent truncation.

Generator copies those values into a typed `evidence_handoff`. Guardian returns a
typed `review_verdict` carrying the request ID and evidence count, with fixture
result `evidence_present` when the count is positive and `evidence_missing` otherwise.
These are mechanical fixture results, not approval, correctness, or a real review.
Both cases finish `COMPLETED`; missing evidence is a business result, not a runtime
failure. Hand-authored tests pin exact payloads for both cases.

The Spec contains exactly two Transform nodes connected by Route edges, a budget
of two steps, and terminals `COMPLETED`, `FAILED_VALIDATION`, `FAILED_BUDGET`.
No new node types or execution driver. Short-budget behavior is tested through
core seams, not an additional browser budget control.

### Surface, evidence and verification

Provide a separate role-workflow mode with producer/output/consumer choices and
an inspected graph. A selected fixture can run through the generated graph alone;
Generate / check covers both supplied cases against the independent plain reference.
Keep custom-run success and case-scoped conformance distinct. Design edits invalidate
both results and late responses; fixture selection invalidates the run only.

Preserve exact loopback/Host/Origin/token checks, existing request size limits,
inert rendering, protected output roots, fresh state/logs and complete run-evidence
checks. Runtime, generation and audit failures remain visible and never imply success.
No browser input can supply bindings, code, paths, initial outputs or registry records.

Public authoring/run/check seams, actual HTTP, and real Chromium tests cover both
fixtures, the incompatible consumer, unsupported operations, malformed contracts,
strict input validation, candidate structure/behavior tampering, short budgets,
state isolation, audit failure and stale responses. Full offline regression and
mypy must pass; existing score and triage modes remain usable.

Approved review baseline: `19ae20e563ab82968a23874380315ccfbc0a5678` (HEAD at
contract refinement). Preserve unrelated changes. No broad prefactor is proposed.

## Readiness decision

Adam explicitly approved the detailed catalog, fixture semantics, limits, surface
behavior, test seams and review baseline. Contract refinement is complete.
Ticket 18 remains separately blocked by this delivery and its unresolved source
and snapshot contract; this approval does not expand ticket 17's boundaries.

## Boundaries

Offline fixture-backed operations only. No real agent/model execution, SOUL generation,
skill generation, permission verification, live integrations, or Hermes writes/activation.
No new runtime, Parallel, Gates, persistent public Spec format, or packaging.
No broad prefactor is authorized; identify only necessary bounded changes during contract refinement.
