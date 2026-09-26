# Bug report: Codex live generation stops at response-header validation

> **Resolved — historical record.** The two incompatibilities described here were
> diagnosed and corrected on 2026-09-23; the bounded live Generator → Guardian pair
> later completed with a passing offline Check and was accepted with ticket 19. Read
> [codex-protocol-diagnosis.md](docs/codex-protocol-diagnosis.md) and
> [codex-compatibility-correction.md](docs/codex-compatibility-correction.md) for the
> remedy. Nothing below is a current blocker or a live-call authorization.

## Current triage — 2026-09-22 (superseded by the resolution note above)

The incident remains open. Five historical live attempts are now recorded; the
older four-attempt snapshot below is retained as historical evidence. Smoke 05
(`0080738`) returned HTTP 200 / `missing_http_content_type` after about 1.11 seconds,
with 35 header field lines and no Guardian invocation. It did not establish root cause.

Adam has chosen to keep Codex Generator and Vertex Guardian. A separate synthetic
DeepSeek connectivity observation is not a replacement workflow or a fix. Fresh
Codex/response-header tests: **329 passed in 2.25 seconds**; full regression remains
blocked by this session's temporary evidence-root policy. Current findings and the
bounded next experiment proposal: [provider triage](docs/provider-triage-2026-09-22.md).
See [CURRENT.md](CURRENT.md) for current status and permissions; do not execute old
smoke scripts or infer a new paid-request allowance from this report.

## Summary

Four separately authorized live smoke attempts stopped at the Codex Generator,
preventing the workflow from reaching Vertex Guardian or completed-pair offline
Check. The latest attempt failed with `missing_http_content_type` and provider
status **200** after approximately **1.29 seconds**.

The immediate rejection is known: the adapter found no Content-Type field in the
first HTTP header block it parsed. The underlying cause is **not established**.
Raw response headers and bodies were deliberately not retained.

**This is not evidence of a Vertex failure.** No live Vertex Guardian or Vertex
authentication request occurred in these smokes. Vertex is covered offline but
remains unverified live.

## Repository state

- Latest implementation commit: `6149bcf1a4fbb65a5d2b982c2bc62f8dbda7e974`.
- Ticket 26 is accepted and closed; delivery: `docs/designer-ticket26.md`.
- Parent ticket 19 remains open; complete live execution and editorial quality are
  unverified.
- There are unrelated working-tree changes and local planning files. Inspect
  `git status`; do not blanket stage, reset, clean or discard changes.
- Read `AGENTS.md` and consult Graft before source exploration. `HANDOFF.md` has
  current state and historical details; its newest entries supersede older ones.

## Intended workflow

1. Capture the oldest eligible local draft and explicit guidance, read-only.
2. Generate one LinkedIn draft through Codex.
3. Independently review the exact draft through Vertex Guardian.
4. Run completed-pair Check offline using recorded exchanges.

Configured models at capture:

- Generator: `openai-codex / gpt-5.6-sol`.
- Guardian: `vertex / google/gemini-3.1-pro-preview`.

At most two generation attempts are permitted, one per role, with no retries,
repair or fallback. Authentication activity is separately accounted for. Nothing
is published, and source/Hermes state must not be modified.

## Observed live attempts

Each row describes a separate explicit authorization and a fresh request, not an
automatic retry. All authorizations are now consumed.

| Smoke | Commit | Recorded Generator failure | Provider status |
| --- | --- | --- | --- |
| 01 | See private evidence | `invalid_response` | Not established here |
| 02 | `31d408b` | `invalid_http_headers` | 200 |
| 03 | `1e5e8e8` | `unsupported_http_content_type` | 200 |
| 04 | `6149bcf` | `missing_http_content_type` | 200 |

Do not assume all four failures had the same cause. Diagnostics changed between
attempts, and historical evidence cannot recover discarded response headers.

### Latest attempt

Private evidence directory: `/home/hermes/workflow-evidence/live-smoke-04`.

- Snapshot: `3e5adad869b53850a889fcb7a9c24e1a9b96b629ab714953e14c7b0a86991ba7`.
- Request: `049eaba17b53cb02f98966d6a4ecd99e1d213d7c044b412590050e53adb5c006`.
- Selected draft: `20-years-to-get-here-first-post.md`, dated 2026-09-08.
- Nine eligible entries and one excluded entry.
- Selected source, all 14 guidance files and default model selections were unchanged
  from smoke 03.
- One generation attempt reserved; zero recorded auth requests; usage unknown.
- No valid model output, copy, Guardian review or completed-pair Check.
- Snapshot/receipt digests and receipt/view equality verified.
- Inspected source/guidance bytes unchanged; evidence private and owned.

Read `SMOKE.md`, `run-view.json`, `timing.json` and `verification.json` there first.
`capture-view.json` and immutable run records contain private source/guidance;
avoid dumping or sharing them unnecessarily. Earlier evidence is under sibling
`live-smoke-01`, `live-smoke-02` and `live-smoke-03` directories.

**Do not execute `execute_once.py`, remove `execution-guard.json`, resume requests,
or modify any existing smoke store.**

## Relevant code and behavior

Spans below refer to commit `6149bcf`:

- `agent_lab/designer/codex.py:136–229`, `_https`: direct TLS connection to
  `chatgpt.com:443`, POST `/backend-api/codex/responses`, HTTP response parsing.
- `agent_lab/designer/codex.py`, `CodexSource.invoke`: existing credential loading,
  request transport, bounded response parsing and sanitized worker boundary.
- `agent_lab/designer/vertex.py:218–316`, `_https`: analogous HTTP parsing used by
  Vertex generation and OAuth; relevant for comparison, not an observed live failure.
- `agent_lab/designer/http_response.py:23–29`, `header_field`: validates syntax and
  lowercases field names. Content-Type is not discarded as repeatable metadata.
- `agent_lab/model_operation.py`, `ModelFailure`: fixed diagnostic allowlist.
- `agent_lab/designer/draft_runs.py`, `DraftRuns`: one-shot reservation, exchange,
  receipt and failure propagation.

Both provider transports currently:

1. Read through the first `\r\n\r\n` delimiter.
2. Parse its status line and require status 200.
3. Validate headers, rejecting malformed syntax and disallowed duplicates.
4. Require Content-Type: Codex expects `text/event-stream`; Vertex expects
   `application/json`.
5. Validate content encoding and body framing before model response parsing.

Media types are compared case-insensitively. Absent and entirely empty fields have
separate diagnostics; other mismatches use `unsupported_http_content_type`.
Parameters after the first semicolon remain ignored by explicit ticket-26 policy.

The implementations inspected use direct TLS POST, not CONNECT, and do not contain
an environment-proxy resolver. This does not establish the actual live network path.

## Offline investigation already performed

Report: `docs/designer-header-block-investigation.md`.

At `6149bcf`, 144 synthetic public-adapter cases exercised Codex generation,
Vertex generation and Vertex OAuth with whole-buffer, one-byte and seven-byte
asynchronous delivery. Real socket connections and DNS were denied; credentials
were synthetic and unchanged.

Findings:

- Valid headers, lowercase/mixed-case field names and metadata preceding
  Content-Type were accepted. Fragmentation did not lose fields.
- A genuinely absent Content-Type or an extra blank line before it yielded
  `missing_http_content_type`, status 200.
- Synthetic `200 Connection established` followed by a complete response, or a
  headerless 200 followed by another response, yielded the same failure. This
  reproduces a signature, **not the live cause** and not evidence of a proxy.
- Informational 100/103 responses preceding a final response yielded
  `provider_rejected`, status 100/103. The adapters do not advance past them.
  This compatibility limitation has a different signature from smoke 04.
- 101 was rejected. LF-only headers yielded `transport_incomplete`; leading blank
  lines yielded `invalid_http_status`; folded fields and whitespace before the
  field colon yielded `invalid_http_header`.

Local artifacts, if still present:

- `/tmp/workflow-header-block-investigation.py`
- `/tmp/workflow-header-block-investigation.json`
- `/tmp/header-block-existing-tests.txt`
- Earlier MIME characterization: `/tmp/workflow-content-type-investigation.py`
  and `/tmp/workflow-content-type-investigation.json` (records pre-ticket-26 behavior).

Current response-header regression: **247 passed**.
Ticket-26 full offline regression: **1,836 passed, 3 expected skips**, including
real Chromium and completed-pair replay. Mypy: **35 source files clean**.
Console: `/tmp/workflow-ticket26-full-suite-final.txt`.

These are recorded results, not a new verification run for this report. Passing
synthetic tests does not prove live provider compatibility.

## Questions for independent investigation

1. Is there an overlooked request-construction, TLS, HTTP parsing or response
   interpretation defect that could explain the observed missing-field/200 result?
2. Are the synthetic transport fixtures masking behavior of the actual connection?
3. Does existing non-secret evidence support any cause beyond the rejection itself?
4. If new observation is necessary, what minimum fixed, secret-safe metadata would
   discriminate hypotheses without retaining raw headers, bodies or credentials?

Please distinguish confirmed defects, reproduced signatures, hypotheses and
missing evidence. Do not propose unrelated compatibility fixes as a demonstrated
remedy for smoke 04.

Potential diagnostic additions previously discussed—but **not approved for
implementation**—include bounded header-block byte/field counts and booleans for
fixed framing fields. Their schema, persistence and public test seams need agreement.

## Safety and authorization boundaries

This report is for independent investigation. It does not authorize a live request,
real credential-content read, credential repair, implementation or validation-policy
change. Obtain fresh explicit permission for such work as applicable.

- Preserve all four failed stores and consumed execution guards unchanged.
- Do not read real Codex/Vertex credentials to investigate offline.
- Do not import/run Hermes runtime flows that might refresh credentials or mutate
  authentication, configuration or profile state.
- Do not skip arbitrary 200 blocks, accept missing types, sniff bodies or add
  JSON/HTML fallback based on speculation.
- No retries/resumes, model substitutions, publication or protected writes.
- Any future live observation needs explicit authorization, a new private destination
  and an agreed secret-safe observation contract.
- HTTP 200 does not prove generation succeeded, usage was zero or nothing was billed.
- Keep private source/guidance and any discovered secrets out of reports and logs.
