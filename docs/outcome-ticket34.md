# Ticket 34 — declared JSON output checks

## Contract

`JsonOutputExpectation` attaches to one `TransformNode.expected_output` in the
in-memory spec: safe relative `file`, distinct literal top-level `required_fields`,
and positive `max_bytes` (default 1 MiB, configurable). Adam approved the explicit
byte-limit contract during implementation. Fields check presence, not value:
null, false and empty values count as present. No semantic-quality claim.

`agent_lab.outcome.run_checked` admits the spec before fixture execution, saves
`declaration.json`, creates a fresh run-owned `output/` folder, executes through
the existing reference or generated graph driver, and saves `verdict.json` beside
`run.jsonl`. Use this opt-in entry point for checked runs; the drivers' ordinary
`run` methods do not automatically check outcomes. No new node type or driver.
The generated graph retains the expectation in its inspectable structure.

The verdict names the run, checked step, original declaration, workflow terminal,
findings and exact-byte SHA-256 checksums for the saved declaration and inspected
output (when safely read). `COMPLETED` is separate from `passed`.
A skipped or failed checked step cannot pass merely because another step wrote
its file. Every invocation has a fresh folder, so older output is not reused.

Reads reject symbolic links in the output root, path components and file; hard
links and nonregular files are rejected before content reads. Directory-descriptor
traversal avoids a check-then-follow race. Reads are bounded by the declared size.
Missing files, malformed JSON/non-object roots, missing fields, unsafe files and
exceeded byte limits produce named findings. Audit/write failures raise rather
than falsely claim a saved verdict.

Trusted local fixture bindings receive the output folder. This is not a Python
sandbox or a guarantee that a malicious binding writes only there. The slice
rejects model operations and uses no paid calls, retries, alerts, browser changes,
Hermes writes or private-source edits. Exactly one checked Transform is supported;
this is not the full expected-outcome pillar or a real-workflow acceptance.
Internal JSON evidence snapshots do not settle the deferred public spec format.

## Reproduce

```bash
.venv/bin/python -m agent_lab.outcome_demo \
  --store /home/hermes/workflow-validation-scratch/ticket-34-final-demo

/home/hermes/.hermes/profiles/astra-pinned/bin/workflow-generator-validation \
  .venv/bin/python -m pytest -q tests/test_outcome.py tests/test_workflow_spec.py \
  tests/test_generation.py tests/test_reference.py tests/test_conformance.py --tb=short

.venv/bin/python -m mypy agent_lab
python3 scripts/project_state.py check
python3 scripts/project_state.py measure
```

## Verified evidence — 2026-10-01

- Focused regression: **202 passed**, exit 0; permitted evidence root
  `/home/hermes/workflow-validation-scratch/v-ZY933p`.
- Typing: **45 source files clean**, exit 0.
- Fresh-session guard and `git diff --check`: passed; mandated entry read
  **5,742 chars** at that check (before later status edits).
- Four actual demonstrations, two per driver: valid output passes; missing `body`
  fails even though execution is `COMPLETED`. Read-back verified all four saved
  verdicts and exact saved declaration/output checksums. Private manifest:
  `/home/hermes/workflow-validation-scratch/ticket-34-final-demo/verified-demos.json`.
- Independent Standards review: no established hard breaches; declaration checksum
  ambiguity fixed and pinned by exact saved-byte regression. Optional test-factory
  duplication retained to keep security-specific cases explicit.
- Independent Spec review: one size-limit contract finding; resolved by Adam's
  explicit approval, typed configurable declaration and pass/fail/invalid-limit
  regression. Reviews were static; final corrections verified by the parent.
- Review queries refreshed the generated Graft index; `git status --short` showed
  no tracked Graft changes. Existing sibling edits and ticket-28 briefs preserved.

## Final full-suite evidence

The final revision completed the full offline suite with exit 0:
**2,436 passed, 3 skipped in 1,058.10 seconds**. The skips are two opt-in live
TypeSafe calls and the optional real Hermes plugin-loader check; those paths were
not verified. Log read back:
`/home/hermes/workflow-validation-scratch/ticket-34-final-demo/full-suite.log`.

Earlier timed-out/stopped attempts are not counted as passing evidence. Ticket 34
is implemented, verified and accepted by Adam. Commit and push are authorized;
inspect Git and the remote for publication status. No next slice is authorized.
