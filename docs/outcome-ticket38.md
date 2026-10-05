# Ticket38 — declared outcome on a recorded LinkedIn review workflow

## Implemented boundary

`agent_lab.designer.review_outcome.check_review_outcome` joins ticket19's existing
completed Generator/Guardian workflow to tickets35–37. It first validates the
complete saved evidence chain and runs independent reference/generated replay
through `DraftChecks`. Failed replay stops before packet production, local repair
or delivery. It admits no provider or credential source.

The useful output is a private `review-packet.json`: exact validated draft/review,
original snapshot/run identity, receipt/check/draft/review digests, historical
per-role usage, copy-only scope and explicit `human_decision: required`. Unknown
historical usage remains unknown. New model/auth calls are zero; historical usage
does not become new spend, and this slice measures no savings.

The caller must declare accepted Guardian verdicts and an aggregate local allowance
of one or two output steps. Approved, Changes requested and Blocked are all completed
editorial reviews; policy acceptance is separate. Both outcome drivers check declared
top-level fields and exact attribution/scope/verdict strings. Nested draft/review
content comes from the trusted deterministic projection of validated replay.

Repair rebuilds that identical projection at most once in fresh output. It cannot
revise copy, change Guardian's verdict, resume an incomplete provider attempt,
modify source metadata or authorize publication. Execution failure is ineligible
and never retried. A verdict rejected by caller policy remains exhausted after
local packet repair. Omitting the endpoint makes no delivery claim.

An explicit loopback endpoint uses ticket37's bounded single attempt and suppresses
passed/repaired results. `private_fields` removes the six original attribution
constraints from the transported expectation and marks their names as redacted;
all exact constraints remain in local evidence. Alerts retain public verdict/scope/
human-decision policy, fresh outcome identities and unmet field names. Draft/review/
source text and original recording identifiers/digests are excluded. HTTP 2xx means
local acknowledgement, not receipt by Adam. Existing alert defaults remain intact.

`DraftSource.validate_output_root` keeps the derived store disjoint from capture
inputs, guidance, profiles and recordings, including ancestor overlap. Existing
files remain unchanged; replay adds fresh check receipts in the recording evidence
root. The adapter also pins the replay recording root to the captured source's validated
evidence root before any write. The CLI prints status/paths only and exits 1 for
unresolved outcomes.

## Usage

With an existing completed pair and a disjoint private output store:

```bash
python -m agent_lab.designer.review_outcome \
  --config /private/capture.json --recordings /private/evidence \
  --snapshot CAPTURE_DIGEST --run-request REQUEST_ID \
  --store /private/derived-output --accept-verdict Approved --step-allowance 2 \
  --driver graph
```

`--accept-verdict` may repeat to admit multiple distinct completed verdicts.
`--endpoint http://127.0.0.1:PORT/alerts` is optional, explicit and local only.
The placeholders describe operator inputs; no private input is embedded in Git.
Run from the isolated checkout using the existing project interpreter. Use the
existing validation wrapper from the original cwd for validation evidence.

## Validation — 2026-10-05

Checkout `/home/hermes/Documents/Codex/2026-10-05/task-6/workflow-generator`,
branch `ticket/38-representative-outcome-loop`, directly based on verified ticket37
checkpoint `75b2a97a0c6b05dde720cb2f96e1aaccd9177d14`. Root and predecessors are
preserved. An ignored `.venv` symlink reuses the existing project interpreter
for the plugin subprocess contract; it installs no packages. Five inherited combined status files remain uncommitted and separate.

Final-code focused: **225 passed**, exit 0, 28.75 seconds, private evidence
`/home/hermes/workflow-validation-scratch/v-vm3fbl`. The six focused files plus
`test_diagnosis_report.py::test_terminal_and_plugin_present_the_same_report_and_measured_before`
ran through the established wrapper from the original cwd. Complete final-code
regression: **2,571 passed, 3 expected skips**, exit 0, **1,066.10 seconds**
(17m46s), private `/home/hermes/workflow-validation-scratch/v-ajWj1b`.
Both saved `pytest-output.log` summary and `pytest-exit.txt` (0) were read back.
The skips are two opt-in TypeSafe live tests and the optional real Hermes loader.
Final tested implementation checkpoint was `251b9c1`; later edits are documents/status
only. The first runner finished before this clean rerun; no concurrent duplicate
full runner or elapsed-time abort occurred.

Exact complete-suite command, from the original project cwd:

```bash
/home/hermes/.hermes/profiles/astra-pinned/bin/workflow-generator-validation bash -c '
/home/hermes/Projects/workflow-generator/.venv/bin/python -m pytest -q \
  /home/hermes/Documents/Codex/2026-10-05/task-6/workflow-generator/lessons \
  /home/hermes/Documents/Codex/2026-10-05/task-6/workflow-generator/tests --tb=short \
  2>&1 | tee "$WORKFLOW_VALIDATION_DIR/pytest-output.log"
result=${PIPESTATUS[0]}
printf "%s\n" "$result" > "$WORKFLOW_VALIDATION_DIR/pytest-exit.txt"
exit "$result"'
```
 Initial complete
run finished with one setup failure: the diagnosis/plugin subprocess required the
predecessor's ignored `.venv` symlink. It was restored to the existing interpreter.
Initial private evidence `v-BZkrK5` recorded exit 1; that run preceded reviewed
corrections and establishes no final-code pass. The clean rerun follows only after
its completion. Typing after the
corrections: existing interpreter `-m mypy --cache-dir /tmp/ticket38-mypy agent_lab`,
49 source files clean, exit 0. A final CLI check against the existing real pair
passed at `8e6a96c`, private `v-KXCf9V/cli-summary.json`: zero model/auth calls,
no alert requested, human decision required. `git diff --check` passed.

Focused files: `test_review_outcome.py`, `test_designer_draft_check.py`,
`test_outcome.py`, `test_outcome_values.py`, `test_outcome_remedy.py`,
`test_outcome_alerts.py`, plus the plugin subprocess regression named above. They cover exact packet provenance, all three editorial
verdicts, caller policy, both drivers, missing-packet repair, preserved rejection,
private alert redaction, invalid redaction before reservation, corrupt/partial
recording rejection, protected outputs, network denial, unchanged input bytes,
CLI status/privacy, ineligible execution failures and mismatched recording-store rejection.

### Existing real recording, without a new provider call

Private evidence `/home/hermes/workflow-validation-scratch/v-LFyXpf`, with
`real-replay-summary.json` and `reproduce-real-replay.py`. The harness consumed the
existing successful operator-pinned ticket19 recording, not a new live execution.
Both drivers validated the entire pair and reproduced its exact completed state.
Each exercised intact packet (passed; alert suppressed), deliberate test-only
missing packet once (repaired; alert suppressed), and missing packet on both
attempts (exhausted; one loopback acknowledgement). Six assertions passed, process
exit 0. All checked existing capture/guidance/profile/draft/recording bytes remained
unchanged. The local server/thread were closed. Raw alert bytes excluded original
source identifiers/digests and draft text. No external destination or auth was used.

Exact harness invocation from original cwd, using the retained harness:

```bash
/home/hermes/.hermes/profiles/astra-pinned/bin/workflow-generator-validation \
  /home/hermes/Projects/workflow-generator/.venv/bin/python \
  /home/hermes/workflow-validation-scratch/v-LFyXpf/reproduce-real-replay.py
```

This proves the recorded real workflow's offline integration and bounded local
artifact remedy/alert. It does not demonstrate live generation with the new
outcome wrapper, a new editorial revision, public-use permission, actual delivery
to Adam, default-oldest live selection or full internal-release acceptance.

## Independent review

The code-review skill ran separate Standards and Spec agents against ticket37's
fixed checkpoint. Standards identified no actionable violations. Spec identified
original source identifiers/digests leaking through exact string constraints in
the alert declaration. The correction redacts those constraints only in transport,
with raw-byte assertions and invalid-redaction guards. Implementation self-review tightened recording-store preflight and identified
the failed-replay evidence pointer. Both reviewers re-reviewed
the alert correction, `8e6a96c` recording-store guard and final `251b9c1` failure-evidence pointer; zero remaining findings. They did not run tests or read
private evidence. This is independent agent review, not Adam's personal acceptance.

## Remaining release acceptance and handoff

The parent chooses the existing LinkedIn scenario. The exact remaining user delivery
choice is the channel and recipient/endpoint for one redacted test alert, plus its
authorized delivery mechanism. Concrete two-call/runtime bounds and optional later
revision scope are in the [minimal approval bundle](linkedin-live-acceptance-bundle.md).
The parent can settle bounded test execution under the continuing mandate; further
user approval applies to genuinely consequential permissions beyond it. Browser
outcome/remedy integration, attributable before/after measurement and actual
representative release acceptance remain. No live call/send starts in this session.

Checkout-local environment preflight is now mandatory and prominent in the handoff.
It passed on 2026-10-05: the ignored link uses the existing interpreter, `agent_lab`
imports from this successor, Python 3.14.7/pytest 9.1.1, and the plugin subprocess check
passes in the final focused run. Future sessions run that check before aggregate
pytest, without committing machine-specific setup.

Focused publication/readback and verified successor bundle/cumulative ticket35–38
status patch observations belong in [HANDOFF.md](../HANDOFF.md), which is the
fresh-session authority entry. The established original repository-local Git helper
must be loaded into only the push/readback process as described in
[ticket37 evidence](outcome-ticket37.md). No credentials/profile configuration
changes, source writes, merge, deployment or human-gate bypass occurred.
