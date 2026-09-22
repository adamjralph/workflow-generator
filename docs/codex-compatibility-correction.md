# Codex compatibility correction

## Frozen scope and regression seams (before implementation)

Approved source: `codex-protocol-diagnosis.md`, CURRENT and HANDOFF. This is a
Codex-only correction, not ticket 28 or live workflow acceptance.

- Exercise `CodexSource.invoke` with synthetic HTTP bytes at `asyncio.open_connection`.
  Allow absent Content-Type only on the pinned Codex endpoint. Empty, duplicate,
  explicit wrong MIME, non-200, encoding, framing, TLS, bounds and deadline rules
  remain enforced. Vertex generation and OAuth still reject missing MIME.
- Exercise the public adapter using synthetic SSE lifecycle events. A terminal
  completed response with empty output may assemble only completed output items,
  with contiguous indices, unique nonempty item IDs, a matching created/final
  response ID, and agreement with all observed item/content/text events. No
  synthesized text, usage or model identity. Nonempty final output remains authoritative
  and must agree with streamed items.
- Reject duplicate/conflicting/incomplete items, gaps and wrong indices/IDs,
  response-ID contradictions, text contradictions, events after item/response
  completion, failed/interrupted streams, tools, refusals and malformed SSE.
  Preserve whitespace, reasoning separation, secret-safe failure and no retry.
- Keep optional-metadata and completed-envelope compatibility outside the new
  empty-output path; do not require a full streamed lifecycle for old final-only
  responses.

Validation must use the profile-scoped runner and retain each fresh external
scratch directory. Full pytest, mypy, JavaScript syntax and final diff checks are
required. Independent Standards and Spec reviews remain outstanding and cannot
be self-approved or launched without Adam's explicit authorization. No live calls,
private-draft/Guardian acceptance, Hermes changes, commit or push are part of this
implementation.

## Implementation

`agent_lab/designer/codex.py` changes only the pinned Codex transport and its SSE
parser. Missing MIME proceeds to the existing encoding/framing/body checks;
explicit MIME is still validated. Empty final output uses only indexed completed
items, with response identity, contiguous indices and unique nonempty item IDs.
All observed items and terminal text must agree. Initial text, if supplied, must
be a prefix of the final text. Later events cannot reopen a completed item.
Nonempty final output remains authoritative. No text, usage or model is invented.

The new public-adapter regression module covers both MIME states, empty/nonempty
final output, with/without reasoning and all existing HTTP framing modes, plus
negative lifecycle/identity/text/tool/refusal/secret cases. Older header tests were
updated only where the approved Codex missing-MIME exception changes the expected
stage; Vertex still rejects missing MIME. The durable-failure test now verifies
that missing Codex MIME with an invalid SSE body persists `invalid_response_body`,
without a header observation, retries or Guardian dispatch.

## Execution evidence

All runs use `/home/hermes/.hermes/profiles/astra-pinned/bin/workflow-generator-validation`.
Logs below are retained beneath `/home/hermes/workflow-validation-scratch/`.

- Initial RED: `workflow-generator-20260922T093243Z-TxMD7e/red.log` — **20 failed,
  59 passed in 0.71s**, exit 1. Reproduced both approved incompatibilities and two
  identity gaps, before production edits.
- First focused run: `workflow-generator-20260922T093349Z-985Ezb/focused.log` —
  **4 failed, 499 passed in 15.73s**, exit 1. The failures were older expectations
  that absent Codex MIME must fail at headers; they were updated to the new contract.
- Added-text agreement RED: `workflow-generator-20260922T093609Z-SrSmot/agreement-red.log`
  — **4 failed, 81 passed in 0.57s**, exit 1. Contradictory added message/part text
  was accepted; prefix consistency checks corrected this for both final-output forms.
- Final focused run: `workflow-generator-20260922T095104Z-v4Sucx/focused.log` —
  **509 passed in 21.16s**, exit 0. Command:
  `AGENT_LAB_JUDGMENT=stub .venv/bin/python -m pytest -q tests/test_designer_codex*.py tests/test_designer_response_headers.py tests/test_designer_header*.py --tb=short`.
- Type/syntax/diff gate through `workflow-generator-20260922T094138Z-cvIZSP`:
  `.venv/bin/python -m mypy agent_lab` — **35 source files clean**;
  `node --check agent_lab/designer/static/app.js` and `git diff --check` passed,
  combined exit 0. No separate project lint gate was identified.

### Full regression environment findings

The first complete run, `workflow-generator-20260922T093646Z-iIOwtn/full-pytest.log`,
returned **1,817 passed, 3 skipped, 160 errors in 291.83s**, exit 1. Parsing its
error blocks confirmed **all 160 setup errors** contain Chromium's fatal
`Socket path too long`. The emitted socket path was 128 bytes. This is a different
problem from the resolved evidence-root guard conflict.

A command-local fresh **short sibling directory** under the same approved scratch
root avoids Chromium's socket-path limit. Both the runner-created directory and
short directory are retained. No runner/profile/source guard was modified, no
symlink or HOME disguise was used, and no existing directory was reused or deleted.
The browser probe in `v-MZxOXb/browser-probe.log` passed **1 test in 1.95s**.
Read-only verification confirmed short directories are user-owned `0700`, accepted
by the unchanged production `validate_evidence_root`, with real
`HOME=/home/hermes` and `HERMES_HOME=/home/hermes/.hermes/profiles/astra-pinned`.
An initial verification command used an incorrect import (`designer.storage`),
failed without writes, and was corrected to `agent_lab.designer` after graph lookup.

Reproducible full-run command (run from the repository; retain both directories):

```sh
/home/hermes/.hermes/profiles/astra-pinned/bin/workflow-generator-validation bash -c '
  set -u
  umask 077
  outer="$WORKFLOW_VALIDATION_DIR"
  short=$(mktemp -d -p /home/hermes/workflow-validation-scratch v-XXXXXX) || exit
  export TMPDIR="$short" TMP="$short" TEMP="$short" WORKFLOW_VALIDATION_DIR="$short"
  printf "RUNNER_DIR=%s\nSHORT_VALIDATION_DIR=%s\n" "$outer" "$short"
  AGENT_LAB_JUDGMENT=stub .venv/bin/python -m pytest -q --tb=short > "$short/full-pytest.log" 2>&1
  result=$?
  printf "%s\n" "$result" > "$short/exit-code.txt"
  printf "FULL_LOG=%s/full-pytest.log\n" "$short"
  exit "$result"
'
```

Use a tracked background terminal invocation with completion notification for the
full run: a foreground tool request timed out at 420 seconds despite its requested
600-second timeout. `v-Vx92QG/full-pytest.log` is that **incomplete run**, not a
passing suite; it reached 76% and showed a failure without the terminal summary.
No pytest process remained afterwards.

A subsequent fail-fast full run in `v-byYwpS/full-pytest.log` stopped with
**1 failed, 613 passed, 2 skipped in 120.87s**, exit 1. The unchanged browser test
`test_late_run_response_cannot_restore_invalidated_display[invalid-mode]` exhausted
its short polling loop before `held` was populated. Its isolated rerun passed;
this establishes timing sensitivity, not permission to weaken or silently remove
that test. The browser test and production UI were not edited.

The final complete full run in `v-Ip1U4p/full-pytest.log` returned **1,977 passed,
3 skipped in 467.61s**, exit **0** (also retained in `exit-code.txt`). This includes
the browser suite, without modifying its assertions or timing. The runner's outer
directory is `workflow-generator-20260922T095320Z-Qsg7E1`. The three skips are the
two opt-in live Jev tests and optional real Hermes plugin-loader integration.
This green run does not erase the earlier timing failure or prove it is fixed.
The isolated browser retest is `v-rgnhi7/browser-isolation.log`: 1 passed in 1.67s.

**Implemented and offline-tested, not independently reviewed or accepted live.**
Independent Standards/Spec reviews and separate live acceptance remain outstanding;
no self-approval is claimed. Ticket 19 remains Blocked on review/live acceptance,
and ticket 28 remains unimplemented. Adam subsequently explicitly authorized the
two independent reviews and requested a handoff/local checkpoint commit. That
review authorization carries into the next session; no reviewer model has been
selected and no additional model/worker was launched during this handoff. See the
latest HANDOFF section. Commit authorization is not push or live-acceptance permission.

## Review baseline and unchanged boundaries

The working-tree code/test SHA-256 values (not a commit or independent review):

- `agent_lab/designer/codex.py`: `e1c6699599eded1a05deb61d3cf91797a840fe1a96260dbc8da970c4605907b5`
- `tests/test_designer_codex_compatibility.py`: `442f3f7929a2440aa759c5534938e5c42dcd112e76d959d8aec4d25f27fbf09f`
- `tests/test_designer_response_headers.py`: `18c4b35d714e5550e3505ab946139ec84093248c445edbb00a7f1333463ade71`
- `tests/test_designer_header_observation.py`: `793b0e2b6d53279a405c1be920eeeb01ceefed2131d5dc13fc16d75bc05661a0`
- `tests/test_designer_header_diagnostics.py`: `212cc62923250be899b531145bc5bb40daa0ce3590962bf98e0c6560464bf388`

Graft wiring freshness and final code/test diff whitespace checks passed. Inspection
found only the scoped adapter/tests and documentation changes; fixture identifiers
and credentials are synthetic. Vertex implementation, production evidence guards,
UI, profiles, routes, live credentials, tools and runner remain unchanged. Existing
uncommitted handoff/current/diagnostic work was preserved. No model calls, worker,
private-draft/Guardian acceptance, commit, push or ticket-28 work occurred.
