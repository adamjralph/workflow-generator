# Independent investigation: Codex 200 response without Content-Type

Baseline: `6149bcf1a4fbb65a5d2b982c2bc62f8dbda7e974`.
Status: investigation only; root cause remains unresolved.

## Correction to the initial report

The initial version overstated several conclusions. This revision supersedes its
claims that the peer was proven to be Cloudflare, all three earlier smokes showed
an absent Content-Type, SDK requests were proven successful, and all adapter
framing defects were eliminated. It also withdraws the ranking of a bot/edge rule
as the leading cause. The evidence does not support those conclusions.

ALPN is a concrete implementation difference, not a demonstrated cause or fix.
No identity substitution or live A/B experiment is authorized by this report.

## Confirmed observations

Smoke 04 recorded `missing_http_content_type`, provider status 200, about 1.29
seconds elapsed, one reserved generation attempt, and unknown usage. No completed
Generator output, Guardian request, or completed-pair Check followed. The earlier
investigation read its sanitized views and recorded verification results; this
continuation did not reread private smoke records or independently reverify their
digests.

In `agent_lab/designer/codex.py:136–229`, `_https` reads the first CRLF-CRLF-delimited
header section and checks its status and fields before consuming the body.
`missing_http_content_type` at lines 169–171 means that this parsed section lacked
a `content-type` key. It does **not** mean that the section had no other headers,
that the response body was empty, or that a second HTTP response existed.

`header_field` (`agent_lab/designer/http_response.py:23–29`) lowercases field names.
Content-Type is not discarded as repeatable metadata. A malformed, duplicate,
empty, or unsupported Content-Type has a different diagnostic when reached in the
validation order. No field-loss defect was found in this path. This is narrower
than proving the entire request, transport, and live environment correct.

## Historical diagnostics are not equivalent

- Smoke 02, `31d408b`: `invalid_http_headers`, status 200. This broad diagnostic
  could indicate field syntax, duplication, content type, or content encoding.
  It does not establish absent Content-Type.
- Smoke 03, `1e5e8e8`: `unsupported_http_content_type`, status 200. Absence, an empty
  value, an unexpected media type, and media-type case differences were possible.
- Smoke 04, `6149bcf`: `missing_http_content_type`, status 200. Absence in the parsed
  section is specifically established.

A common cause is possible but not demonstrated. Ticket 26's case normalization
was not established as a live remedy; that does not invalidate the separately
accepted offline implementation or prove the earlier response had the same shape.

## New offline characterization

Continuation artifact: `/tmp/codex-offline-followup.py`.
Executed with `PYTHONPATH=. .venv/bin/python /tmp/codex-offline-followup.py`.
All five cases passed their assertions. DNS and real connection entry points were
patched to fail; `asyncio.open_connection` supplied synthetic StreamReader/Writer
objects. The probe called `_https` directly and did not load credentials or run
Hermes. It is transport characterization, not a public-adapter or real-TLS test.

1. A 200 section with zero fields: `missing_http_content_type`, 200.
2. A 200 section with Date, Content-Length, and Connection but no Content-Type:
   the identical diagnostic and status.
3. A headerless 200 followed by a complete second response: the identical failure.
4. A 103 section followed by a 200 response: `provider_rejected`, 103.
5. Mixed-case expected media type with a two-byte Content-Length body: accepted
   by the transport. This is not an SSE semantic-output validation test.

All failing cases made only one reader call, `readuntil`, and closed the writer.
The request writer was captured: one POST to the expected path, correct header/body
separator, exact UTF-8 body preservation, and Content-Length measured in bytes
rather than Unicode characters. No request-framing defect was found in this test.

The earlier investigation recorded **268 passed** for
`tests/test_designer_response_headers.py` and
`tests/test_designer_header_diagnostics.py`; that suite was not rerun in this
continuation. The prior 144-case fragmentation investigation is described in
`docs/designer-header-block-investigation.md`.

## TLS and reference-client evidence: what it does and does not show

The adapter configures direct TLS, hostname verification, and SNI for chatgpt.com.
It sends POST, not CONNECT, and contains no environment-proxy resolver. Under the
normal default transport, reaching the header parser implies that the TLS handshake
completed using the process's configured trust. It does not independently identify
the live peer, certificate chain, DNS answer, intermediary, or application that
produced the response.

Earlier local inspection found no proxy environment settings or hosts-file override
in the inspected locations. Those were current, partial observations, not proof of
the historical network path or an exhaustive trust-store audit. Filename/text
searches do not reliably exclude custom certificate authorities. Firewall commands
with suppressed errors do not prove that no interception rules exist.

The inspected Hermes logs showed client creation and some failures; socket listings
showed connections. Neither establishes a successful equivalent Codex generation,
its negotiated HTTP version, or its response headers at the smoke time. Hermes is
an implementation comparison, not a verified successful control for this incident.

The adapter does not call `set_alpn_protocols`. The inspected installed httpcore
source (`_async/connection.py:146–147`) advertises `http/1.1` when HTTP/2 is disabled.
The earlier loopback probe selected no ALPN with the adapter-style default context.
These observations establish a configuration difference. They do not demonstrate
that the provider rejects absent ALPN, that it requires HTTP/2, or that adding ALPN
would fix smoke 04. No-ALPN HTTP/1.1 is not inherently evidence of a malformed client.

Other static differences include truthful harness identity, optional session/cache
headers, compression preferences, connection reuse, and empty-tools serialization.
Actual SDK settings may vary; optional compression modules and call-specific
arguments prevent treating static defaults as a captured wire request. No evidence
shows that `workflow-generator` is an invalid or blocked originator. Do not pretend
to be Hermes or another client to test an unsupported allowlist theory.

## Hypotheses still open

- A response from the provider or an intermediary genuinely lacked Content-Type.
- A request/TLS characteristic influenced the response returned.
- An unexamined live-environment or transport interaction differs from fixtures.

None can currently be ranked confidently. Content-Type absence alone is not proof
of an HTTP protocol violation: HTTP can carry responses without it, while this
adapter deliberately requires the expected representation type. A bot challenge,
empty body, successful generation, or zero billing cannot be inferred.

Informational 100/103 handling is a separate compatibility limitation. Its known
failure signature differs from smoke 04. Synthetic CONNECT-style 200 blocks can
reproduce the failure but do not establish that CONNECT or a proxy was involved.

## Proposed next decision: observe the existing rejection point

Before another live attempt, agree a small versioned observation contract. The
minimal proposed fields, derived only from the already-read first section, are:

- header-section byte count, including its delimiter, bounded by the existing limit;
- total field-line count before discarding repeatable metadata;
- presence booleans for Content-Type, Content-Length, Transfer-Encoding, and
  Content-Encoding;
- existing failure code and parsed status.

These could distinguish zero fields from multiple fields lacking Content-Type.
They would **not** identify the response author, prove a bot rule, recover the body,
or separate every network hypothesis. Counts can disclose limited metadata and
still require explicit schema and persistence approval. No arbitrary field names,
values, header hashes, bodies, credentials, or exception text should be retained.

The original proposal to count CRLF-CRLF delimiters until connection close is
withdrawn. The adapter stops at the first section; reading further would change
failure-time behavior, require separate bounds, and might inspect body bytes.
A CRLF-CRLF sequence in a body is not proof of another HTTP header section.
TLS metadata would be a separate, optional scope, not necessary for the minimal
header-shape question.

If approved, implement and test diagnostics offline at public adapter and persisted
failure boundaries, preserving validation order, limits, no retries, and redaction.
Then obtain separate authorization for one new live attempt and a new private store.
Keep request identity unchanged initially so instrumentation is not confounded with
a behavioral change. An A/B experiment necessarily involves separately authorized
requests; it cannot be folded into a one-request authorization.

## Continuation boundaries

This continuation made no external network, provider, model, authentication, or
credential-content request. It changed only this report and a synthetic probe under
`/tmp`; production code, tests, existing smoke stores, and guards were untouched.
Previous broad searches and temporary output are not an independently verified
privacy audit; this revision makes no blanket certification of the earlier session.
All four prior smoke authorizations remain consumed. Parent ticket 19 remains open.
