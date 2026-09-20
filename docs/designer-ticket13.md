# Ticket 13 — local browser workflow designer

## Run

Use the existing development environment (`requirements-dev.txt`). No frontend build,
CDN, model credentials or Hermes activation is needed:

```bash
.venv/bin/python -m agent_lab.designer --evidence-dir /tmp/workflow-designer-evidence
```

Open the printed **http://127.0.0.1:PORT/** URL (not `localhost`). Optional `--port`
selects a fixed port. Ctrl-C stops the server. Choose a caller-owned evidence directory
outside this repository, Hermes home/configuration and Hermes source. Known Hermes
home and loaded-host source paths are rejected; operators must not select other
undiscovered Hermes installations. Evidence directories must be trusted local paths,
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

Review baseline: `2047f1afe177ab60a993b68a56762689aa35fb0e`.
