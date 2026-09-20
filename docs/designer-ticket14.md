# Ticket 14 — bounded browser composition

Implemented against approved review baseline `ecc32fe2d0edec05a90e0f358b30a54fdc53485b`.
Contract: `.scratch/workflow-generator/issues/14-compose-workflows-through-browser-questionnaire.md`.
This evidence supersedes HANDOFF.md's older statement that ticket 14 awaits scope approval.
Adam explicitly accepted and closed ticket 14 after trying the UI: “sounds good. Accept ticket 14.” Implementation and acceptance records are included in the ticket-14 commit.

## Delivered

- Questionnaire adds/removes adjustments and Decisions, selects destinations, and
  displays the structurally authored graph. Stable identities survive edits;
  removing a referenced node leaves visible dangling routes until repaired.
- Strict frozen integer score; receive, ±10 adjustments, thresholds 10/50/100.
  Exactly one receive entry, 1–6 nodes, at most two Decisions, complete routes,
  reachable acyclic nodes, ACCEPTED/REVIEW destinations. Equality takes at_or_above.
- `author_design(answers)` returns typed spec, trusted bindings, deterministic
  typed cases and view. The private UI transport is now a `nodes` questionnaire,
  replacing the old fixed three-field threshold questionnaire, not a public
  persistent spec format.
- `check_design(answers, evidence_dir=...)` generates the actual candidate and
  invokes existing independent reference/common conformance checking. Trusted
  Python tests retain candidate injection; HTTP has no executable-code seam.
- Budget is the longest **feasible executable** path, including receive and
  Decisions, excluding terminals. An infeasible longer path cannot inflate it.
- Each syntactic path contributes its integer input interval after accumulated
  adjustments. Nonempty intervals yield finite endpoints and an integer midpoint
  when available; one-sided intervals use the endpoint and adjacent interior
  integer; unconstrained paths use zero. Inputs are sorted/deduplicated. Scope
  and infeasible routes are displayed; PASS is explicitly listed-case-only.
- Every edit clears results and invalidates in-flight design/check responses,
  including invalid drafts. Validation/generation/check/evidence failures remain
  visible and cannot produce passing evidence.
- Existing server request boundary and protected-root code are unchanged. HTTP
  tests re-prove exact Host/Origin/token checks, bounded JSON requests, no arbitrary
  file reads/output roots/code, and rejection before generation/evidence creation.

## Changed files

- `agent_lab/designer/__init__.py`: bounded authoring, graph admission, interval
  cases, budget and view; retained core generation/check/evidence seams.
- `agent_lab/designer/static/{app.js,index.html,style.css}`: composition UI.
- `tests/test_designer.py`: independent route/terminal/final-score fixtures for
  linear, branching, reconvergent, two-Decision, equality and infeasible designs;
  case derivation fixtures, strict admission, altered candidates and failures.
- `tests/test_designer_server.py`: current questionnaire protocol and negative
  direct-request coverage; original request/read-only boundary tests retained.
- `tests/test_designer_browser.py`: nine real Chromium tests, including linear
  composition, operations before/after a Decision, deletion/repair, bounds,
  infeasible paths and stale design/check responses.
- This evidence document.

## Verification

Final working tree:

```text
.venv/bin/python -m pytest -q tests/test_designer.py tests/test_designer_server.py tests/test_designer_browser.py
191 passed

AGENT_LAB_JUDGMENT=stub .venv/bin/python -m pytest -q
614 passed, 3 skipped

.venv/bin/python -m mypy agent_lab
Success: no issues found in 22 source files

git diff --check
clean

graft build
refreshed successfully
```

The three expected skips are two opt-in live Jev checks and the optional real
Hermes plugin loader check. No live calls, Hermes writes, installation or activation.
Tests use real generated graphs and real persisted evidence at temporary roots.

## Independent review

Two independent reviewers examined only implementation/test changes against the
approved baseline, excluding unrelated pre-existing working-tree edits.

- **Standards:** no documented-standard violations. One optional maintenance
  suggestion remains: extract the repeated node-ID Field constraint into an
  annotated type. No broad refactor was performed.
- **Spec:** found budget initially counted an infeasible longer path. Fixed by
  taking the maximum over feasible paths, with `INFEASIBLE_LONG` independently
  expecting budget 3 instead of 5, plus actual execution and evidence assertions.
  Independent follow-up confirmed resolution and ran all 122 public designer
  tests. No outstanding confirmed Spec findings.

## Try it

```bash
.venv/bin/python -m agent_lab.designer --evidence-dir /tmp/workflow-evidence
```

Open the printed exact `127.0.0.1` URL. To create a linear design, remove the
Decision and repair receive's done destination, then add an adjustment and route
receive to its stable ID. New unconnected nodes intentionally make a draft invalid
until connected. Branching designs can route either Decision outcome through
adjustments or reconverge sequentially; this is not parallel execution.

Unrelated initial edits and untracked planning/config files were preserved. Adam
subsequently accepted and closed the ticket, then authorized its scoped commit.
