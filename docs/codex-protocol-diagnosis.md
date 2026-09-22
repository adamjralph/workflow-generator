# Codex protocol diagnosis — two demonstrated adapter incompatibilities

**Implementation update:** the approved correction is now implemented and
offline-tested; see [compatibility correction](codex-compatibility-correction.md)
for 1,977 passed / 3 expected skips, frozen code/test hashes and remaining review/
live-acceptance gates. The diagnosis below is historical evidence; its environment-
blocked and unimplemented status statements no longer describe the current state.

## Conclusion and decision

At source baseline `3224103e06a7963cccdc44a64b992ada1e3ed984`, three fresh,
synthetic requests returned HTTP 200 and SSE events reporting exact model
`gpt-5.6-sol` and exact output `OK`. The observed blockers are:

1. The response lacks `Content-Type`. Production `_https` rejects it with
   `missing_http_content_type` before reading the body
   (`agent_lab/designer/codex.py:175–177`).
2. The third response's `response.completed.response.output` is an empty list,
   despite a completed assistant message in `response.output_item.done`.
   Production `_parse` requires exactly one message in final `output` and raises
   `ValueError` at `agent_lab/designer/codex.py:374–386`. The second response also
   failed the parser; its failing line was not captured.

These are demonstrated incompatibilities between the current client contract and
this endpoint's observed stream. They are not evidence that the account/model is
unavailable. They do not identify which server/intermediary omitted Content-Type,
prove a provider-wide contract, or retrospectively establish every historical
smoke's response body. Production correctly enforces its current strict contract.

**Correction scope approved by Adam** in response to this diagnosis (“Approve”).
The approved direction is the narrowly scoped Codex-only compatibility change
below, not a transport rewrite or model replacement. The decision bullets below
record the proposed boundaries that approval covers; do not re-ask for generic
scope approval. No implementation has started. **Blocked on the required
validation environment**, whose mandatory scratch remains inside `.hermes`.
The following requirements must be encoded and tested in a permitted runtime:

- Decide whether this pinned HTTPS Codex endpoint may omit Content-Type while
  retaining rejection of empty, duplicate or explicitly wrong Content-Type and all
  status, encoding, framing, TLS, size and deadline checks. This is an explicit
  exception, not generic content sniffing or silent MIME acceptance.
- Decide whether a completed response with empty final output can use validated
  `response.output_item.done` items. Require terminal completion, consistent
  response/item identities and indices, no duplicate/conflicting items, exact text
  agreement and explicit unsupported-tool/refusal/malformed-stream failures.
  Nonempty final output must still agree with streamed items. Do not fill gaps in
  failed, interrupted or contradictory streams.
- Before implementation, freeze regression seams for both cases and their negative
  boundaries. Preserve secret-safe error/evidence behavior and Vertex's existing
  contract. Do not treat a diagnostic structural reconstruction as a production fix.
- Arrange a permitted validation runtime: current mandatory scratch is inside
  `.hermes`, which project evidence guards reject. Full regression and required
  independent reviews remain prerequisites; neither is waived by this diagnosis.

No production/test code or acceptance contract changed. Ticket 19 remains Blocked;
ticket 28 remains unimplemented. No further live experiment is needed merely to
repeat these observations. A real private-draft/Guardian acceptance run is separate.

## Authorization and experiment bounds

Adam's continuation authorization at the top of `HANDOFF.md` explicitly permits
necessary synthetic diagnostic model calls, private sanitized header/bounded-body
inspection and widened investigation within safety limits. Existing edits to
`CURRENT.md`, `HANDOFF.md` and `docs/codex-alpn-comparison.md` were preserved.

Exactly three sequential requests were sent, one connection per request, each
reserved in a fresh private directory before dispatch. No retries, redirects,
Guardian, delegated worker, supported-client invocation, private draft, profile
edit, auth refresh or credential repair. Each used the existing production
read-only credential loader for `~/.hermes/auth.json`. No token/account value was
printed or persisted by the probes.

Per request: 180-second deadline, 65,536-byte header bound, 8,192-byte decoded body
sample bound and 4,096-byte chunk-line framing bound. TLS certificate and hostname
verification remained on; default ALPN and truthful `WorkflowGenerator/1` /
`workflow-generator` identity were unchanged. Direct POST endpoint:
`https://chatgpt.com/backend-api/codex/responses`.

Exact synthetic JSON (same payload as the earlier ALPN comparison):

```json
{"model":"gpt-5.6-sol","instructions":"This is a synthetic connectivity test. Do not use tools. Reply with only OK.","input":[{"role":"user","content":[{"type":"input_text","text":"Reply with only OK."}]}],"tools":[],"store":false,"stream":true}
```

The probes used the same request framing as production. They replayed the received
first header section into an isolated copy of production `_https` with an in-memory
connection to establish its rejection without a second network request. Reading
past rejection happened only in the diagnostic probe; production was untouched.
This is not full public-adapter or workflow execution.

Response bytes stayed in memory. Persisted summaries use fixed header-value enums,
fixed event/phrase vocabularies and booleans. Cookie values, IDs and arbitrary
provider text are never retained. Probe 03 additionally retained a **sanitized
structural derivative**, with unknown keys/string values replaced by neutral labels
and non-allowlisted numeric fields replaced by zero. It is not an actual provider
response, replay evidence or model-generated deliverable. It exists only for local
offline characterization. Raw headers/body were not saved.

## Actual observations

All three responses:

- HTTP 200; 35 header fields; Content-Type, Content-Length and Content-Encoding
  absent; Transfer-Encoding exactly `chunked`.
- Allowed server enum `cloudflare`; Set-Cookie present; no observed cf-mitigated,
  WWW-Authenticate or Location field. This does **not** establish a Cloudflare bot
  challenge or responsibility for omitted MIME.
- Decoded body 6,290 bytes, terminating zero chunk observed within the sample cap.
  Diagnostic code stops at that zero chunk; it does not validate trailers or claim
  complete production framing acceptance.
- Nine parsed SSE JSON objects, including `response.completed`; exact `OK` in
  `response.output_text.done`; requested model reported, no other reported model.
  No HTML marker or parsed error object in the bounded sample.
- `missing_http_content_type` from unmodified production header logic.

Individual probes:

1. Header/body characterization: 2,641 header-section bytes, 1.530 seconds.
   Strict SSE parser was not exercised on this request.
2. Strict-body-parser discrimination: 2,649 header-section bytes, 1.545 seconds.
   Production `_parse` rejects the actual in-memory body with `ValueError`.
3. Parser location and structural retention: 2,647 header-section bytes,
   1.613 seconds. Actual in-memory `_parse` fails at line 386. Sanitized derivative
   retains empty final output and one completed streamed message at output index 0.
   Its allowlisted usage fields report 32 input / 5 output / 37 total tokens,
   zero reasoning tokens and zero cached input tokens. This is request 03 only;
   aggregate usage/cost for all three is unknown, not zero.

This progression was diagnostic, not retry-until-success: body characterization
revealed a second question; parser testing revealed a second failure; the final
probe located it and retained sufficient sanitized structure for offline work.
The missing instrumentation in probe 02 necessitated probe 03; future capture
probes should record sanitized source-frame locations on their first parser pass.

## Offline causal isolation and verification

Before each invocation, synthetic preflight assertions passed for cookie/identifier
omission, existing missing-MIME rejection, chunk decoding, the body cap and SSE
summary classification. These are focused assertions, not a comprehensive probe
security audit or project suite.

The final offline reproduction forbids socket creation, DNS and connection helpers:

```sh
PYTHONPATH=. .venv/bin/python "$TMPDIR/workflow-codex-offline-reproduction.py"
```

Actual output, exit 0:

```text
PASS: sanitized live structure reproduces production _parse:386 rejection.
PASS: changing ONLY synthetic final output to streamed done item lets unmodified parser accept.
PASS: contradictory synthetic final output remains rejected; network denied throughout.
```

The counterfactual only changes the sanitized synthetic fixture's final output to
its already-completed streamed item. The unmodified parser then returns exact
`OK`, exact requested model, 32 input tokens and 5 output tokens. This isolates
empty final output as the parser barrier in the derivative; it is **not** a passing
live parse, implemented aggregation algorithm or completed workflow.

Fresh existing tests:

```sh
AGENT_LAB_JUDGMENT=stub .venv/bin/python -m pytest -q tests/test_designer_codex.py tests/test_designer_response_headers.py
```

**329 passed in 2.25 seconds, exit 0.** This confirms current contract behavior,
not compatibility with the rejected responses. Graft freshness check passed.
Full regression was not rerun because the already-reproduced validation-root
conflict persists. No independent review, new full-suite/typecheck claim, commit,
push or publication. The diagnosis and proposed exception require review/decision.

## Private artifacts and integrity

All artifacts below are beneath
`/home/hermes/.hermes/profiles/astra-pinned/cache/scratch/` and may be pruned after
72 hours. Result directories use mode 0700; result/derivative files mode 0600.
Each live probe consumes its own exclusive directory guard. **Do not rerun an
invocation or reuse/remove its guard.** Results were read back after execution.
The repo retains this sanitized evidence report, not the private captures.

Probe commands used `PYTHONPATH=. .venv/bin/python "$TMPDIR/<probe>" --invoke`.
Probe-to-destination mapping:

- `workflow-codex-body-probe.py` → `workflow-codex-body-diagnostic-01/`
- `workflow-codex-body-parser-probe.py` → `workflow-codex-body-diagnostic-02/`
- `workflow-codex-parser-location-probe.py` → `workflow-codex-body-diagnostic-03/`

SHA-256:

- Probe 01: `f54337b8d712c6cddca47999d9c7d8a7d843a9eafebe66146d9cba3242183be9`
- Probe 02: `a6ab16e1663524f9d03046b5113ca05ba749cdba2e92b45e3c45966701afed87`
- Probe 03: `2dcf2a01e9e76bb88b25fb5b1f44a0f32d1ed9b1e17b701f828521230dcb7905`
- Result 01: `e93f426a2b62995f414009c0113d34c4deb4090c1048720fd631b3834dbd52f6`
- Result 02: `e531172f6e0c9f199fc95f27208bf8ec10d7e3a3cd8a87122dc3d7e950a22afc`
- Result 03: `50ba9b039546f91bbf7a978581bc7b5aa28c6624aea3234e56f4aa6e260bb719`
- `workflow-codex-body-diagnostic-03/sanitized-structure.json`:
  `21e102c27483a4c0fedc40c6cb9bfc9524a9d38d98a56d3509a8b21910c4ee02`
- `workflow-codex-offline-reproduction.py`:
  `5738d5611fe7c62b2900881b5d9cf220e766d7de017a71963206b790cabafcc2`
