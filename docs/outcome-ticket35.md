# Ticket 35 — exact declared JSON string values

## Contract and limits

`JsonOutputExpectation.string_fields` is an immutable tuple of
`StringFieldExpectation(field=..., allowed_values=(...))` declarations. Each field
must be required and constrained once; the allowed values are distinct literal
strings in a nonempty tuple. Empty strings are allowed as explicit literal values.
Matching is case-sensitive and does not trim or coerce. There are no nested field
paths, regular expressions, numeric comparisons or semantic judgments.

Missing fields retain `missing_field`; present non-string or disallowed values
produce `unexpected_value` with the literal field name. Findings omit observed
content. Duplicate JSON keys anywhere in the parsed object fail `invalid_json`,
including duplicates outside constrained fields, avoiding silent last-value wins.
This intentionally tightens parsing for presence-only checked outputs too.

The existing approved byte/file safety limits, run-owned output directories,
step-completion attribution and saved exact-byte checksums remain. Both drivers
execute independently; they use the same deterministic output checker. New fresh
spec snapshots include `string_fields: []` by default, changing their exact-byte
hashes. Existing saved declarations, replay evidence and historical hashes are
not rewritten. No public persistent spec format is established.

The representative scenario saves synthetic LinkedIn review outputs using the
existing `ReviewResult` vocabulary (`Approved`, `Changes requested`, `Blocked`)
and `copy-only` scope. A compliant `Blocked` result passes declared-output checking:
this does not mean editorial approval or publication permission. Tests execute
actual trusted file-writing bindings through both drivers and inspect saved
verdicts. This is offline contract coverage, not real/private-source acceptance,
a live Guardian run, full review-schema validation or a completed internal release.

## Reproduction and evidence — 2026-10-05

Checkout: `/home/hermes/Documents/Codex/2026-10-05/task-3/workflow-generator`.
Interpreter: `/home/hermes/Projects/workflow-generator/.venv/bin/python`.
Validation wrapper is invoked from the original project directory, as required;
pytest uses the isolated checkout's absolute test paths and root conftest imports.

Focused command: existing `workflow-generator-validation` wrapper + interpreter
`-m pytest -q <checkout>/tests/test_outcome_values.py <checkout>/tests/test_outcome.py
<checkout>/tests/test_workflow_spec.py <checkout>/tests/test_generation.py --tb=short`.
**159 passed**, exit 0, evidence root `/home/hermes/workflow-validation-scratch/v-0fSilc`.
An earlier attempt failed on new test-fixture setup and was corrected; it is not
passing evidence.

Typing from the isolated checkout: interpreter `-m mypy --cache-dir
/tmp/ticket35-mypy agent_lab`: **45 source files clean**, exit 0.

Independent GPT-6.1 Sol Standards/Spec review against the session baseline found
**no blocking findings**. Optional additional mutation/immutability tests were
suggested; inherited strict/frozen/revalidation behavior and copied nested-value
admission are already exercised. Reviewer performed no duplicate full test run.

Full command (from `/home/hermes/Projects/workflow-generator`):

```bash
/home/hermes/.hermes/profiles/astra-pinned/bin/workflow-generator-validation \
  /home/hermes/Projects/workflow-generator/.venv/bin/python -m pytest -q \
  /home/hermes/Documents/Codex/2026-10-05/task-3/workflow-generator/lessons \
  /home/hermes/Documents/Codex/2026-10-05/task-3/workflow-generator/tests --tb=short
```

Full offline suite: **2,468 passed, 2 failed, 3 expected skips**, exit 1 in
1,016.53 seconds, evidence root `/home/hermes/workflow-validation-scratch/v-nWuFhP`.
Both failures were plugin subprocess launch errors caused by the isolated checkout
missing `.venv/bin/python`. An ignored `.venv` symlink to the existing original
environment restored that path. No product code changed. The same wrapper/interpreter
reran exactly `tests/test_diagnosis_report.py::test_terminal_and_plugin_present_the_same_report_and_measured_before`
and `tests/test_read_only_boundary.py::test_local_plugin_install_registration_and_invocation_leave_protected_tree_unchanged`:
**2 passed**, exit 0, evidence root `/home/hermes/workflow-validation-scratch/v-rt7AGk`.
No full-suite rerun was performed or claimed. All observed failures are resolved.
No live calls or credentials read.

## Integration handoff

Original checkout and its five sibling status edits remain untouched. The focused
implementation commit includes code, tests, ticket and supporting contract/evidence
docs only. Combined status docs stay uncommitted in this isolated checkout.
`../ticket35-status.patch` is the incremental delta against the exact original
session-start documents, excluding inherited sibling edits. Parent should reread
original current contents and use `git apply --check` before applying that delta.
No PR, merge, deployment, repair dispatch or notification was performed.

Autonomous technical verification is complete; parent assessment is next. Adam
did not personally review this slice; V2–V5 and real-workflow outcome acceptance remain
open. Ticket 19's historical two-call proof keeps its implemented limits; its
contract now distinguishes future pillar relaxations without changing execution.
