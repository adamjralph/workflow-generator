# Workflow Generator — product spec

**Feature:** workflow-generator
**Status:** ready-for-agent
**Decided:** 2026-09-19
**Authoritative decisions:** `CONTEXT.md` §2 (closed) and §6 (deliberately open); `HANDOFF.md`.
**No ADRs exist yet.** `CONTEXT.md` is the domain document and the glossary for this spec.

---

## Problem Statement

The user runs a Hermes agent team — a set of named profiles that carry out work on Kanban boards
and similar runtimes. Every worker independently rediscovers its route and stops when it judges
itself done, so the cost of a run is set by the model's behaviour rather than by the workflow.
Across the measured baseline (23 confirmed worker runs), that came to **214 API calls and
1,132,524 fresh input tokens at ~9.3 calls per run**, with input costing roughly **12.7× output**.
Auxiliary and review traffic turned out to be a separate cost axis that the baseline did not see
at all.

From the user's perspective the problem is fourfold:

1. **They cannot see what a workflow costs or why.** There is no before-number, no per-role
   breakdown, and no way to tell which part of a run is expensive.
2. **They cannot prove a change helped.** Any claim of "faster and cheaper" is unfalsifiable
   without a measured baseline taken through the same join.
3. **They cannot safely build or modify a runnable workflow.** There is no mechanical way to show
   that a generated workflow matches the design it came from, that a human approved the exact
   artifact that shipped, or that a failure was recorded rather than swallowed.
4. **They cannot trust an agent-authored workflow with real work.** A prompt or a `SOUL.md` is not
   a security sandbox, and an agent loop with no declared shape has no knowable call count.

## Solution

A plug-and-play tool — shipped as a Hermes plugin with a visual surface (UI or TUI) and the same
core behind a standalone product and an internal build tool — that:

1. **Diagnoses** existing Hermes workflows and measures them in four fixed units: calls per run
   (primary), context per call (secondary), tokens per run (outcome), and cache hit rate (health).
   Diagnosis reads only; it never writes.
2. **Guides** the user through step-by-step, multiple-choice questions to design a workflow from a
   fixed set of five node types, so the design is typed rather than free prose.
3. **Draws** the workflow as a visual diagram/graph, before and after a change.
4. **Builds or modifies** a runnable workflow from that design, on `agent-workflow-lab` as the
   foundation.
5. **Links** data sources, **identifies** the agents a workflow needs and writes a `SOUL.md` for
   each, and **identifies** the skills it needs — reusing existing skills in preference to creating
   new ones, and creating skills only where none exist.
6. **Checks conformance**: a mechanical check that the runnable workflow matches the spec.
7. **Produces a trusted workflow**: replayable, auditable, with approvals bound to exact artifact
   digests, failures recorded as terminal states, and least privilege verified.
8. **Never modifies Hermes** — no edits to its source, configuration, or authentication.

The first capability to ship is diagnosis, because it produces value immediately and its output is
the input to generation.

## User Stories

### Diagnosis and measurement

1. As a Hermes operator, I want to measure an existing workflow in calls per run, context per call,
   tokens per run, and cache hit rate, so that I have a before-number to judge any change against.
2. As a Hermes operator, I want diagnosis to use the existing attribution join, so that the numbers
   match the ones my team already trusts.
3. As a Hermes operator, I want auxiliary and review traffic reported separately from the worker's
   own loop, so that I do not misattribute review spend to an agent's reasoning.
4. As a Hermes operator, I want reasoning tokens reported separately from `output_tokens`, so that
   cost forecasts are not under-counted by roughly 3×.
5. As a Hermes operator, I want diagnosis to read only and write nothing, so that inspecting a live
   workflow cannot change it.
6. As a Hermes operator, I want per-role and per-run breakdowns, so that I can see which role
   dominates cost.
7. As a Hermes operator, I want diagnosis to work without modifying Hermes source, configuration, or
   authentication, so that I can adopt it without risk.
8. As a Hermes operator, I want diagnosis to discover profiles, models, and skills the way our
   existing integration already does, so that the integration pattern is proven rather than assumed.
9. As a Hermes operator, I want diagnosis output to feed directly into design and generation, so
   that the measured baseline becomes the target the new workflow is built against.
10. As a Hermes operator, I want to diagnose a workflow that is not on Kanban, so that I am not tied
    to one runtime.

### Design and the questionnaire

11. As a workflow designer, I want to be taken through step-by-step questions rather than writing
    free prose, so that the design is complete and checkable.
12. As a workflow designer, I want multiple-choice answers, so that the resulting spec is typed and
    unambiguous.
13. As a workflow designer, I want a regular LLM to check that all information is present and that
    no follow-up is needed, so that I cannot accidentally submit an incomplete design.
14. As a workflow designer, I want the questionnaire to work without Jev, so that designing a
    workflow does not depend on the judgment model.
15. As a workflow designer, I want to choose the model that runs the completeness check, so that I
    control its cost and quality.
16. As a workflow designer, I want to design from a fixed set of node types, so that the result is
    reliable rather than inventive.
17. As a workflow designer, I want to use a Judgment node for a typed decision with confidence, so
    that real decision points are explicit.
18. As a workflow designer, I want to use a Decision node for code routing on a value, so that
    branching is deterministic and costs no model call.
19. As a workflow designer, I want to use a Gate node to pause for a human, so that risky steps
    require approval.
20. As a workflow designer, I want to use a Transform node for deterministic work, so that work that
    needs no model costs no model call.
21. As a workflow designer, I want to use a Loop node with a bounded exit predicate, so that retries
    cannot run forever.

### Visual workflow

22. As a workflow designer, I want to see a visual diagram/graph of the workflow, so that I can
    reason about its shape before building it.
23. As a workflow designer, I want parallel branches, joins, and multiple convergence points to be
    visible in the diagram, so that it reflects real fan-out rather than a straight line.
24. As a workflow designer, I want to see the diagram before and after a change, so that I can judge
    the delta.
25. As a workflow designer, I want the visual design layer to be useful on its own, so that I can use
    it as a standalone product.

### Building and generation

26. As a builder, I want the tool to build or modify a runnable workflow from the design, so that the
    design becomes real rather than staying a drawing.
27. As a builder, I want the generated workflow to preserve the foundation's typed state, transition
    allow-list, terminal states, and budgets, so that the trust properties survive generation.
28. As a builder, I want to choose the target runtime the runnable workflow is emitted for, so that
    it fits where I actually run it.
29. As a builder, I want generated work to declare and respect a step budget, so that the call count
    is a property of the workflow rather than of the model's whim.

### Jev and judgment

30. As a builder, I want Jev to be the judgment model inside the finished workflow, so that decision
    points receive a narrow typed choice with confidence and probability.
31. As an operator, I want agents to connect to our Python boundary rather than to Jev directly, so
    that Jev is isolated alongside data sources and environments.
32. As an operator, I want an invalid judgment to become a recorded `FAILED_VALIDATION` terminal
    rather than a silent coercion, so that bad model output is visible and stops the run.
33. As a tester, I want to swap Jev for a recorded or stub judgment source, so that runs are
    deterministic and testable offline.

### Data sources, agents, and skills

34. As a builder, I want help linking data sources, so that the workflow reads real data through a
    controlled boundary.
35. As a builder, I want the tool to identify which agents a workflow needs and write a `SOUL.md`
    for each, so that roles are defined explicitly.
36. As a builder, I want existing skills reused in preference to creating new ones, so that we do
    not duplicate capability.
37. As a builder, I want skills created only where none exist, so that creation is a last resort
    rather than the default.

### Trust

38. As an auditor, I want a run to be replayable byte-identically offline, so that I can reproduce a
    decision with no key and no network.
39. As an auditor, I want an append-only run log that records every transition including failures,
    so that the run is auditable exactly as it happened.
40. As an approver, I want my approval bound to the exact spec digest and the exact emitted bundle
    digest, each re-derived rather than trusted from stored state, so that an edited design or a
    changed emission cannot inherit my consent.
41. As an approver, I want a rejection to stop the run, so that a stored decision is never read as
    consent.
42. As an operator, I want failures to be recorded terminal states rather than exceptions escaping
    the workflow, so that nothing disappears silently.
43. As a security reviewer, I want least privilege enforced at the toolset level and verified in a
    fresh session, so that a prompt or `SOUL.md` is never treated as a sandbox.

### Conformance

44. As a builder, I want a conformance check that mechanically verifies the runnable workflow
    matches the spec, so that "matches the design" is a test rather than a promise.
45. As a builder, I want the conformance check to fail closed, so that a mismatch is an error and
    not a warning.
46. As a builder, I want a branch's conformance verdict to travel by return value through a reducer,
    so that concurrent branches cannot overwrite each other's verdicts.

### Metrics and improvement

47. As an operator, I want a before/after measurement taken through the same join, so that any
    efficiency claim is falsifiable.
48. As an operator, I want calls per run to be set by the workflow's declared shape, so that cost is
    knowable in advance.
49. As an operator, I want cache hit rate reported as a health metric, so that I can tell when the
    caching lever is spent.
50. As an operator, I want the reviewer to run on a different model from the one running the
    workflow, so that review is never self-review.

### Surface and integration

51. As an operator, I want the tool available as a Hermes plugin with a visual surface, so that it
    lives where I already work.
52. As an operator, I want the plugin to never modify Hermes, so that installing it is safe.
53. As an operator, I want a UI or a TUI, so that the surface can match how I work.
54. As an operator, I want the same core behind a standalone product, an internal build tool, and the
    plugin, so that capability does not fork into three implementations.

### Parallelism and durability

55. As a builder, I want run-level budget and sequence counters allocated globally, so that parallel
    branches cannot silently exceed a cap or collide on an event sequence number.
56. As a builder, I want branch results gathered by return value through reducers, so that a
    read-await-write race cannot lose findings.
57. As a builder, I want a gate between parallel waves, so that a human can check in and the run can
    resume without re-spending work already done.

### Regeneration

58. As a workflow designer, I want to hand-edit generated output without losing my edits on
    regeneration, so that generated and hand-written parts can coexist.

## Implementation Decisions

### Build on the foundation, and promote it deliberately

- The core is built on `agent-workflow-lab`. Its typed state, transition allow-list, terminal
  states, budgets, approval gate, Jev boundary, three interchangeable judgment sources, and the
  pydantic-graph driver proven for fan-out and resume are adopted, not reinvented.
- The lab describes itself as "a teaching lab, not production infrastructure." Promoting it is
  real, estimated work and is part of this project rather than a hidden assumption.
- Both drivers exist on purpose: a plain state machine and a pydantic-graph port must produce
  identical events and digests. That equivalence is an acceptance test, not an implementation
  detail.

### The core is the spec plus the conformance check

- The questionnaire is a front door, not the core. The core is a **spec** and a mechanical
  **conformance check** that a runnable workflow matches it.
- A spec is a **typed directed graph**: nodes are instances of the five fixed node types, edges are
  typed moves, and the spec declares budgets and terminals. It is not a linear route, and the
  foundation's stages are one compilation target, not the model. **See ADR 0004.**
- Diagnosis, design, generation, and conformance all speak in terms of the spec.
- The concrete on-disk spec format is **undecided** (see Further Notes, and it is blocked by the
  community question). The spec is defined here as a typed in-memory boundary; the serialization is
  not fixed and tests must not assume it.

### Conformance is structural and behavioural, never semantic

- The conformance check proves exactly two things: **structural** match (node types, edges,
  transitions, budgets, terminals, digests) and **behavioural** match — the spec compiles to a
  **reference execution** (the plain state-machine driver), and the emitted artifact (the
  pydantic-graph driver) must produce identical events and digests on a recorded run.
  **See ADR 0008.**
- It does **not** decide whether the workflow does what the user meant. `Conformance` and
  `Correctness` are separate terms, and "conformant" must never be read as "correct".
- **See ADR 0001.**

### The five node types are fixed and hard-coded

Node types are a small fixed set. A model may not invent node types. Reliability is the point.

| Node | What it is | Model used |
|---|---|---|
| **Judgment** | pick one of N typed options + confidence | Jev |
| **Decision** | code routing on a value | none |
| **Gate** | pause for a human, bound to the exact spec and bundle digests | none |
| **Transform** | deterministic work | none |
| **Loop** | bounded retry with an exit predicate | none |

- The five types compile to the foundation through a **fixed, documented mapping**: each spec node
  becomes a foundation node/stage, typed edges become allow-listed transitions, `Judgment` → the
  judgment call, `Decision` → a code router, `Gate` → the approval node, `Transform` → deterministic
  work, `Loop` → a bounded retry with an exit predicate. Terminals and budgets are declared in the
  spec. **See ADR 0007.**
- The foundation's existing six nodes are one *instance* of this mapping, not the model.

### Jev's role

- Jev is the **judgment model in the completed workflow**. It is a narrow typed classifier returning
  a choice plus a confidence and a probability. It does not orchestrate, write prose, call tools,
  or run workflows.
- Jev is **not** used in the questionnaire and **not** used to build. A regular LLM checks
  completeness; the user selects it.
- Agents connect to our Python boundary, not to Jev directly. Jev sits behind it alongside data
  sources and environments.
- The existing `JudgmentSource` protocol holds: `JevSource` (live), `RecordedSource` (offline
  replay), `StubSource` (tests). All return the same validated judgment. Invalid output raises and
  becomes a recorded `FAILED_VALIDATION` terminal rather than a silent coercion.

### Questionnaire

- The questionnaire is a **static decision tree** of multiple-choice questions, so the question count
  and flow are deterministic and auditable.
- A **single bounded model call** (a regular LLM, chosen by the user, not Jev) checks completeness —
  that all required information is present and no follow-up is needed.
- The questionnaire is a front door onto the core: it authors a spec and does not run workflows.

### Trusted means five concrete properties

1. **Replayable** — a recorded judgment replays byte-identically offline, with no key and no
   network.
2. **Auditable** — an append-only run log records every transition, including failures.
3. **Bound approvals** — a human decision is bound to **both the exact spec digest and the exact
   emitted bundle digest**, each **re-derived** and never trusted from stored state. An approval for
   an edited spec or a re-emitted bundle does not unlock, and a rejection is a decision that stops
   the run. **See ADR 0005.**
4. **Failures are recorded terminal states** — not exceptions escaping the workflow.
5. **Least privilege is verified** — a declared toolset is enforced at the toolset level and checked
   by spawning a **fresh Hermes session** and asserting that denied tools actually fail. A prompt or
   `SOUL.md` is not a sandbox, so the check is a real attempted denial, not a config read.

### Diagnosis

- Diagnosis is the **first capability to ship**. It measures existing Hermes workflows.
- Diagnosis is **runtime-neutral via a run-attribution adapter**: any runtime that records a link
  from a run to the session usage it caused is diagnosable, and Kanban is the first adapter. The
  first adapter wraps the existing proven join: Kanban `task_runs.metadata.worker_session_id` joined
  to per-profile `session_model_usage`, grouped by `task` so that auxiliary calls
  (`title_generation`, `goal_judge`, `compression`, `background_review`, `approval`) are reported
  separately from the worker's own loop.
- Diagnosis produces **measurements, not an inferred spec**: per-run and per-role evidence in the
  four units, plus the baseline. It does not infer a workflow graph from logs. The design generation
  consumes is authored through the questionnaire. **See ADR 0003.**
- A **diagnosis record** is typed per run: `run_id`, runtime, role, session ids, the four units,
  auxiliary/review separated, reasoning tokens separate, cache hit.
- The **run-attribution adapter** exposes a minimal read-only contract: `run_id → session ids, role,
  workflow identity`. Kanban is the first implementation.
- Roles come from the **`specialist-agent-role-registry.yaml`** role contracts (`accepts` /
  `produces` / `reviews`, `verified` with evidence receipts); it is the type system a spec compiles
  against, read under the read-only boundary.
- Measurement units are fixed up front so "more efficient" is testable: **calls per run** (primary),
  **context per call** (secondary), **tokens per run** (outcome), **cache hit rate** (health).
- **Reasoning tokens are a first-class cost line**, reported separately from `output_tokens`.
- Diagnosis is **read-only**. It writes nothing to Hermes.
- A session counts as workflow cost only when a recorded run names it; interactive chat sessions are
  excluded.
- The summed per-usage rows are the source of truth, not the `sessions.api_call_count` rollup.

### Never modify Hermes

- **Hermes is read-only.** "No writes to Hermes" is defined precisely as: no edits to Hermes source,
  configuration, authentication, or live board/profile state. Reading Hermes is always allowed, and
  the tool is plug-and-play. **See ADR 0002.**
- Discovery of profiles, models, and skills uses the proven **fresh-process adapter** pattern,
  reading Hermes config without writing it.
- Everything the tool produces — the spec, the emitted workflow, run logs, and approval records — is
  written to the tool's **own artifact store** or to a project directory the user names, never inside
  Hermes.

### Artifact store

- Artifacts are held as **immutable, digest-addressed versions** in a per-workflow directory: spec,
  emitted bundle, run logs, and approval records. Each regeneration creates a new version rather than
  overwriting, so an approved artifact cannot change underneath its approval. **See ADR 0009.**
- The store lives in a user-named project directory, never inside Hermes.

### Surface

- The surface is **not fixed**: a **UI or a TUI are both acceptable**. This is a decision, not an
  open question — what is undecided is which one ships first.
- The interaction model is question-and-answer with multiple choice, on either surface.
- A **TUI is an acceptable surface both for the tool and for driving surface-level checks.** Choosing
  a TUI does not change the seam decision: the core is tested at the spec boundary, and a TUI is
  just another front door onto the same core.
- A plugin ships its own surface through the supported plugin pattern (a mounted API router, a JS/CSS
  bundle, and a manifest) rather than by patching the dashboard. This is a supported pattern, not a
  workaround.

### Not tied to Kanban

- Kanban is a target and an evidence source, not the frame. It is a queue: one task, one worker, no
  parallel fan-out.
- Parallel branches, joins, and mid-graph resume require the pydantic-graph runtime, which is proven
  for exactly those mechanics.
- Kanban's `tasks` table already carries `workflow_template_id` and `current_step_key` — written but
  not consulted for routing. This is a ready-made slot for a generated workflow's identity and
  position, and the spec may populate it later through an explicit gate (writes are otherwise out of
  scope).

### Target runtime

- The **first target runtime is the pydantic-graph foundation**, already proven for fan-out, joins,
  and mid-graph resume, and it is the core.
- **Kanban is the second target.**
- **Non-Hermes targets** (eve, Claude Code, Codex, standalone) are deferred, and are additionally
  behind the undecided community question.

### Three uses, one engine

The three framings are three front doors on one core, not three products:

1. a workflow designer product for others,
2. our own build tool for client work,
3. a Hermes plugin.

### Generation and regeneration

- Generated output is written between **generated-region markers**; hand-edits live outside them in
  a **user layer**. Regeneration rewrites only the marked regions, so hand-edits survive.
  **See ADR 0006.**
- This is what makes user story 58 hold.

### Skills

- Skills are **reused first**. A new skill is created only when no existing skill matches **and** a
  human explicitly approves. Creation is recorded as an auditable action.

### Concurrency and accounting corrections (measured, not assumed)

These were found by running the parallel-capability spikes and constrain the design:

- **Run-level budget and sequence must move out of the per-run holder.** Concurrent branches
  produced colliding `seq = [0, 0]` and two spent steps recording `used_steps = 1`, so a cap can be
  exceeded silently and an append-only log cannot be replayed in order. Counters are allocated
  globally or prefixed per branch under a parent run.
- **Branch results travel by return value through reducers**, never accumulated into shared state
  across an `await`. Measured: three branches ran, the join collected all three results, but shared
  state held one of three findings.
- **Concurrent appends to the run log are safe; the numbering handed to them is not.** The file
  writer is append-only and atomic enough at this size.
- **A gate between parallel waves is the natural check-in point**; resuming from it re-spends
  nothing, via pending-task injection rather than a second graph entry point.

### Reviewer

- The reviewer is a **different model from the one running the workflow**, so review is never
  self-review. The user selects both.
- The selected reviewer is `vertex/google/gemini-3.1-pro-preview`, already configured as
  `auxiliary.background_review`, so it is existing behaviour rather than a new dependency.
- Review is **permitted and opt-in, default off**, and its cost is surfaced whenever it runs.
  Mandatory review is rejected because it recreates the invisible-review-spend blindness the
  baseline suffered from. Whenever review runs, the different-model rule holds.

### Sequencing

- This spec covers **the whole product**, not a diagnosis-only slice: it records the closed
decisions for design, generation, trust, and conformance as well as diagnosis.
- Diagnosis ships first; generation follows. Diagnosis establishes the baseline and proves savings,
  and its output is the input to generation.
- The generator **dogfoods**: its own design/build/review steps are themselves a workflow with a
  declared shape and budget, measured in the same four units.
- This spec authorises no build. Beginning implementation is Adam's decision.

## Testing Decisions

A good test asserts **externally observable behaviour at the seam** — the conformance report, the
emitted spec, the four measured units, the recorded terminal, the run-log events, the approval
outcome — and never private node internals or the call count of an internal function.

### The seam

The single highest seam is the **workflow spec boundary**: the typed contract through which
diagnosis, design, generation, and conformance all pass. Tests feed a spec and a run (or a recorded
run log) into the conformance check and assert the typed report, and assert the measured units from
diagnosis. This keeps the number of feature-level seams at one, and it follows the foundation's own
rule that the core is the spec plus the check.

**Confirmed 2026-09-19:** testing happens at the spec boundary, not at the plugin surface. The
plugin surface is deliberately not the primary seam, because the surface is not fixed (a UI or a TUI
are both acceptable) and would churn; a TUI is an acceptable surface for driving surface-level
checks. A small number of surface smoke tests may be added later to prove the surface is wired up,
but the core logic is tested at the spec.

Two supporting seams are **reused, not invented**:

- The foundation's existing `Deps` injection (`JudgmentSource`, `ApprovalStore`, `RunLog`) is the
  seam for deterministic runtime tests. `StubSource` and `RecordedSource` make runs offline and
  repeatable with no key and no network. This is the preferred existing seam and should not be
  duplicated.
- One new seam is unavoidable for diagnosis: a **run-attribution adapter** (Kanban first) returning
  measurement records. Its production implementation uses the fresh-process bridge pattern and has
  no write path; tests back it with fixtures so no test touches `~/.hermes`.

### Modules to be tested

- **Diagnosis measurement** — through the run-attribution adapter (Kanban first, fixtures in tests):
  the four units, auxiliary/review separation, reasoning-token reporting, and the exclusion of
  non-run sessions.
- **Spec and conformance** — the core seam: the spec compiles to a reference execution; the emitted
  artifact matching it structurally and behaviourally passes; one that diverges fails closed with a
  typed finding; the verdict travels by return value through a reducer across parallel branches.
- **Node-type mapping** — each of the five types compiles to the documented foundation shape, and the
  foundation's own six nodes are reproducible as one instance of the mapping.
- **Runtime drivers** — the plain state machine and the pydantic-graph driver produce identical
  terminals, stages, digests, events, and step accounting for the same input.
- **Approval gate** — exact-digest binding, digest re-derivation, rejection stopping the run, and
  approval from a different run or draft not unlocking.
- **Judgment sources** — stub, recorded, and live all yield the same validated judgment type; an
  invalid judgment becomes a recorded `FAILED_VALIDATION` terminal in both drivers.
- **Run log and budget** — append-only ordering, per-run sequence numbering, recorded failures, and
  a step cap that cannot be exceeded under parallel branches.
- **Non-modification** — the diagnosis adapter is read-only and the plugin performs no write to
  Hermes configuration, source, or authentication.

### Prior art

- `agent-workflow-lab/lessons/lesson_02_workflow/test_workflow.py` is the model for seam-level tests:
  it asserts driver equivalence, terminal reachability, digest-bound approval, recorded failures,
  and log shape without reaching into node internals.
- `agent-workflow-lab/spikes/parallel-capability/` is the model for tests that reproduce a measured
  concurrency defect and pin the fix with a regression test.
- The foundation's `conftest.py` / pytest `pythonpath` convention is the model for making the suite
  run from any working directory.

## Out of Scope

- **Writes to Hermes.** Profiles, `model_route`, prompts, and board configuration are not written.
  Writes may be added later behind an explicit gate; this spec ships diagnose-only.
- **Non-Hermes target runtimes** (eve, Claude Code, Codex, standalone) are not emitted by this spec;
  they are deferred and are additionally behind the community question.
- **Distribution and packaging.**
- **The concrete spec serialization format.**
- **Skill creation gating policy.**
- **Whether the questionnaire is static or model-assisted** (multiple-choice interaction is decided;
  the model's role in driving it is not).

## Further Notes

### Explicitly undecided (from `CONTEXT.md` §6 and §3) — not settled by this spec

These must not be treated as decided, and no implementation may invent an answer:

- **For us only, or a community plugin?** Revisit in ~2 months. **Blocks** the spec format and
  packaging, which must not be decided ahead of it.
- **Product naming.** A client's brand name (`Stillroom Workflow Generator`) only makes sense if this
  is a Stillroom product, so naming is **blocked by** the community question. Directory stays
  `workflow-generator`.
- **Gated writes to Hermes beyond the read-only boundary.** The boundary itself is decided (Hermes
  is read-only); whether writes are ever added behind a gate remains open. Default: diagnose-only.
- **The spec format** (own format vs reusing something with an existing checker). Blocked by the
  community question above. The spec's **conceptual model is decided** (a typed directed graph); only
  its serialization is open.
- **Distribution and packaging.** Blocked by the community question above.

### Domain vocabulary used throughout

`run`, `stage`, `transition`, `terminal`, `gate`, `budget`, `judgment`, `spec`, `conformance check`,
`calls per run`, `context per call`, `tokens per run`, `cache hit rate`, `Judgment node`,
`Decision node`, `Gate node`, `Transform node`, `Loop node`, `spec graph`, `reference execution`,
`conformance`, `correctness`, `run attribution`, `diagnosis record`, `artifact store`, `front door`.

### Working method

The spec flow is `to-spec` (synthesise, no interview) → `grill-with-docs` (adversarial interview that
also writes ADRs and glossary entries) → `to-tickets` (break into tracer-bullet tickets). This
document is the synthesis; it has been sharpened by the interview, which closed the design frontier
and left the remaining items parked behind the deferred community question (§3.1 of `CONTEXT.md`).
