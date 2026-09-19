# Workflow Generator handoff

Updated: ticket 01 closed at Adam's explicit request.
Next objective: **Start ticket 02 only in a fresh session using Adam's supplied prompt.**
Final-answer owner: Adam. No coordinating profile is assigned.
Authorization: ticket 01 closure is complete; implementation landed as `cddadc6` on `main`.
Adam authorised ticket 02 only for the next session. Tickets 02–06 were not started here.

## Start here

Read in this order:

1. `CONTEXT.md` (this directory) — the decided context: decisions (§2, §9, §10, §11), ruled-out
   directions, open questions, and the `## Language` glossary. Authoritative for this project.
2. `.scratch/workflow-generator/spec.md` — the product spec. 58 user stories, all closed decisions,
   every open item named, `Status: ready-for-agent`.
3. `docs/adr/0001-0009` — the nine decisions that are hard to reverse, surprising, and the result of
   a real trade-off. Read these before touching the area they govern.
4. `.scratch/workflow-generator/issues/01-06` — the diagnosis-first ticket set, in dependency order.
5. `README.md` (this directory) — one-page orientation.
6. `/home/hermes/Projects/agent-workflow-lab/WHY.md` — the measured problem this exists to solve.
7. `/home/hermes/Projects/agent-workflow-lab/spikes/parallel-capability/FINDINGS.md` — proven
   mechanics and the concurrency defects that constrain ticket 02.
8. `/home/hermes/Documents/life-os/Business/Stillroom/agent-team/verification/2026-09-18-cost-baseline/cost-baseline.md`
   — the baseline ticket 06 must reproduce.

Suggested skills: `handoff`, `plan`, `pydantic-graph-workflows`,
`autonomous-ai-agents:multi-agent-profile-workflows` (esp.
`references/measuring-workflow-token-cost.md`), `autonomous-ai-agents:hermes-agent`, `graft`,
`code-review`.

## Verified current state

**This project** (`~/Projects/workflow-generator/`)

- `CONTEXT.md` — decision record plus `## Language` glossary.
- `README.md` — current orientation, local setup, and core imports.
- `agent_lab/` — promoted runtime core; `lessons/` — full inherited regression suite.
- `docs/foundation/README.md` — provenance, verification, and retained limitations.
- `HANDOFF.md` — this file.
- `docs/adr/0001`–`0009` — nine ADRs (see below for subjects).
- `docs/agents/issue-tracker.md`, `docs/agents/triage-labels.md` — tracker conventions.
- `.scratch/workflow-generator/spec.md` — the product spec, `Status: ready-for-agent`.
- `.scratch/workflow-generator/issues/01`–`06` — ticket 01 is `resolved`; 02–06 remain
  `ready-for-agent`, subject to their blockers.
- **A git repository on `main`**, with docs-only baseline `e03a19d` and ticket 01 foundation
  promotion. The existing `agent_lab` namespace is the one local runtime core; no sibling checkout
  is required. Local test dependencies are in `requirements-dev.txt`, not distribution metadata.

**The foundation** (`~/Projects/agent-workflow-lab`)

- Branch `main` at `ce34093`, working tree clean (verified 2026-09-19).
- Test suite: **65 passed, 2 skipped** (the two live TypeSafe/Jev tests need
  `AGENT_LAB_JUDGMENT=jev`).
- Proven mechanics: real parallel fan-out (3 × 0.30s in **0.514s** wall vs 1.50s sequential),
  broadcast forks, multiple convergence points, mid-graph pause/resume with **zero** branch
  re-execution.
- Known defects, all measured in `FINDINGS.md`, all required by ticket 02: shared graph state is
  last-writer-wins (colliding `seq = [0, 0]`, two spent steps recording `used_steps = 1`);
  read → await model → write loses data silently (3 branches, 1 of 3 findings survived); no parallel
  fan-out in the Kanban dispatcher.
- The lab describes itself as "a teaching lab, not production infrastructure." Promoting it is
  ticket 01's real work.

**Cost baseline** (do not recompute from memory; use the script)

- Artifact: `cost-baseline.md` + `measure_cost_baseline.py` (read-only, exits 0) in the vault path
  above.
- Headline: **214 API calls, 1,132,524 fresh input, 4,608,338 cache-read, 89,103 output, 9.3
  calls/run, 26,826 context/call, 80% cache hit** across 23 worker runs.
- All-profile Gemini usage is **$4.41 estimated** — 9× the pilot-scoped `$0.474`, because the
  baseline counted worker runs only. Review traffic was invisible to it.
- Gemini emitted **24,025 output against 69,463 reasoning tokens (ratio 2.89)**.

**Supporting assets confirmed to exist**

- `~/.hermes/hermes-agent/plugins/kanban/dashboard/` — a plugin **can** ship a visual surface.
- `~/Projects/stillroom-studio/studio/hermes_bridge.py` — fresh-process Hermes discovery **without
  modifying Hermes**.
- `/home/hermes/Documents/life-os/Business/Stillroom/agent-team/specialist-agent-role-registry.yaml`
  — role contracts (`accepts`/`produces`/`reviews`) with `verified` status and evidence receipts.
- `~/.hermes/config.yaml:134-137` — `auxiliary.background_review` → `vertex` /
  `google/gemini-3.1-pro-preview` / `reasoning_effort: medium`.

## What this session produced

`to-spec` wrote the product spec; `grill-with-docs` ran three rounds and closed the design frontier;
`to-tickets` broke the diagnosis-first slice into tickets.

**ADRs written** (`docs/adr/`):

1. Conformance is structural and behavioural, never semantic.
2. Hermes is read-only; generated artifacts live in a user-named store.
3. Diagnosis produces measurements, not an inferred spec.
4. The spec is a typed directed graph of the five node types.
5. Approval binds to both the spec digest and the emitted bundle digest.
6. Regeneration rewrites only generated regions; hand-edits live in a user layer.
7. Node types compile through a fixed, documented mapping.
8. Behavioural conformance pins the plain driver as the reference execution.
9. Artifacts are immutable, digest-addressed versions.

**`CONTEXT.md` additions:** §9 (8 decisions), §10 (7), §11 (5), and a `## Language` glossary. §3.1,
§3.3, §3.4 and §6 are annotated with the new status of each previously-open item.

**Tickets** (dependency order): 01 promote the foundation; 02 fix parallel accounting; 03 diagnose
one Kanban run end to end; 04 prove the read-only boundary; 05 measure in all four units; 06
per-role breakdown and baseline. **Next frontier: ticket 02 only, in a fresh session.**

## In progress and pending

- **The spec is done and reviewed by `grill-with-docs`.** It is not awaiting more requirements.
- **The core/generation half of the spec is deliberately unticketked.** It needs *a* spec
  serialization to persist a spec or emit a bundle, and the format is parked behind the deferred
  community question (`CONTEXT.md` §3.1).
- **Ticket 01's foundation suite is green here: 65 passed, 2 live-Jev skips.** All nine core
  modules and three test files are unchanged from the lab at `ce34093`. An exploratory mypy run
  found the same 11 errors in both checkouts; see `docs/foundation/README.md`.
- Parallel corrections, diagnosis, measurement, and the unticketed generation half remain unbuilt.

## Decisions and boundaries

The full record is `CONTEXT.md` §2 and §9–§11. The shape a fresh agent most needs:

- **Diagnose first, generate second.** Ticket 01–06 are the diagnosis slice.
- **Never modify Hermes.** Read-only boundary, precisely defined (ADR-0002).
- **The core is the spec plus the conformance check**, not the questionnaire.
- **Five node types, hard-coded** (Judgment/Decision/Gate/Transform/Loop), compiled through a fixed
  mapping (ADR-0007).
- **Jev is the judgment model inside the finished workflow**, behind our Python boundary; a regular
  LLM checks questionnaire completeness.
- **Trusted = replayable, auditable, bound approvals (both digests), recorded terminal failures,
  verified least privilege.**
- **Metrics fixed up front:** calls/run (primary), context/call, tokens/run, cache hit.
- **Reviewer is a different model, permitted and opt-in, default off.**

**Boundaries that still hold**

- Ticket 02 is authorised only in a fresh session; do not start 03–06.
- Do not modify Hermes source, configuration, or authentication.
- Diagnose-only. Writing to profiles, `model_route`, prompts or board config is not authorised.
- No real client data in this project.
- Do not decide the parked items by inference. See below.

## Open decisions still owned by Adam

1. **Ticket 01 is accepted and closed at Adam's request.** Ticket 02 is next, in a fresh session.
2. **For us only, or a community plugin?** Deferred ~2 months. **Blocks** the spec serialization
   format, packaging, and product naming — which must not be decided ahead of it.
3. **Gated writes to Hermes beyond the read-only boundary.**
4. **Distribution and packaging.**
5. **Product naming** (a client's brand only makes sense if this is a Stillroom product).

## Blockers and troubleshooting

- The old claim that `workflow-generator` is not a git repo was stale: baseline `e03a19d`
  already existed before ticket 01; no reinitialisation was performed.
- **The lab is "a teaching lab".** Promoting it is real, unestimated work inside ticket 01.
- **The core cannot be ticketed until the spec format is unblocked.** Do not invent a format; it is
  parked behind open decision 2.
- **Ticket 01 is resolved at Adam's explicit request.** Do not start ticket 02 in the closure session.
- **`sessions.api_call_count` is a rollup** (188) that disagrees with the summed usage rows (214).
  Ticket 03 must use the summed figure.
- **Bare `except:` swallows schema errors.** Verify column names before trusting an empty result.
- **`output_tokens` under-reports real work.** Reasoning tokens are separate and dominated 2.89:1.
- `CONTEXT.md` and the product spec contain historical status text; their decided constraints
  and ADRs remain authoritative. Ticket 01 did not redesign the domain model.

## Next actions

1. Ticket 01 is closed; closure verification again reported **65 passed, 2 live-Jev skips**.
2. Start a **fresh session** for ticket 02 using Adam's supplied prompt. The subsequent
   dependency order remains 02 → 03 → {04, 05} → 06. `/implement` takes one ticket per session;
   do not point it at the product spec.
3. Do not start any ticket before its blockers are resolved. Ticket 02's acceptance boxes and
   closure remain Adam's responsibility. Do not start tickets 03–06.

## Definition of done

**For the spec:** met — it covers every closed decision, names each open item, invents nothing, and
has been through `grill-with-docs`. **For a build:** real tool output shows it runs, and a
before/after measurement through the existing attribution join demonstrates the efficiency claim in
the four agreed units. No claim of improvement without a measured before from the same join.
