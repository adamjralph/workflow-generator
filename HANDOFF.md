# Workflow Generator — next-session handoff

## Latest update — ticket 17 accepted and closed

Ticket 17 is implemented on `main` in `a1384c5`. Select **Role workflow (offline
fixtures)** in the browser to compose Signal Generator → `evidence_handoff` →
Signal Guardian, run either fixture, and independently check both supplied cases.
Studio Producer demonstrates an incompatible consumer; matching registry types
without fixture operations are explicitly unsupported. No real agents/models run.

- Full offline suite: **915 passed, 3 expected skips**, including **68 real Chromium
  tests**. Mypy: **25 files, no issues**. Console: `/tmp/workflow-ticket17-full-suite.txt`.
- Independent review against `19ae20e563ab82968a23874380315ccfbc0a5678`: Standards
  found no documented violations and two optional duplication heuristics; Spec
  found no confirmed issues and independently reran all 107 new tests successfully.
- Evidence: `docs/designer-ticket17.md`. No code changes after full-suite verification.
- Adam explicitly accepted ticket 17 ("approve"); it is accepted and closed.
  Do not reimplement it. Ticket 18's implementation prerequisite is now satisfied,
  but it remains `needs-info` pending its source/snapshot contract; no implementation
  of ticket 18 is authorized.
- Unrelated working-tree changes remain preserved. Hermes stays read-only; no live calls.

Next: refine ticket 18's controlled source and bounded snapshot contract with Adam.
Older next-step instructions below are historical and superseded by this update.

## Previous update — ticket 16 accepted and closed

Adam explicitly accepted ticket 16 ("accept"). Implementation is committed on
`main` as `0b87473`: **custom support requests execute offline against the
currently authored triage workflow**. Do not reimplement it. The local issue now
records acceptance and closure with its acceptance checklist checked.

### Next session

1. Read `docs/designer-ticket16.md` and the approved contract at
   `.scratch/workflow-generator/issues/16-try-custom-support-requests.md`.
2. Ticket 16 is accepted and closed. Adam approved the next two slices:
   ticket 17, compose and run one role-compatible workflow; ticket 18, run that
   workflow with one controlled read-only data source (blocked by 17).
3. Ticket 17 is now `ready-for-agent`: Adam explicitly approved the complete
   contract and review baseline `19ae20e563ab82968a23874380315ccfbc0a5678`.
   Read its local issue before implementation. The demo is Signal Generator →
   Signal Guardian via `evidence_handoff`, with two deterministic fixture-backed
   Transforms, two supplied cases and a two-step budget; no real agent execution.
   Ticket 18 remains `needs-info`, blocked by 17 and an agreed source/snapshot
   contract. No live integrations are authorized.
4. Inspect `git status` and use Graft before source exploration. Preserve the
   unrelated changes listed below. Hermes remains read-only; no live calls.

### Delivered behavior and verification

- `agent_lab/designer/custom.py::run_request` validates the current triage design
  and strict request fields, generates and executes the actual graph once, and
  returns submitted input, observed route, team, priority, deterministic summary,
  terminal, steps and fresh evidence path. Shared `TriageRequest` input rules feed
  the existing `TriageState`; no second triage runtime or model.
- Protected `POST /api/run` accepts only `{design, request}`. Exact loopback
  Host/Origin/token, JSON/body limits and caller-selected protected evidence root
  remain in force. No browser-supplied code, paths or output roots.
- Browser **Run request** results are separate from **Generate / check** supplied-
  case conformance. Custom input edits do not replace or expand conformance
  evidence. Workflow/request edits clear stale custom results and invalidate late
  success/error responses. Descriptions and rendered outputs remain inert text.
- Full offline suite after review fixes: **808 passed, 3 expected skips**, including
  **44 real Chromium tests** (none skipped). Mypy: **24 files, no issues**.
  Skips are two opt-in live Jev tests and the optional real Hermes loader check.
  Console evidence: `/tmp/workflow-ticket16-full-suite.txt` (temporary local file).
- Parallel independent review against starting HEAD `eabde12`: Standards found no
  violations/material smells; Spec found two gaps. Both were reproduced red-first
  and fixed: silent audit-event loss now fails event-count/accounting/route checks;
  description entry no longer truncates emoji using UTF-16 `maxlength` semantics.
  Regression tests and the full suite passed after fixes. The reviewers did not
  independently re-review those final fixes. Details: `docs/designer-ticket16.md`.
- Graft refreshed; diff checks clean. Ticket 15 and score composition still work.

### Try it

```bash
.venv/bin/python -m agent_lab.designer --evidence-dir /tmp/workflow-ticket16-evidence
```

Open the printed exact `http://127.0.0.1:PORT/` URL. Select **Support-request
triage**, fill the four fields under **Try a custom support request**, and click
**Run request**. **Generate / check** still checks only the six supplied cases.

### Working-tree caution

Ticket-16 implementation committed only its nine implementation/test/evidence
files. Existing modified files remain: `.gitignore`, `ROADMAP.md`, tickets 04/09,
`docs/read-only-ticket04.md`. Existing untracked files remain: `.ignore`,
`AGENTS.md`, `opencode.json`, local tickets 12/13/16 and
`.scratch/workflow-generator/map.md`. Do not stage them incidentally or discard
user changes. This handoff does not authorize expanding the runtime, persistent
Spec format, packaging, live integrations or Hermes writes/activation.

All older next-step instructions below are historical and superseded.

## Previous update — ticket 15 accepted

Adam explicitly accepted ticket 15 ("accept"). Offline support-request triage is
implemented in `178f3e0`, accepted and closed. Evidence: `docs/designer-ticket15.md`
(720 passed, 3 expected skips, 19 Chromium tests; mypy clean; independent review
found no blocking Standards or Spec findings). Do not reimplement it.

Ticket 16, custom support-request entry/execution, is the next unblocked ticket.
Its approved contract is in the local issue file; acceptance of ticket 15 does not
itself request implementation of ticket 16. Preserve unrelated working-tree changes.
Hermes remains read-only; no live calls are authorized.

Older next-step instructions below are historical and superseded by this update.

## Previous update — ticket 14 accepted

Adam explicitly accepted and closed ticket 14: “sounds good. Accept ticket 14.”
The local issue is now resolved. Browser composition is delivered; do not reimplement
or re-scope it. Evidence: `docs/designer-ticket14.md` (614 passed, 3 expected skips;
mypy clean; independent review findings resolved). Implementation and acceptance
records are included in the ticket-14 commit; preserve unrelated working-tree changes.

Next direction discussed: choose and scope one useful offline request-triage workflow
with meaningful operations, sample inputs and visible outputs. No concrete next-ticket
contract or implementation is approved yet. Parallel and Gates need not block that
scope discussion. Hermes remains read-only; no live calls are authorized.

The prior session notes below are historical: statements that ticket 14 awaits scope
or implementation are superseded by this update.

## Start here: previous state and approved direction

Working branch: `main`.

**Latest session:** ticket 13 is implemented and reviewed in `0bad1d0` and
`3e47b2b`. Adam tried the UI, confirmed that it is a constrained pre-built workflow
demo, and said “good work. next”. Do not reimplement ticket 13. Its local issue and
the planning map still contain older `ready-for-agent` wording; the implementation
and verification evidence is `docs/designer-ticket13.md`.

**Next-session priority:** scope **ticket 14: compose workflows through the browser
questionnaire**, moving beyond the fixed threshold-demo shape. Adam approved this
direction with “yes, but we will have to do it in next session handoff”. Detailed
contract design and implementation are deferred to the next session. Ticket 14 has
not yet been published; do not treat this direction as an agreed detailed spec.

**Numbering warning:** published ticket 13 came from planning item **P26**. The new
browser-composition ticket 14 is **not P14** (parallel branch Decisions/Loops), and
neither P13's parallel kernel nor P17's Gate work blocks this browser direction.
Read this handoff before selecting an item by number.

Tickets **01–12 are accepted and closed**. Ticket 12 implementation and review:
`597d315` (bounded Loop execution and conformance), `c0a2760` (review evidence and
candidate-side audit-failure regression). Adam explicitly confirmed ticket 12
acceptance/closure (“confirm 12”); its local issue now records closure and checked
acceptance criteria.

The generation/checking loop now supports Transform/Decision, restricted
Intervention Judgment and bounded Loop nodes with Route edges.
Its artifact is in-memory, with independently supplied candidates and
same-ID/separate-fresh-log exact trace/byte/digest comparison. Persistent spec
serialization remains deferred. Later milestones remain outlines, not authorized
implementation work.

Adam approved the next direction:

> Prove the smallest complete generation loop first:
> authored spec → plain reference → generated graph → passing conformance check.
> Keep the initial target restricted to Transform/Decision nodes and Route edges;
> expand node support only after this loop is demonstrated.

That restricted loop is now accepted. Adam subsequently clarified that a small
implementation slice must not restrict the planning horizon. The next session should
review the whole-product dependency map before refining the implementation frontier.

### Next session's job

1. Read `docs/designer-ticket13.md` and
   `.scratch/workflow-generator/issues/13-build-browser-workflow-designer.md` for the
   delivered browser slice. Inspect working-tree changes before editing; use Graft
   before opening source. The implementation is in `agent_lab/designer/`.
2. Scope ticket 14 with Adam around the approved direction:
   - Choose steps from a small, safe operation catalog.
   - Add Decisions and select their destinations.
   - See the graph change structurally, not just its threshold.
   - Generate/check through the same existing core.
   - Keep questionnaire-based editing, **not drag-and-drop**.
   Existing Transform/Decision + Route execution is enough for this direction;
   parallel execution and Gates remain separate work, not prerequisites.
3. Agree a bounded concrete demo, catalog/state contract, allowed graph shapes and
   size/budget limits, destination editing and invalid-design behavior, typed offline
   cases/independent expected outcomes, public test seams and review baseline before
   marking ticket 14 `ready-for-agent`. These details have **not** been approved yet.
   `3e47b2b` is the latest implementation baseline candidate, not an approved ticket-14
   review baseline. Publish the agreed contract under `.scratch/workflow-generator/issues/`.
4. Retain ticket 13's safety and evidence guarantees: finite trusted operations,
   strict inputs, caller-selected protected evidence root, exact loopback/origin/token
   request boundary, real core checking, visible failures and stale-result invalidation.
   No persistent public spec format, arbitrary browser-supplied code, live calls or
   Hermes changes are authorized by this direction.
5. Read `.scratch/workflow-generator/map.md`, `ROADMAP.md`, `CONTEXT.md` and relevant
   ADRs for the whole-product horizon. Update stale ticket-13 bookkeeping explicitly;
   do not conflate provisional P-identifiers with published issue numbers. Parallel,
   Gate/artifact identity, roles/data/skills and other outlines remain future work.
   No broad prefactor is pre-authorized.

### Ticket 13 verification and trying the UI

- Full offline suite: **474 passed, 3 expected optional skips**, including five real
  Chromium smoke tests. Mypy: **22 source files, zero errors**.
- Independent Standards/Spec review: no outstanding hard/blocking findings. A concern
  about digest-addressed logs was withdrawn on follow-up: the browser reuses the
  accepted temporary conformance-evidence contract, not an approval-bound artifact store.
- Commits: `0bad1d0` implementation; `3e47b2b` protected-root review follow-up/evidence.
- The current UI's shape is fixed: receive → threshold Decision → chosen terminals.
  Threshold/outcome choices author a real spec and execute real generation/conformance;
  it is not yet a general composer. Adam understands this limitation.

```bash
.venv/bin/python -m agent_lab.designer --evidence-dir /tmp/workflow-evidence
```

Open the printed `http://127.0.0.1:PORT/` URL, not `localhost`. Ctrl-C stops serving.
Browser tests require `requirements-browser.txt` and system Chromium (or `CHROMIUM`).
Repeatable `--protected-root PATH` protects additional Hermes installations.

**No live calls, Hermes activation changes or Hermes writes are authorized.**

## What works now

- Repo-local foundation in `agent_lab/`, with existing plain and graph business
  drivers and their equivalence tests. No sibling-runtime imports.
- Shared run-level budget reservations and append-only event sequence allocation;
  parallel foundation tests prove cap enforcement and preservation of branch
  results through reducers. This is not a general generated parallel engine.
- Read-only Kanban/Hermes diagnosis, four metrics, worker/auxiliary/review traffic
  separation, separate reasoning tokens, per-role/per-run reports and measured
  baseline comparisons. Immutable digest-addressed diagnosis/report artifacts.
- Terminal and local Hermes plugin commands. Installation/registration without
  protected edits is accepted; normal activation remains an explicit operator
  config opt-in. Do not bypass the host activation gate.
- `agent_lab.spec.validate_spec`: typed in-memory declarations for all five node
  types, Route/Fork edges, complete routing, joins and bounded-cycle validation.
  Admission is not execution or conformance.
- `agent_lab.reference.compile_reference`: Transform/Decision/Intervention Judgment/Loop
  + Route execution with explicit caller bindings and frozen Pydantic state.
  Judgment uses node-ID bindings with an assessment adapter and source; checking
  requires independent offline sources and compares full judgment/input evidence. All unsupported/unbound
  declarations, including unreachable ones, are rejected before execution.
  State snapshots are validated/detached; binding failures and budget exhaustion
  are recorded. Arbitrary node identities work, not just business Stage values.
- Loop predicates use exact opaque caller-binding keys and strict boolean results.
  Every visit reserves a step before invocation. True exits even after the last
  allowed repeat; false repeats while allowance remains, otherwise exhausts.
  Counters are per Loop identity/per run, never reset on re-entry, and start fresh
  for a new run. Predicate snapshots cannot mutate retained state or caller input.
  Events persist `repeat_count` and `max_iterations`; structural checking inspects
  actual bounds, predicate references, routes and unreachable declarations.
- Reference execution reuses `RunAccounting.reserve`, `Budget` and
  `RunLog.append_next`. `RunLog.fresh_run` refuses reused recorded identities and
  overlapping reference passes on the same log. Audit I/O failure stops execution
  visibly. No resume or crash durability.
- `agent_lab.generation.generate_graph` emits an owned in-memory executable graph;
  `agent_lab.conformance.check_conformance` checks actual execution configuration
  and supplied-case behavior against its independently compiled plain reference.
  Passing is restricted, case-scoped evidence, not universal conformance.

## Verification at the end of ticket 12

- Loop public-seam tests: **32 passed** (`tests/test_loop_routes.py`).
- Full offline suite: **423 passed, 3 optional skips**.
- Mypy: **19 source files, zero errors**; diff checks clean; Graft refreshed.
- Parallel Standards/Spec review against `5038a372780171b892b057be150baf7fb2f0dd8d`:
  no documented Standards violations and no confirmed Spec violations. The Spec
  reviewer suggested candidate-phase checker audit-failure coverage; added it.
- One optional maintainability smell retained: repeated type switches selecting
  `operation` / `value` / `exit_predicate` / Judgment node ID in admission,
  execution, generation and structural inspection. A small shared accessor could
  reduce drift, but is not a blocker or an approved standalone next ticket.
  Preserve independent driver control flow and actual-candidate inspection if
  addressing it; do not conflate shared metadata lookup with driver delegation.
- Evidence: `docs/loop-ticket12.md`. No live calls or Hermes edits.

```bash
.venv/bin/python -m pytest -q tests/test_loop_routes.py
.venv/bin/python -m mypy agent_lab
AGENT_LAB_JUDGMENT=stub .venv/bin/python -m pytest -q
git diff --check
```

## Historical verification at the end of ticket 11

- Judgment public-seam tests: **55 passed**.
- Full offline suite: **391 passed, 3 optional skips**.
- Mypy: **19 source files, zero errors**; diff checks clean; Graft refreshed.
- Standards: no hard violations, two optional heuristics retained.
- Spec: one coercion defect fixed with seven red→green cases; independent follow-up
  confirmed resolution. No live calls or Hermes changes.
- Evidence and public APIs: `docs/judgment-ticket11.md`.

## Historical verification at the end of ticket 10

- Focused generation/conformance/reference tests: **98 passed**.
- Full offline suite: **336 passed, 3 optional skips**.
- Mypy: **19 source files, zero errors**; diff checks clean; Graft refreshed.
- Both review axes found the same unordered-state strict-comparison bug, fixed
  with red→green public-seam regressions. Independent follow-up: Standards
  **0 new findings**, Spec **0 outstanding findings**.
- Evidence and public APIs: `docs/generation-ticket10.md`.

## Historical verification at the end of ticket 09

Implementation: `cc10740`; review improvement and evidence: `027efa0`.
Approved review baseline: `e6c1c9bc3d7920c518f210e05bcc271b685eebb8`.

- `tests/test_reference.py`: **26 passed**.
- Full offline suite: **264 passed, 3 optional skips** (two live Jev tests and the
  real Hermes loader check).
- Mypy: **17 source files, zero errors**.
- Parallel review: Standards **0 hard violations**, one optional duplication
  improvement addressed; Spec **0 actionable findings**.
- Focused tests, mypy and full suite rerun after the improvement; diff check clean
  and local Graft graph refreshed. No live calls or Hermes changes.

```bash
.venv/bin/python -m pytest -q tests/test_reference.py
.venv/bin/python -m mypy agent_lab
AGENT_LAB_JUDGMENT=stub .venv/bin/python -m pytest -q
```

## Remaining product work

See `ROADMAP.md` for ordered milestones and their completion evidence. Most of the
full generator and user-facing product remains: expansion beyond restricted
generation/conformance, arbitrary Judgment vocabularies, Gate and generated
parallel/resume support, spec/bundle approvals,
regeneration, roles/data/skills, questionnaire/visual surface, second runtime
and end-to-end dogfooding. There is no credible completion percentage or delivery
estimate yet; later milestones are not sized implementation tickets.

The product spec `.scratch/workflow-generator/spec.md` describes the whole product,
not current implementation authorization. It has stale introductory/out-of-scope
wording (for example, “No ADRs exist yet” and questionnaire/skill-policy language).
Use the later explicit decisions in `CONTEXT.md` and ADRs, plus approved ticket
contracts; do not interpret stale wording as new scope permission.

## Boundaries and decisions still owned by Adam

- Hermes source, configuration, authentication and live application state remain
  read-only. Outputs go to a caller-named project directory/tool store.
- Persistent spec serialization and distribution/packaging remain deferred behind
  the internal-versus-community decision. Naming remains undecided.
- Whether gated Hermes writes are ever added remains open. Producing a generated
  artifact does not authorize installing or activating it inside Hermes.
- UI versus TUI can be chosen later; the core remains the spec/conformance seam.
- The existing business approval binds run/draft, **not** a spec/bundle pair.
- Shared accounting is in-process; logging uses local advisory file locks. Do not
  mix explicit-sequence replay/import appends with active runtime writes.
- Bindings are trusted deterministic local code, not sandboxed code. State
  validators/serializers must support deterministic Python round-trip validation.
- Conformance means structural/behavioral agreement, not semantic correctness,
  proven savings, production readiness or verified least privilege.

## Working-tree care

Before this handoff update there were unrelated local edits to `.gitignore`,
tickets 04 and 09, and `docs/read-only-ticket04.md`, plus untracked `.ignore`,
`AGENTS.md`, `opencode.json` and the ticket-12 issue file. Leave these alone unless
explicitly updating ticket bookkeeping with Adam; inspect `git status` before
staging. Ticket-12 implementation commits deliberately excluded those files.
Do not use `git add -A` or discard user changes.

## Historical evidence pointers

- Foundation promotion: `docs/foundation/README.md` (source lab `ce34093`, repo
  promotion `cddadc6`; ticket 01 closure `a158632`).
- Ticket 02: `docs/foundation/parallel-accounting.md` (`7e1d517`, `c492e93`).
- Ticket 03: `docs/diagnosis-ticket03.md` (`fcfb06c`, `39a2bd2`).
- Ticket 04: `docs/read-only-ticket04.md` (`6271106` and subsequent explicit
  acceptance of installation without protected edits; activation remains separate).
- Ticket 05: `docs/measurement-ticket05.md` (`3106982`, `7abde37`).
- Ticket 07: `docs/typechecking-ticket07.md` (`2077d7d`, `12db524`).
- Ticket 06: `docs/report-ticket06.md` (`ea50593`, `c4af4d3`, `f6b9c49`).
- Ticket 08: `docs/spec-ticket08.md` (`98f555a`, `abfe1e8`; closure `e6c1c9b`).
- Ticket 09: `docs/reference-ticket09.md` (`cc10740`, `027efa0`).
- Ticket 10: `docs/generation-ticket10.md` (`568ad14`, `0855f25`, `03f1af3`); accepted.
