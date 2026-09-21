# 18: Run a role-bound workflow with one controlled data source

**What to build:** Select one approved read-only source in the browser, inspect its captured input, execute the role-bound workflow, and replay that input through conformance checking.

**Blocked by:** 17 — Compose and run one role-compatible workflow (accepted and closed; dependency satisfied).

**Status:** accepted and closed

## Approval and readiness

Adam approved the slice, then explicitly approved the controlled-source and snapshot
contract below ("approve") and the review baseline ("accept"). Ticket 17 is
accepted and closed. Ticket 18 was implemented in `fce3a59` and explicitly
accepted by Adam ("accept"). Evidence: `docs/designer-ticket18.md` (`35b9a5d`).
All acceptance criteria are satisfied: 1004 tests passed, 3 expected skips;
mypy clean (26 files).

## Acceptance criteria

- [x] A user can select the agreed controlled read-only source and inspect the captured input before executing the compatible role-bound workflow.
- [x] Source input is validated against the agreed role input contract; unsupported or invalid input fails visibly before workflow work begins.
- [x] Execution uses the captured input through the existing generated graph and displays outputs and attributable run evidence.
- [x] Captured input can replay offline through the independent plain reference and actual generated candidate, with supplied-case conformance evidence distinct from a successful custom run.
- [x] The bounded snapshot contract defines what was captured and prevents replay from silently rereading changed source content.
- [x] Source failures and missing, invalid, or corrupt captured input cannot appear as successful runs or passing checks.
- [x] Source access is read-only; HTTP cannot select arbitrary filesystem paths, code, credentials, or output roots. Evidence remains under the caller-selected protected root.
- [x] Public-seam, HTTP, and real-browser tests cover capture, execution, replay, source changes, failure behavior, and read-only preservation; offline regression and type checking pass.

## Approved controlled-source and snapshot contract

- **Source:** One operator-selected local JSON file containing a single writing
  brief: request ID, text, and evidence labels, using ticket 17's strict field rules.
- **Browser:** Show a fixed source name, not its path. Capture and preview the
  input before running. The browser cannot select filesystem paths.
- **Snapshot:** Capture once into the protected evidence store with a content
  digest. Runs and conformance checks use the captured bytes, never silently
  reread the source. This is a private input-snapshot format, not a persistent
  public Spec format.
- **Changes:** Source edits require explicit recapture. Recapture invalidates
  previous displayed results and in-flight responses.
- **Limits:** UTF-8 JSON, maximum 4 KiB. Reject extra fields, duplicate keys,
  malformed input, and unsupported file types. Preserve ticket 17's strict brief
  validation without coercion or truncation.
- **Failures:** Missing/unreadable source or missing/corrupt snapshot fails visibly;
  no successful run or passing check is reported.
- **Safety:** No network, URL fetching, model calls, browser-selected paths, or
  source writes. Retain the existing protected evidence root and HTTP boundary.
- **Tests:** Public capture/run/check seams, actual HTTP, and real Chromium;
  independently expected outputs, changed-source replay, corruption, stale
  responses, and read-only preservation. Full offline regression and type checking
  must pass, preserving existing modes and ticket 17's fixed-fixture behavior.

## Approved review baseline

`163c586517c724fcd5c202b92033893956f632f8` (ticket 17 acceptance).
Adam explicitly accepted this baseline. Contract refinement is complete; this
approval establishes implementation readiness, not acceptance of delivered work.

## Boundaries

One controlled source and a bounded snapshot contract only. No arbitrary browser-selected
paths, live integrations, network/model calls, real agent execution, or Hermes writes/activation.
No general connector framework, bulk imports, new runtime, Parallel, Gates, public persistent
Spec format, or packaging. Role compatibility is not permission verification.
