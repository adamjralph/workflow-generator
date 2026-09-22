# Ticket 13 — local browser workflow designer

**Accepted and closed (2026-09-22):** reconciled under Adam's explicit authorization
to close finished tickets, using the delivered implementation and independent review
below. No runtime code changed. Historical results remain historical; see
[`CURRENT.md`](../CURRENT.md) for the present validation environment blocker.

## Run

Use the existing development environment (`requirements-dev.txt`). No frontend build,
CDN, model credentials or Hermes activation is needed:

```bash
.venv/bin/python -m agent_lab.designer --evidence-dir /tmp/workflow-designer-evidence
```

Open the printed **http://127.0.0.1:PORT/** URL (not `localhost`). Optional `--port`
selects a fixed port. Ctrl-C stops the server. Choose a caller-owned evidence directory
outside this repository, Hermes home/configuration and Hermes source. Known Hermes
home and loaded-host source paths are rejected; use repeatable `--protected-root PATH`
for additional Hermes installations/source roots. Evidence directories must be trusted local paths,
not concurrently replaced by another local process.

Select a threshold (10, 50 or 100), a below-threshold terminal and an at-or-above
terminal (ACCEPTED or REVIEW). Equality always takes **at_or_above**. The diagram
shows the same authored spec used for generation: receive Transform → threshold
Decision → chosen terminals. Safety terminals are displayed separately; they are
runtime failure outcomes, not authored Route edges. Each run has a two-step budget.

Generate / check builds an in-memory pydantic-graph candidate and invokes the existing
independent reference/conformance seam with typed below/at/above cases. The browser
shows case scope, findings and reference/candidate evidence paths. Logs are stored in
fresh `check-*` directories; the UI cannot change the output root or read arbitrary
files. Changing any answer invalidates previous results immediately, including late
in-flight responses. This does not cancel an already-started offline check; its logs
remain at the operator-selected root.

A pass is structural/behavioural agreement for these cases only, not semantic
correctness, universal conformance or measured savings. This slice does not persist
a spec or executable bundle, implement approval Gates, or define a public wire format.
These fresh conformance logs reuse the accepted ticket-10 checking contract; they are
not published artifact-store versions or approval-bound records. ADR 0009's immutable,
digest-addressed artifact lifecycle remains deferred to the artifact/Gate slice, not
claimed by this browser front door.

## Public seams and safety

- `author_design(answers)` returns the typed spec, finite trusted bindings, typed cases
  and a private UI view. Unknown fields, unsupported values and coercions fail closed.
- `check_design(answers, evidence_dir=...)` generates and checks through the shared core.
  Trusted Python tests may inject `candidate_factory`; browser requests cannot.
- `create_server(evidence_dir, port=0)` binds only IPv4 loopback. Exact Host, exact POST
  Origin, JSON content type, bounded request size and a random page token are required.
  No CORS, external assets, arbitrary bindings, code imports or browser-selected paths.
  CSP prohibits framing. This is a single-operator local app, not remote hosting or
  authentication against other local users/processes.

## Verification

```bash
.venv/bin/pip install -r requirements-browser.txt
# Install system Chromium, or set CHROMIUM to its executable.
.venv/bin/python -m pytest -q tests/test_designer.py tests/test_designer_server.py tests/test_designer_browser.py
.venv/bin/python -m mypy agent_lab
AGENT_LAB_JUDGMENT=stub .venv/bin/python -m pytest -q
```

Browser smoke tests are required, not silently skipped if dependencies are missing.
They cover answer → diagram → actual generation/check, editing and regeneration,
nonconforming candidates, generation errors, filesystem failure and late-result
invalidation. Core tests pin hand-authored expected routes for every catalog choice,
including equality; compare real persisted evidence; and exercise validation,
nonconforming behavior, audit I/O failure and protected roots. HTTP tests prove the
request-origin and fixed-root boundaries.

## Results and review

- Focused designer coverage: 51 tests, including five real Chromium smoke tests.
- Full offline suite: **474 passed, 3 expected optional skips** (two live-model tests
  and the real Hermes loader test).
- Mypy: **22 source files, zero errors**. Diff checks clean; Graft refreshed.
- Parallel Standards/Spec review against approved baseline
  `2047f1afe177ab60a993b68a56762689aa35fb0e`: no outstanding hard Standards or Spec
  violations. Standards initially questioned non-digest-addressed conformance logs;
  follow-up withdrew this as the accepted, explicitly bounded ticket-10 contract,
  not a new artifact-lifecycle claim. Optional duplication/catalog-maintenance smells
  remain; no broad refactor was introduced.
- Review prompted repeatable operator `--protected-root` support for additional
  Hermes installations, checked at startup and per generation/check.
- No live model calls, Hermes edits or activation occurred in the implementation.
  User acceptance/closure was separate from implementation and verification; it is
  now reconciled under the authorization stated above.
