# Ticket 15 — offline support-request triage

Implementation baseline: `76a08fa11d0cb42d4d13c297a8fb5a59ad059796`.
Scope: ticket 15 only; no custom-request entry (ticket 16), live calls, external
support tickets, Hermes writes, activation, persistent Spec format, or packaging.
Ticket acceptance/closure remains with Adam. Unrelated handoff/roadmap edits are
outside this delivery.

## Try it

```bash
.venv/bin/python -m agent_lab.designer --evidence-dir /tmp/workflow-ticket15-evidence
```

Open the printed exact `http://127.0.0.1:PORT/` URL and select **Support-request
triage** in **Workflow mode**. Score demo remains the initial mode and retains
its existing composition behavior. Changing modes explicitly resets to that
mode's default design and invalidates results. Triage's graph scrolls horizontally
at readable text size rather than shrinking its eight-to-twelve nodes.

## Contract and decisions

- Private questionnaire transport: `mode: "triage"`, an explicit `entry`, and
  1–12 nodes. Every field is strict; extras are forbidden. No browser-selected
  state/cases, code/bindings, files, or output roots.
- Node IDs, entry, destinations and request IDs: 1–64 characters matching
  `[A-Za-z][A-Za-z0-9_-]*`. Descriptions: 1–240 characters, at least one non-whitespace
  character; Unicode and instruction-like text are inert data. Summary output:
  at most 360 characters (empty only before the summary operation).
- Input category: `billing`, `technical`, `general`; urgency: `normal`, `urgent`.
  Output team: `billing`, `technical`, `general`; priority: `normal`, `high`.
  Team/priority initially unset. State is strict, frozen Pydantic state.
- Finite catalog: `assign_team` (select one team), `assign_priority` (select one
  priority), `summarize`, `category` (three labeled routes), and `urgency` (two
  labeled routes). Transforms have a `done` route. Descriptions never drive a
  Decision and are never interpreted as instructions or classified.
- Summary format: `<request_id>: <team> team; <priority> priority. <description>`.
  Assignments may overwrite earlier assignments. A completing route must have a
  current summary: later assignments require another summary, so displayed
  outputs cannot contradict a stale summary. This is an ordering invariant, not
  another business operation.
- Complete acyclic routing, unique/nonterminal IDs, declared entry/destinations,
  all nodes reachable, at most three Decisions. Only `COMPLETED` is selectable as
  an ordinary terminal; `FAILED_VALIDATION` and `FAILED_BUDGET` remain automatic
  safety terminals. Every **syntactic** path must assign team and priority before
  summary, including branches infeasible for correlated category/urgency Decisions.
- Budget is the longest admitted syntactic path, counting node visits, not
  terminals. It is enforced by the existing `Budget` / `RunAccounting.reserve`
  seam. The default has eight nodes but spends five steps per supplied request;
  the twelve-node/three-Decision fixture has a nine-step longest path.
- Default category branches assign teams and reconverge at urgency; priority
  branches reconverge at summary. All six supplied requests remain fixed and
  visibly listed on edits, including invalid drafts. No ticket-16 input form.

## Real core and visible evidence

`author_design` dispatches only the explicit triage mode to the finite catalog;
existing score authoring remains intact. Both modes produce typed `WorkflowSpec`
and trusted local bindings. `generate_candidate` still uses `generate_graph`;
`check_design` still uses the common `check_conformance`, with independently
compiled plain reference and an independently executable generated candidate.
There is no added runner, reference-as-candidate, output prediction, or second run
for display.

The small core addition is `ConformanceReport.outputs`: observed candidate state,
terminal, used steps, and visited labeled route from the **same checked run**.
It does not affect PASS calculation. The browser renders these outputs (including
nonconforming candidate outputs), all supplied inputs, and both evidence-log paths.
Structural/behavioral PASS is explicitly restricted to the listed cases, not
semantic correctness or free-text coverage (ADRs 0001/0008).

The exact loopback Host/Origin/token, content type, and bounded 4096-byte request
protections are unchanged. The server still owns the caller-selected protected
output root; source/Hermes protection is unchanged (ADR 0002). Evidence continues
the accepted fresh temporary conformance-log contract, not a new persistent
artifact/Spec serialization scheme. Every edit calls revision-based invalidation,
including entry/mode changes and invalid add/remove/destination edits. Late design
and check responses cannot restore older results.

## Test-first evidence and verification

Approved seams: `author_design` / `check_design`, actual loopback HTTP, and real
Chromium. Expected six-case fixtures in `tests/test_designer_triage.py` are worked
literals, not outputs obtained from the implementation. They specify inputs,
teams, priorities, summaries and routes; edited team/priority designs separately
pin changed behavior.

Recorded vertical cycles:

1. Six-request core tracer failed at `author_design` (unsupported triage mode).
   Added strict catalog/state, typed Spec authoring, and actual checked-candidate
   outputs. Targeted core/score/conformance: **174 passed**; mypy clean.
2. All-path admission/longer edited route cycle: **15 failures, 1 pass** before
   graph admission and derived Budget. Then triage/score: **138 passed**; mypy clean.
3. Strict catalog/state, altered-candidate and failure probes: **51 passed**.
   HTTP reuse/admission/security/failure probes plus existing HTTP: **101 passed**.
4. Real-browser tracer failed because Workflow mode did not exist. After adding
   questionnaire mode and visible checked outputs, triage plus existing Chromium
   tests: **10 passed**. Extended add/remove/reconnect, catalog bounds, stale
   responses and five failure modes: **9 triage browser tests passed**.
5. Readable graph test failed at 1116px width; added intrinsic-width scrollable
   triage SVG. Final expanded core/browser targeted command below: **74 passed**;
   mypy clean (23 source files).

Commands executed regularly during implementation:

```bash
.venv/bin/python -m pytest -q tests/test_designer_triage.py
.venv/bin/python -m pytest -q tests/test_designer_triage_server.py tests/test_designer_server.py
.venv/bin/python -m pytest -q tests/test_designer_triage.py tests/test_designer_triage_browser.py tests/test_designer_browser.py
.venv/bin/python -m mypy agent_lab
```

Additional coverage includes the exact twelve/thirteen-node boundary; three/four
Decisions; unreachable nodes; bypassed team/priority/summary; missing/safety
terminal destinations; cycles; strict string bounds; refusal of custom cases and
output roots; altered candidate bindings; generation/unsupported-candidate/
execution errors; a real blocked output directory; and reference/candidate audit
append failures injected at the filesystem boundary, not a mocked checker.
Browser tests use actual system Chromium with no browser skips and real core
responses, including held/released HTTP responses in stale-result tests.

## Final verification

Full offline suite was run **once**, after implementation and targeted cycles:

```bash
AGENT_LAB_JUDGMENT=stub .venv/bin/python -m pytest -q
# 720 passed, 3 skipped in 109.85s
.venv/bin/python -m mypy agent_lab
# Success: no issues found in 23 source files
 git diff --check
# clean
 graft build
# refreshed local ignored graph: 52 files, 811 nodes, 2590 edges
```

The three expected skips are the two opt-in live Jev tests and the optional real
Hermes plugin loader check. All **19 real Chromium tests** ran (nine existing
score tests plus ten triage tests); none skipped. Full-suite console evidence:
`/tmp/workflow-ticket15-full-suite.txt` (local temporary artifact).

## Independent review

Adam approved review baseline `76a08fa11d0cb42d4d13c297a8fb5a59ad059796`.
Two independent reviewers examined the scoped staged diff against that baseline,
excluding unrelated working-tree changes.

- **Standards:** zero documented-standard violations. Two optional, related
  maintainability suggestions remain: shared graph-envelope serialization is
  duplicated between score/triage views, and triage subclasses the score-oriented
  `Design` presentation contract while supplying no score paths. Neither is a
  demonstrated behavioral failure; no broader refactor was added.
- **Spec:** zero confirmed findings or reportable speculative concerns. The
  reviewer checked all-path admission, real candidate outputs, supplied-case
  evidence, failure/stale-response coverage, strict bounds and read-only safety.

No code changes were required after review; the final verification above applies.
Unrelated dirty files were preserved. No known ticket-15 implementation gaps.
Acceptance and ticket closure remain with Adam.
