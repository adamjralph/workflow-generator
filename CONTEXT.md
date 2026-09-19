# Workflow Generator — decided context

**Status:** decisions recorded, spec not yet written
**Started:** 2026-09-18
**Naming:** directory `workflow-generator`. Product name **Stillroom Workflow Generator** is not yet settled — see [Open decisions](#open-decisions). Stillroom is a client's brand, so this is called out deliberately rather than assumed.

This records *what has been decided*, *what was ruled out and why*, and *what is still open*.
It is not a spec. A spec gets written once the decisions below are closed.

---

## 1. What it is

Software that takes a person through step-by-step and multiple-choice questions and produces a
visual workflow (diagram/graph), then builds or modifies the runnable workflow from that design.

It will:
- guide the design through questions, not free prose
- produce a visual workflow
- build or modify a runnable workflow using `agent-workflow-lab` as the foundation
- help link data sources
- identify which agents are needed and write `SOUL.md` for them
- identify which skills are needed, reuse existing ones in preference to creating new, and
  create skills only where none exist
- produce an auditable, trusted workflow

The design layer (workflow designer) is a valid product on its own.

---

## 2. Decisions made

### 2.1 Diagnose first, generate second

**Decided:** the first capability is **diagnosis and measurement of existing Hermes workflows**,
not generation.

**Why:** diagnosis can measure what a workflow already does, establish a baseline, and then show
improvement and savings against it. Generation needs a spec format, a target emitter, SOUL
generation, skill creation and data linking before it produces anything usable. Diagnosis
produces value immediately, and its output is the input to generation.

The measured problem this rests on: the live Hermes agent team costs **214 API calls and
1,132,524 fresh input tokens across 23 runs**, at a near-uniform **~10 calls per run for every
role**. `input_tokens = api_calls × context_per_call`; calls is the multiplier. Full evidence in
`Business/Stillroom/agent-team/verification/2026-09-18-cost-baseline/`.

### 2.2 The plugin must not modify Hermes

**Decided:** no modification to Hermes. Plug-and-play only. No edits to Hermes source,
configuration, or authentication.

**Precedent:** `stillroom-studio` already integrates this way — its `studio/hermes_bridge.py` is a
fresh-process adapter that discovers profiles, models and skills without touching Hermes.

**User selects which model runs the checks.** A reviewer model can be a separate selection from
the one that runs the workflow, so review is not self-review.

### 2.3 Surface is not yet fixed

**Decided:** it may be a **UI or a TUI**. Both are acceptable. Interaction model is
question-and-answer with multiple choice.

**Confirmed feasible:** a Hermes plugin can ship a real visual surface. `plugins/kanban/` ships
`dashboard/plugin_api.py` (a FastAPI `APIRouter` mounted into the dashboard), `dashboard/dist/`
(JS + CSS), and `manifest.json`. So a plugin UI is a supported pattern, not a workaround.

### 2.4 Not tied to Kanban

**Decided:** do not feel tied to Kanban.

**Why:** Kanban is good for straight-line workflows. It has **no parallel fan-out** — it is a
queue, one task per worker. Parallel branches, joins, and mid-graph resume need a different
runtime. Measured on pydantic-graph 2.44.0: real fan-out (3 × 0.30s branches in **0.514s** wall
vs 1.50s sequential), broadcast forks, multiple convergence points, and pause/resume without
re-spending.

Kanban may still be *a* target and is a useful evidence source, but it is not the frame.

### 2.5 Jev's role: judgment inside the finished workflow

**Decided:** Jev is the **judgment model in the completed workflow**. It is not used in the
questionnaire and not used to build. Agents connect to our Python — not to Jev directly — and
Jev sits behind that boundary alongside data sources and environments.

**Why this is the right shape:** Jev is a narrow typed classifier returning a choice plus a
confidence and a probability. It does not orchestrate, write prose, call tools, or run workflows.
`agent_lab/judgment.py` already implements exactly this boundary — a `JudgmentSource` protocol
with `JevSource` (live), `RecordedSource` (offline replay) and `StubSource` (tests), all returning
the same validated `Judgment`. Invalid output raises and becomes a recorded `FAILED_VALIDATION`
terminal rather than a silent coercion.

**Also decided:** the questionnaire does not need Jev. A regular LLM can check that all
information is present and no follow-up is needed. Jev is kept for the workflow's real decision
points, where its typed confidence is genuinely strong.

### 2.6 What "trusted" means, concretely

Five properties, all already demonstrated in `agent-workflow-lab`:

1. **Replayable** — a recorded judgment replays byte-identically offline, no key, no network.
2. **Auditable** — append-only run log; every transition recorded, including failures.
3. **Bound approvals** — a human decision is bound to an exact artifact digest, which is
   **re-derived**, never trusted from stored state. An approval for an edited draft does not unlock.
4. **Failures are recorded terminal states** — not exceptions escaping the workflow.
5. **Least privilege is verified** — enforced at toolset level and checked in a fresh session,
   because a prompt or `SOUL.md` is not a security sandbox.

### 2.7 The five node types are hard-coded

**Decided:** node types are a fixed, small set — not agent-constructed. Reliability is the point;
letting a model invent node types works against it.

| Node | What it is | Model used |
|---|---|---|
| **Judgment** | pick one of N typed options + confidence | Jev |
| **Decision** | code routing on a value | none |
| **Gate** | pause for a human, bound to an exact artifact digest | none |
| **Transform** | deterministic work | none |
| **Loop** | bounded retry with an exit predicate | none |

### 2.8 Measurement units are fixed up front

**Decided:** efficiency claims are made in these units, so "more efficient" is testable:

- **Calls per run** — primary
- **Context per call** — secondary
- **Tokens per run** — outcome
- **Cache hit rate** — health

### 2.9 Three uses, one engine

**Decided:** the three framings are not three products — they are three front doors on one core.

1. Workflow designer / product for others
2. Our own build tool for client work
3. Hermes plugin

The core is **the spec plus the conformance check**, not the questionnaire.

---

## 3. Open decisions

### 3.1 Not yet decided — revisit in ~2 months

**For us only, or for the community as a plugin?**

Both remain open. Adam's stated position: "To be decided."

This changes the spec format, how hard the plugin API is pinned, and whether it is ever packaged
for others. It does **not** block the diagnosis work.

**Grill 2026-09-19:** kept open (see §9.5). The spec format, plugin-API pinning, and packaging are
explicitly **blocked by** this question and must not be decided ahead of it.

### 3.2 Product naming

`Stillroom Workflow Generator` sits beside `stillroom-studio` and `stillroom-lab`, but Stillroom is
a **client's** brand. Decide deliberately whether this is a Stillroom product or carries its own
name. Directory is `workflow-generator` for now.

### 3.3 Diagnose-only vs gated writes

Diagnosis is agreed. Whether the tool may ever **write** (profiles, `model_route`, prompts,
board config) is not settled. Recommended default: ship diagnose-only; add writes later behind an
explicit gate. Writing changes things that affect production work.

**Grill 2026-09-19:** the write *boundary* is now defined (see §9.3): Hermes is read-only, and
generated artifacts live in the tool's own store or a user-named directory. Whether gated writes to
Hermes are ever added remains open; the default is diagnose-only.

### 3.4 Reviewer model

**Decided:** the reviewer is a **different model from the one running the workflow**, so review is
never self-review. User selects both.

**Selected model:** `vertex/google/gemini-3.1-pro-preview` — already wired in Hermes config as
`auxiliary.background_review` at `reasoning_effort: medium`, so this is existing behaviour rather
than a new dependency. It is currently free to us under a $400 credit allowance (**$4.41 used**).

**Evidence for the choice:** Gemini 3.1 Pro reviewed `agent-workflow-lab` and produced **9 findings
(4 high, 5 medium)** — including that a rejection unlocked the approval gate, that the gate trusted
a stored digest instead of re-deriving it, and that the graph driver silently dropped budget and
audit semantics. Each was reproduced before fixing and pinned with a regression test; the suite went
46 → 65. Judged on the work it did, not on a proxy metric.

**Open:** whether a distinct reviewer model is *required* or merely *permitted*, and whether review
is mandatory for every generated workflow or opt-in.

**Grill 2026-09-19 — closed:** a distinct reviewer is *permitted and opt-in, default off*; whenever
review runs it must be a different model from the runner, and its cost is surfaced (see §9.6).

---

## 4. What we are building on

| Asset | What it gives us |
|---|---|
| `~/Projects/agent-workflow-lab` | typed state, transition allow-list, terminal states, budgets, the approval gate, the Jev boundary, three interchangeable judgment sources, and a pydantic-graph driver proven for fan-out and resume |
| `stillroom-studio` (`studio/hermes_bridge.py`) | the proven pattern for discovering Hermes profiles, models and skills without modifying Hermes |
| `plugins/kanban/dashboard/` | the proven pattern for shipping a plugin with a visual surface |
| `specialist-agent-role-registry.yaml` | role contracts (`accepts` / `produces` / `reviews`) plus `verified` status with evidence receipts — a real type system to compile against |
| The 2026-09-18 cost baseline | the before-number, and the join that produces it |

**Caveat:** `agent-workflow-lab` describes itself as "a teaching lab, not production
infrastructure". Building a product on it means promoting it, and that promotion is real work.

---

## 5. Constraints discovered by measurement

Each of these was found by running something, not by reasoning about it.

1. **Kanban has no parallel fan-out.** It is a queue. Parallel branches need another runtime.
2. **Kanban `tasks` already has `workflow_template_id` and `current_step_key`** — written by the
   v1 kernel, not consulted for routing. A ready-made slot.
3. **Concurrent branch state is last-writer-wins.** In the lab's shared holder, two branches
   produced events with colliding `seq = [0, 0]` and two spent steps recorded `used_steps = 1`,
   so a step cap can be exceeded silently.
4. **Read → await model → write loses data silently.** 3 agents ran, the join collected all 3
   return values, but shared state held 1 of 3 findings. Branch results must travel by return
   value through reducers, never accumulate in shared state across an `await`.
5. **`sessions.api_call_count` is a rollup**, not the source of truth (read 188 where the summed
   usage rows read 214). Any cost measurement must use the summed figure.
6. **A SOUL/prompt is not a sandbox.** Least privilege must be enforced at the toolset level and
   verified in a fresh session.
7. **Aux/review traffic is a third cost axis, separate from workflow cost.** Measured
   2026-09-19: Gemini 3.1 Pro totals **$4.41 estimated** across all profiles
   (`cost_source = official_docs_snapshot`), of which **$2.55** is Signal Guardian and **$1.85**
   is `hermes_engineer` `background_review` traffic. That is **9× the $0.474** in the
   2026-09-18 baseline — the baseline counted worker runs only, so review traffic was invisible
   to it. A generator that adds a reviewer node without surfacing this recreates the same
   blindness. Every Gemini row is `cost_status = estimated`, never actual.
8. **Reasoning tokens are a real cost line that `output_tokens` does not show.** Gemini
   measured **24,025 output tokens against 69,463 reasoning tokens** — a ratio of **2.89**.
   Cost forecasts and comparisons that read only `output_tokens` under-count by roughly 3×.

---

## 6. Deliberately not decided yet

Recorded so these are not treated as settled:

- The spec format (own format vs reusing something with an existing checker) — **still open, blocked
  by §3.1.** Its conceptual model is decided (see §10.1).
- How regeneration interacts with hand-edits — **closed 2026-09-19:** generated-region markers plus
  a user layer (see §10.4).
- Skill creation gating policy — **closed 2026-09-19:** reuse-first, creation gated on explicit human
  approval (see §10.6).
- Which target runtimes are emitted first, and whether non-Hermes targets are in scope — **closed
  2026-09-19:** pydantic-graph foundation first, Kanban second, non-Hermes deferred (see §10.2).
- Whether the questionnaire is static or model-assisted — **closed 2026-09-19:** static decision
  tree plus one bounded completeness check (see §9.7).
- Distribution and packaging — **still open, blocked by §3.1.**

---

## 7. Next action

**Decided 2026-09-19:** synthesise the spec with `to-spec`, then sharpen it with `grill-with-docs`.

Synthesis first, adversarial interview second. `CONTEXT.md` already records a large volume of
settled decisions, so grilling from a blank page would spend rounds re-asking what is already
answered. `to-spec` turns the existing conversation into a draft spec; `grill-with-docs` then
interrogates that draft and writes ADRs and glossary entries as decisions land.

This still does **not** settle the diagnosis-first-versus-spec-first question in §1.1. That
question is about *build order*, not about how the spec gets written. It remains open.

Nothing in this document authorises building. No code has been written for this project.

---

## 8. Working method for this project

Recorded because it is a project-level convention, not a one-off choice.

- **Issue tracker:** local Markdown under `.scratch/<feature-slug>/`, one feature per directory,
  spec at `spec.md`, tickets at `issues/NN-<slug>.md`. Vocabulary in
  `docs/agents/issue-tracker.md`; five triage roles in `docs/agents/triage-labels.md`.
- **Spec flow:** `to-spec` (synthesise, no interview) → `grill-with-docs` (relentless interview
  that also writes ADRs and glossary) → `to-tickets` (break into tracer-bullet tickets).
- **Dependency to check before either runs:** `grill-with-docs` is a pointer skill whose whole
  body delegates to `grilling` + `domain-modeling`. All three must resolve on the skill shelf.
  `grilling` was missing from the shelf until 2026-09-19 and the skill was silently half-dead.
- **Domain docs:** root `CONTEXT.md` (this file, which keeps the decision record and gains a
  `## Language` glossary section) plus ADRs in `docs/adr/`.

---

## 9. Decisions closed by grill-with-docs (2026-09-19)

These close items previously recorded as open. They sit alongside §2 and carry the same authority.
ADRs in `docs/adr/` are the durable record for the ones marked.

### 9.1 Diagnosis is runtime-neutral, via a run-attribution adapter

Diagnosis does not assume Kanban. It works against a **run-attribution adapter**: any runtime that
records a link from a run to the session usage it caused is diagnosable. Kanban is the first
adapter, wrapping the existing proven join. This keeps "not tied to Kanban" honest and adds one
seam rather than none or many.

### 9.2 Conformance is structural and behavioural, never semantic

The conformance check proves (a) **structural** match — node types, edges, transitions, budgets,
terminals, digests — and (b) **behavioural** match — a recorded run replays through both drivers
with identical events and digests. It does not decide whether the workflow does what the user meant.
`Conformance` and `Correctness` are distinct terms. **See ADR 0001.**

### 9.3 Hermes is read-only; artifacts live in a user-named store

"No writes to Hermes" is defined precisely as: no edits to Hermes source, configuration,
authentication, or live board/profile state. The tool writes only to its own **artifact store**
(spec, emitted workflow, run logs, approvals) or to a project directory the user names. Reading
Hermes is always allowed. **See ADR 0002.**

### 9.4 Diagnosis produces measurements, not an inferred spec

Diagnosis emits per-run and per-role measurements in the four units, plus the baseline. It does not
infer a workflow graph from logs; the design generation consumes is authored through the
questionnaire. **See ADR 0003.**

### 9.5 The community question stays deferred

"For us only, or a community plugin?" remains open per §3.1. The spec format and packaging are
blocked by it and must not be decided ahead of it.

### 9.6 Reviewer is permitted and opt-in

Review by a different model is **permitted, opt-in, default off**, with its cost surfaced whenever
it runs. Mandatory review is rejected: it recreates the invisible-review-spend blindness that the
baseline suffered from (aux/review traffic was 9× the measured worker cost and absent from it).
Whenever review runs, the reviewer must be a different model from the runner.

### 9.7 Questionnaire is a static decision tree

The questionnaire is a **static decision tree** of multiple-choice questions, so the question count
and flow are deterministic and auditable. One **bounded model call** (a regular LLM, chosen by the
user, not Jev) checks completeness. The questionnaire is a front door onto the core and authors a
spec; it does not run workflows.

### 9.8 Domain-doc structure

`CONTEXT.md` keeps the decision record it already is and gains a `## Language` glossary section;
ADRs live in `docs/adr/`. This deliberately favours one authoritative document over the generic
"glossary-only CONTEXT.md" convention, because the existing file is referenced as authoritative from
`README.md` and `HANDOFF.md`.

---

## 10. Decisions closed by grill-with-docs — Round 2 (2026-09-19)

Further to §9, same authority.

### 10.1 The spec is a typed directed graph

A spec is a directed graph of instances of the five fixed node types (Judgment, Decision, Gate,
Transform, Loop) joined by typed edges, with declared budgets and terminals. It is not a linear
route, and the foundation's stages/transitions are one compilation target, not the model. The
serialization stays undecided. **See ADR 0004.**

### 10.2 First target runtime is the pydantic-graph foundation

The first emitted runtime is the pydantic-graph foundation — already proven for fan-out, joins, and
resume, and it is the core. Kanban is the second target. Non-Hermes targets (eve, Claude Code,
Codex, standalone) are deferred, and are additionally behind §3.1.

### 10.3 Approval binds to both digests

An approval binds to the exact spec digest *and* the exact emitted bundle digest, each re-derived at
the gate. A changed spec or a changed bundle does not unlock. **See ADR 0005.**

### 10.4 Regeneration rewrites only generated regions

Generated output sits between generated-region markers; hand-edits live in a user layer outside
them. Regeneration rewrites only the marked regions, so hand-edits survive. **See ADR 0006.**

### 10.5 Diagnosis record and adapter contract

A diagnosis record is typed per run: `run_id`, runtime, role, session ids, the four units,
auxiliary/review separated, reasoning tokens separate, cache hit. The run-attribution adapter
exposes the minimal read-only contract `run_id → session ids, role, workflow identity`; Kanban is
the first implementation.

### 10.6 Skill creation is reuse-first and gated

Existing skills are reused first. A new skill is created only when no existing skill matches **and**
a human explicitly approves; the creation is recorded as an auditable action.

### 10.7 Least privilege is verified in a fresh session

A role's toolset is declared and enforced at the toolset level. It is verified by spawning a fresh
Hermes session and asserting that a denied tool actually fails — a real attempted denial, not a
config read. No Hermes modification is involved.

---

## 11. Decisions closed by grill-with-docs — Round 3 (2026-09-19)

Further to §9 and §10, same authority. With these, the design frontier is empty: everything still
open is parked behind §3.1.

### 11.1 Node types compile through a fixed mapping

The five spec node types compile to the foundation through a fixed, documented mapping; the
foundation's existing six nodes are one instance of it. **See ADR 0007.**

### 11.2 Behavioural conformance pins the plain driver as the reference

The spec compiles to a reference execution (the plain driver); the emitted artifact (the graph
driver) must produce identical events and digests on a recorded run. **See ADR 0008.**

### 11.3 Artifacts are immutable, digest-addressed versions

The artifact store holds a per-workflow directory of immutable, digest-addressed versions; each
regeneration creates a new version rather than overwriting. **See ADR 0009.**

### 11.4 The generator dogfoods its own workflow

The generator's own design/build/review steps are themselves a workflow with a declared shape and
budget, measured in the same four units.

### 11.5 Role contracts come from the registry

The `specialist-agent-role-registry.yaml` role contracts (`accepts` / `produces` / `reviews`, with
`verified` status and evidence receipts) are the type system a spec compiles against. Read under the
read-only boundary.

---

## Language

The project's canonical vocabulary. Only terms specific to this context appear here; general
programming concepts are deliberately excluded.

**Spec**:
The authored, typed description of a workflow — its nodes, edges, budgets, and terminals. The
contract the conformance check validates against.
_Avoid_: workflow config, blueprint

**Conformance**:
A mechanical check that a runnable workflow matches the spec structurally and behaviourally.
Never a claim that the workflow is correct.
_Avoid_: validation, correctness

**Correctness**:
Whether a workflow does what the user meant. Not mechanically checkable; outside conformance.
_Avoid_: semantic match

**Run**:
One execution of a workflow, identified by `run_id`.
_Avoid_: job, task

**Stage**:
A named point in a run's progress.
_Avoid_: step, phase

**Transition**:
A legal move from one stage to another. The transition allow-list is the only way forward.
_Avoid_: edge

**Terminal**:
The recorded end state of a run. Some terminals stop this pass; others end the run.
_Avoid_: end state, result

**Gate**:
A pause for a human decision bound to an exact artifact digest.
_Avoid_: approval step, checkpoint

**Budget**:
A hard cap on the steps a run may spend.
_Avoid_: limit, quota

**Judgment**:
A narrow typed decision — one of N options with a confidence — produced by a judgment source.
_Avoid_: classification, answer

**Judgment source**:
Where a judgment comes from: Jev (live), recorded (offline replay), or stub (tests).
_Avoid_: model, provider

**Node types**:
The fixed five — Judgment, Decision, Gate, Transform, Loop. A model may not invent others.
_Avoid_: node kinds, steps

**Calls per run**:
The primary cost unit and the main lever; `input_tokens = api_calls × context_per_call`.
_Avoid_: request count

**Context per call**:
The secondary cost unit: tokens resent on each call.
_Avoid_: prompt size

**Tokens per run**:
The outcome cost unit.
_Avoid_: usage

**Cache hit rate**:
The health metric that shows when the caching lever is spent.
_Avoid_: cache ratio

**Run attribution**:
The link from a run to the session usage it caused, supplied by a runtime-specific adapter.
_Avoid_: session matching

**Baseline**:
The measured before-number, taken through the attribution join in the four fixed units.
_Avoid_: benchmark

**Artifact store**:
The tool's own location for specs, emitted workflows, run logs, and approvals. Never inside Hermes.
_Avoid_: output folder

**Front door**:
A surface onto the one core — a UI, a TUI, the Hermes plugin, or the internal build tool.
_Avoid_: interface, app

**Questionnaire**:
The static, multiple-choice question tree that authors a spec.
_Avoid_: wizard, interview

**Completeness check**:
The one bounded model call that confirms the questionnaire captured all required information.
_Avoid_: review

**Reviewer**:
A model different from the runner, used to review a generated workflow when opted in.
_Avoid_: judge, critic
