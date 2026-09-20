# Workflow Generator — next-session handoff

## Start here: current state and approved direction

Working branch: `main`.

Tickets **01–11 are accepted and closed**. Adam explicitly accepted ticket 11
following implementation and independent review. Commits: `2e9848e` (implementation),
`cfa2151` (strict-validation review fix), `c3664b1` (review evidence).

The generation/checking loop now supports Transform/Decision and restricted
Intervention Judgment nodes with Route edges.
Its artifact is in-memory, with independently supplied candidates and
same-ID/separate-fresh-log exact trace/byte/digest comparison. Persistent spec
serialization remains deferred. Later milestones remain outlines, not authorized
implementation work.

Adam approved the next direction:

> Prove the smallest complete generation loop first:
> authored spec → plain reference → generated graph → passing conformance check.
> Keep the initial target restricted to Transform/Decision nodes and Route edges;
> expand node support only after this loop is demonstrated.

That restricted loop is now accepted. The next session should refine the next
smallest complete vertical slice from the remaining roadmap with `/to-tickets`.

### Next session's job

1. Read `ROADMAP.md`, `docs/judgment-ticket11.md` and the closed ticket 11.
2. Read `docs/reference-ticket09.md`, `docs/spec-ticket08.md`, `CONTEXT.md` and
   relevant ADRs. Use the repo's Graft graph before opening source.
3. Tickets 01–11 are accepted; do not reimplement or reopen them without cause.
4. Run `/to-tickets` on the remaining roadmap, starting with M2. Define the next
   smallest complete vertical slice across reference, generation and checking.
5. Surface decisions needing approval, including contract, public test seam and
   review baseline. Do not implement until the next ticket is approved.

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
- `agent_lab.reference.compile_reference`: Transform/Decision/Intervention Judgment
  + Route execution with explicit caller bindings and frozen Pydantic state.
  Judgment uses node-ID bindings with an assessment adapter and source; checking
  requires independent offline sources and compares full judgment/input evidence. All unsupported/unbound
  declarations, including unreachable ones, are rejected before execution.
  State snapshots are validated/detached; binding failures and budget exhaustion
  are recorded. Arbitrary node identities work, not just business Stage values.
- Reference execution reuses `RunAccounting.reserve`, `Budget` and
  `RunLog.append_next`. `RunLog.fresh_run` refuses reused recorded identities and
  overlapping reference passes on the same log. Audit I/O failure stops execution
  visibly. No resume or crash durability.
- `agent_lab.generation.generate_graph` emits an owned in-memory executable graph;
  `agent_lab.conformance.check_conformance` checks actual execution configuration
  and supplied-case behavior against its independently compiled plain reference.
  Passing is restricted, case-scoped evidence, not universal conformance.

## Verification at the end of ticket 11

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
generation/conformance, arbitrary Judgment vocabularies, Gate/Loop and generated
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
ticket 04, `docs/read-only-ticket04.md`, plus untracked `.ignore`, `AGENTS.md` and
`opencode.json`. Leave these alone; inspect `git status` before staging.
`HANDOFF.md` also had local updates to ticket 04's activation/acceptance wording;
that meaning is preserved above in this explicitly requested handoff refresh.
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
