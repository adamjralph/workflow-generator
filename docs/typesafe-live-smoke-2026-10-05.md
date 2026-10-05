# TypeSafe live smoke evidence — 2026-10-05

## Observed result

Two selected existing tests ran once through the private evidence wrapper:
**2 passed, 0 failed, 0 errors, 0 skipped; pytest exit 0**. The mandated
`python3 scripts/project_state.py check` passed before execution.
Provider: TypeSafe System One at the SDK default `https://api.typesafe.ai`.
Model: explicit `jev-latest` (an alias; backend model revision was not captured).
Installed SDK: `typesafe-sdk==0.6.0`.

- `test_live_jev_returns_a_valid_typed_judgment`: validated source, intervention,
  confidence and review-gap ranges; positive input-token usage asserted. Its
  token totals are not persisted by this existing test.
- `test_live_jev_drives_the_workflow_end_to_end`: recorded Jev classification,
  routing, draft preparation/verification and approval-gate terminal `NEEDS_REVIEW`.
  Intervention `review_follow_up`, confidence 1.0, review gap 0.98.
  Recorded usage: **532 input tokens, 66 output tokens**. A replay recording was saved.

The run used the existing key loader with an existing Hermes dotenv pointer;
no key value, profile edit or persistent credential copy was introduced.
Scope allowed two SDK calls; SDK default `max_retries=2` means at most six HTTP
attempts. Actual HTTP-attempt count, first-test token totals, total USD cost and
remaining provider balance were not captured. There was no manual rerun, top-up
or payment/plan change. The runner has no dollar/output-token cap.

## Exact command executed

From `/home/hermes/Projects/workflow-generator`:

```bash
TYPESAFE_ENV_FILE=/home/hermes/.hermes/.env AGENT_LAB_JUDGMENT=jev PYTHONDONTWRITEBYTECODE=1 \
/home/hermes/.hermes/profiles/astra-pinned/bin/workflow-generator-validation bash -c '
.venv/bin/python -m pytest -q -x -p no:cacheprovider \
  lessons/lesson_03_jev/test_jev.py::test_live_jev_returns_a_valid_typed_judgment \
  lessons/lesson_03_jev/test_jev.py::test_live_jev_drives_the_workflow_end_to_end \
  --tb=short --junitxml="$WORKFLOW_VALIDATION_DIR/live-results.xml" \
  > "$WORKFLOW_VALIDATION_DIR/pytest.log" 2>&1
validation_status=$?
printf "pytest_exit_code=%s\n" "$validation_status"
exit "$validation_status"'
```

This records the completed command; it is not approval to rerun it.

## Private supporting evidence

Root: `/home/hermes/workflow-validation-scratch/v-sSzdfF/` (outside Git).

- `pytest.log`: pytest output.
- `live-results.xml`: two passing test cases, zero failures/errors/skips.
- `pytest-of-hermes/pytest-0/test_live_jev_drives_the_workf0/live.jsonl`:
  nodes `intake`, `classify`, `route`, `prepare`, `verify`, `await_approval`;
  final terminal `NEEDS_REVIEW`, classification and usage.
- `pytest-of-hermes/pytest-0/test_live_jev_drives_the_workf0/live-recording.json`:
  assessment digest, typed result and usage.

All four evidence files were inspected for the exact credential literal: zero
matches. Only this sanitized summary is intended for Git; raw evidence stays private.

## Scope and handoff

These are legacy typed-judgment/plain-workflow integration checks on a fixed
synthetic assessment. They do not establish semantic model accuracy, completed
human approval, posting, generated-driver parity, or live declared-output
compliance. Ticket 34 remains its accepted deterministic fixture-only slice;
`run_checked` rejects model operations. Its prior full-suite evidence remains
historical and was not rerun here.

No implementation/source changes. No further ticket or live run is authorized.
The optional real Hermes plugin-loader check remains unverified. The requested
`typesafe-ai` skill was not found in inspected local locations; no skill install
was attempted. Status/handoff updates are left uncommitted with the five existing
local document edits; only this new evidence file belongs in the focused commit.

Next action: `python3 scripts/project_state.py check`, then read `CURRENT.md`
and obtain Adam's next scoped instruction.
