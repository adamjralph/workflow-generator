# Ticket 17 — offline role-compatible workflow

Implemented against approved baseline `19ae20e563ab82968a23874380315ccfbc0a5678`.
No live calls or Hermes writes. Unrelated working-tree changes were preserved.

## Delivered surface and scope

Select **Role workflow (offline fixtures)** in the existing browser. Inspect the
producer/output/consumer choices, full excerpted accepts/produces/review relations,
historical status, provenance, and the separate executable fixture contracts.
Signal Generator → `evidence_handoff` → Signal Guardian is executable.
Studio Producer rejects that handoff. Generator → `caption` → Studio Producer
matches registry types but is explicitly unsupported without fixture operations.

The repository-owned `agent_lab/designer/role_catalog.json` preserves the three
registry roles' declared types and review relationships. Its provenance names
`specialist-agent-role-registry.yaml`, its source sections, and the SHA-256 of the
read-only source inspected during implementation. Runtime reads only the local
excerpt, never the original absolute path. Model routes, accounts and receipt
details are omitted. Verification is historical metadata, not current permission
or execution quality; receipts are not executable inputs.

`author_design` dispatches role answers into `author_roles`. The latter accepts an
optional trusted-Python catalog for contract validation; HTTP cannot supply it.
Admission requires exact declared type membership on both sides, the available
Generator/Guardian fixture operations (including their required input/output
contracts), and Guardian's declared review relationship. The Spec has exactly two
Transforms, two Route edges, budget two and the three approved terminals.

`run_request(design, {"fixture": "with_evidence" | "without_evidence"}, ...)`
reuses the existing generated-graph-only run and complete evidence checks.
`check_design` reuses real graph generation, independent plain execution and
case-scoped conformance. There is no new execution driver or node type.

Brief/handoff fields are frozen, strict and bounded in Unicode code points.
Evidence labels are distinct inert text; neither URLs nor paths are fetched.
Both fixed cases complete. `evidence_present` / `evidence_missing` are mechanical
fixture results, not approval or a real review. Selected-fixture runs remain
separate from checking both supplied cases. Design edits discard both results and
late responses; fixture changes discard only the run, including late responses.

## Observed red → green evidence

Tests were written at the approved public author/run/check, actual HTTP and real
Chromium seams. Core run seams cover strict state and short-budget behavior.

1. **Author/check both cases:** new role answers failed score-answer validation;
   added role dispatch, typed fixture state, two transforms and the bounded Spec.
   Hand-written expected payloads pin both actual candidate outputs and routes.
2. **Catalog/admission:** catalog inspection failed with missing `catalog`, while
   incompatible and unsupported requests had only literal-choice errors. Added
   the validated excerpt, explicit compatibility/operation/review admission and
   inspected contract metadata. Malformed/missing contracts fail authoring.
3. **Selected fixture run:** public `run_request` failed triage-answer validation;
   added role fixture dispatch while retaining the existing run/evidence path.
   One early test incorrectly counted the existing lock sidecar as reference
   execution; corrected it to inspect execution `.jsonl` logs only.
4. **Strict fixture bounds:** core-run tests demonstrated acceptance of blank,
   oversized and duplicate-label briefs (11 failing cases). Added nonblank,
   code-point length, distinct-label and cardinality validation; all passed.
5. **Actual HTTP:** role design/check worked but selected-fixture run returned
   HTTP 400. Added strict fixture dispatch inside the existing protected `/api/run`
   envelope; actual HTTP then exercised both outputs successfully.
6. **Real Chromium mode:** selecting `roles` timed out because the option did not
   exist. Added the separate mode, catalog selectors/inspection, fixture selection
   and inert run/check output rendering using the existing stale-response guards.
7. **Inspected artifact types:** Chromium showed operation identifiers but not
   `evidence_handoff` / `review_verdict` in the admitted graph. The assertion failed;
   graph labels now explicitly show the two fixture output types.

Additional regression tests confirmed existing core guarantees without replacing
working implementations: actual candidate behavioral/structural mismatch,
unsupported candidate, generation/runtime failures, independent fresh log bytes
and digests, short budgets in both drivers, reused identity rejection, state
isolation, audit append/read failures, silently lost first/last events, protected
symlink roots, strict fixed-selection envelopes, and exact HTTP credential/body
limits. Filesystem fault injection stays at the filesystem boundary; deliberate
alternate graphs use the approved trusted candidate-factory seam.

Chromium additionally exercises incompatible and unsupported selections, malformed
catalog admission, generation/runtime/audit failures, inert candidate payloads,
late run success/error after every role control or mode/fixture edit, late
check/design responses after rejection, and fixture edits preserving an in-flight
case-scoped check. Score and triage regression files remain green.

## Verification

- `pytest -q tests/test_designer_roles.py tests/test_designer_roles_server.py tests/test_designer_roles_browser.py`:
  **107 passed**, including **24 required real Chromium tests**, no skips.
- Focused existing designer regression files (score, triage and custom request;
  public, server and browser files): **385 passed**, including their **44 Chromium
  tests**, no skips. `AGENT_LAB_JUDGMENT=stub` used.
- Combined focused coverage: **492 passing tests**, **68 real Chromium tests**.
- `python -m mypy agent_lab`: **25 source files, no issues** (repeated during slices).
- `git diff --check`: clean. `graft build`: refreshed local ignored graph.
- Full offline suite: `AGENT_LAB_JUDGMENT=stub .venv/bin/python -m pytest -q -rs`
  — **915 passed, 3 expected skips** in 183.61s, including all **68 real Chromium tests**.
  Skips: two opt-in live Jev calls and the optional real Hermes loader check.
  Console record: `/tmp/workflow-ticket17-full-suite.txt`.
- Parent reran mypy: **25 source files, no issues**.

## Independent review

Two independent reviewers examined `git diff
19ae20e563ab82968a23874380315ccfbc0a5678...a1384c5`, excluding unrelated
working-tree changes.

### Standards

No confirmed documented-standard violations. Two optional maintainability
heuristics remain: repeated role/triage request dispatch in the HTTP and public
run boundaries, and duplicated fixed fixture-contract declarations in catalog
presentation and admission. Neither is a demonstrated runtime defect; no broad
refactor was added to this bounded slice.

### Spec

No confirmed missing/partial requirements, incorrect behavior, or scope creep.
The reviewer independently reran all ticket-17 public, HTTP, and Chromium tests:
**107 passed**. No code changes were needed after the full-suite run.

Implementation: `a1384c5`. Ticket 17 awaits Adam's explicit acceptance; review does
not close it or authorize implementation of ticket 18.
