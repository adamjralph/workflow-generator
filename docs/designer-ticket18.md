# Ticket 18 — controlled read-only source snapshots

Implemented on `main` in `fce3a59`; awaiting user acceptance.
Approved contract: `.scratch/workflow-generator/issues/18-run-role-workflow-with-controlled-data-source.md`.
Approved review baseline: `163c586517c724fcd5c202b92033893956f632f8`.

## Try it

```bash
.venv/bin/python -m agent_lab.designer \
  --evidence-dir /tmp/workflow-ticket18-evidence \
  --source-file /tmp/writing-brief.json
```

The operator-selected JSON file must contain only `request_id`, `text`, and
`evidence_labels`, for example:

```json
{"request_id":"demo","text":"Write a synthetic update.","evidence_labels":["synthetic-note"]}
```

Open the printed exact loopback URL, select **Role workflow (offline fixtures)**,
then select the controlled source. Capture and inspect its input before running
or checking. Explicit recapture is required to observe source edits. Existing
fixture execution and supplied-fixture conformance remain available separately.

## Delivered contract

- `ControlledSource.capture`, `.run`, and `.check` provide the public seams.
- Input is regular-file, strict UTF-8 JSON bounded to 4 KiB, with duplicate and
  extra keys rejected and existing strict writing-brief validation retained.
- Captured bytes are stored under `snapshots/<sha256>.json` in the protected
  evidence destination. Replay verifies the digest and never rereads the source.
- Run evidence uses the actual generated candidate; replay conformance uses the
  independent plain reference and actual candidate for `captured_input`.
- Results carry snapshot attribution; custom execution success remains distinct
  from case-scoped conformance. Missing/corrupt snapshots and source failures fail
  visibly before execution.
- HTTP exposes only a fixed source name and digest, not source-path selection.
  Existing Host/Origin/token and bounded-body protections remain enforced.
- Capture, design and mode changes invalidate stale UI results/responses. Input
  and outputs remain inert text. Source access is read-only; no live calls or
  Hermes changes were made.

## Verification

Incremental red→green implementation at approved public, HTTP, and real-browser
seams added 89 tests (45 public, 12 HTTP/CLI, 32 Chromium).

Final verification after implementation and independent review:

- `.venv/bin/python -m mypy agent_lab`: **26 files, no issues**.
- `AGENT_LAB_JUDGMENT=stub .venv/bin/python -m pytest -q`:
  **1004 passed, 3 expected skips**, including **100 real Chromium tests**.
- Skips: two opt-in live Jev tests and optional real Hermes plugin loader check.
- Full console evidence: `/tmp/workflow-ticket18-full-suite.txt` (temporary).

## Independent review

Both axes reviewed `git diff 163c586517c724fcd5c202b92033893956f632f8...HEAD`
at implementation commit `fce3a59` and independently passed the 89 new tests.

### Standards

No confirmed documented-standard violations. Two optional observations remain:
non-atomic snapshot publication can leave a corrupt entry after interrupted
writes or make concurrent capture fail closed; duplicate-key rejection logic
could be shared across the source and HTTP boundaries. Neither permits corrupted
input to run or pass a check. Crash recovery and concurrent publication remain
robustness limitations, not claimed guarantees.

### Spec

No actionable deviations or scope creep found. Full-suite/typechecking results
above were run after this review, not independently verified by reviewers.

Unrelated pre-existing working-tree changes were not staged or discarded.
