# Offline transport investigation

## Authorization and question

Adam approved this bounded investigation with “yes”: static comparison with the
installed Hermes Codex client, followed by synthetic responses and loopback TLS.
The question is whether a maintained HTTP client can replace the handwritten
transport **without silently changing the approved safety and evidence contract**.
This is not approval for a production replacement or another live request.

Repository baseline: `00807380b120f343780b26f697843dacfe054066`.
Ticket 27 remains accepted and closed; parent 19 remains open.

## Recommendation

**Do not replace the transport with a plain HTTPX streaming client yet.** HTTPX
is a plausible maintained-client candidate, but the tested public response seam
loses information and changes acceptance behavior required by the current contract.
It is not a drop-in replacement, even with explicit safe defaults and MIME checks.

There is still no established cause or remedy for smoke 05. Both transports reject
a synthetic 200 response containing 35 fields without Content-Type. This models
only the known shape, not the unknown live headers, values, body or network path.
ALPN differs locally, but that does not establish a live cause or cure.

A future implementation proposal must first resolve the byte-level observation and
validation boundary: exact first-section size/counts, duplicate singleton headers,
first-section status policy, bounded framing and trailer checks. Do not quietly
weaken these guarantees to accommodate a library. A lower-level interception layer
would require its own feasibility proof and version-pinning plan; it is not tested
or approved here. No additional live retry or diagnostics ticket is recommended
on this evidence alone.

## Narrow static comparison

Installed Hermes source checkout: `5eb99eb2844b22ebb723711b8e6a0bbb80bb5f04`.
Paths below use `H = /home/hermes/.hermes/hermes-agent`. This identifies the inspected
checkout, not the version running during any earlier smoke or proof of a successful
Hermes control. Only the specified source and third-party package trees were read;
no Hermes module was imported or invoked.

- `H/agent/auxiliary_client.py:2767–2794` constructs the auxiliary Codex client
  through `_create_openai_client`; the inspected helper's `:146–188` configuration
  injects a keepalive client and sets SDK retries to zero. This is a bounded look at
  the auxiliary construction path, not every Hermes runtime/provider override.
- `H/agent/process_bootstrap.py:387–444` configures HTTPX with connect/write
  timeouts of 15 seconds, pool timeout of 10 seconds and no read timeout. It can
  select environment proxies and reuse synchronous direct transports. Those
  behaviors must not be copied wholesale into this project's one-attempt adapter.
- `H/agent/codex_headers.py:16–77` uses the same official Codex endpoint family and
  truthful Hermes identity for that endpoint. The project must retain its own
  `WorkflowGenerator/1` and `workflow-generator` identity, not impersonate Hermes.
- Project `agent_lab/designer/codex.py:140–238` uses direct verified TLS, HTTP/1.1,
  `Connection: close`, and no explicit ALPN configuration. Its public invocation
  at `:444–533` adds identity encoding, credential isolation, whole-request deadline,
  aggregate body limit and sanitized worker-boundary failures.
- Installed HTTPX 0.28.1 / httpcore 1.0.9 / h11 0.16.0 were copied to a private
  temporary vendor directory for testing. They are not project dependencies;
  no package was downloaded or installed and project dependency files are unchanged.
  Selection is an ecosystem/library evaluation, not an audit of current releases
  or security advisories.

Relevant installed library sources, relative to the copied `vendor/` directory:

- `httpx/_transports/default.py:279–330`: transport defaults include environment
  trust, HTTP/1.1, HTTP/2 disabled and zero connection retries.
- `httpx/_client.py`: client defaults include environment trust and redirects
  disabled; default request headers include Accept-Encoding and User-Agent
  (`:304–317`). Supply explicit overrides rather than relying on these defaults.
- `httpcore/_async/connection.py:140–147`: TLS advertises `http/1.1` with HTTP/2 off.
- `httpcore/_async/http11.py:44–62,170–238`: 64-KiB read chunks, a 100-KiB incomplete
  event limit, informational-response processing, and body/trailer parsing. The
  incomplete-event limit is not the project's exact 65,536-byte header-section cap.
- `h11/_headers.py:152–210`: equal duplicate Content-Length fields are collapsed;
  Transfer-Encoding is normalized before reaching the HTTPX response interface.

## Probe and safeguards

Temporary artifacts: `/tmp/workflow-transport-study/`:

- `probe.py`: throwaway characterization harness and deliberately incomplete
  HTTPX wrapper; **not production-ready**.
- `results.json`, `probe.log`: 52 loopback TLS observations and one refused-connection
  check with assertions.
- `vendor/`: copied third-party package code, without importing Hermes.
- `source-hashes.txt`: probe and inspected Hermes helper hashes.
- Fresh self-signed test certificates/keys and generation logs, private to this
  directory. These are synthetic TLS fixtures, not application credentials.

Command:

```sh
PYTHONPATH=/tmp/workflow-transport-study/vendor:. PYTHONDONTWRITEBYTECODE=1 \
  .venv/bin/python /tmp/workflow-transport-study/probe.py
```

The certificates expire after one day; later reruns need fresh synthetic certificates
with the same SANs. The artifact directory is temporary, not a committed reproducible
production test package.

The Python audit hook permits only literal IPv4 loopback socket destinations and
binds, denies non-loopback DNS, and blocks opens under the real Hermes and gcloud
credential directories. Guard self-checks confirmed denial before DNS, external
connection or credential-file access. The production credential loader was replaced
with a function that raises if called. Synthetic poisoned proxy/CA environment
values were ignored by the configured candidate. Uppercase and lowercase proxy
variables were set, and both NO_PROXY bypass variables were cleared. No real
environment values or credentials were printed.

The existing `_https` function ran through an injected loopback connection seam;
its host/port were asserted before substitution. Both engines used fresh trusted
local TLS contexts. The original's public adapter was **not** invoked: the harness
provided equivalent outer elapsed-time/body bounds for this transport comparison.
Results such as `LimitOverrunError` are therefore raw transport outcomes, not claims
about public adapter failure codes.

The candidate explicitly sets `trust_env=False` on client and transport,
`retries=0`, HTTP/2 off, redirects off, verified TLS, identity encoding, truthful
client identity, `Connection: close`, and uses `aiter_raw()` to avoid automatic
content decompression. It applies status, duplicate-header and MIME checks and a
65,536-byte collected-body limit. An outer `asyncio.timeout(0.4)` bounds tests;
per-operation HTTPX timeouts alone would not bound a trickling response. This is
not a proposed change to the production 180-second limit.

The synthetic peer verifies the exact UTF-8 payload, byte Content-Length, POST path,
synthetic authorization and truthful identity/encoding headers. Each completed
request case used one TCP connection attempt; redirects and 500 responses caused
no second request. Certificate failures also used one TCP attempt and reached no
application handler. A separate refused-loopback-connection check observed exactly
one TCP attempt with HTTPX. This is bounded retry evidence, not exhaustive coverage
of every failure mode.

## Results

**52 TLS observations plus one refused-connection check; all characterization
assertions passed.** Passing means the observed similarities and differences matched
assertions, not compatibility approval.

Both engines:

- Accepted expected and mixed-case MIME, repeatable Set-Cookie metadata, one-byte
  response fragmentation, and exactly 65,536 body bytes.
- Rejected missing, empty and wrong MIME; gzip Content-Encoding (with an actual
  compressed synthetic payload); duplicate MIME;
  Transfer-Encoding plus Content-Length; a headerless first 200 followed by another
  200; redirects; status 500; and 65,537 body bytes.
- Rejected untrusted certificates and trusted certificates with mismatched hostnames.
- Stopped a slow trickling response at the outer deadline, despite continued input.
- Rejected the synthetic 35-field response with `missing_http_content_type`.

Important incompatibilities:

1. **Equal duplicate Content-Length:** original rejected it; candidate accepted it.
   The library collapses duplicates before the wrapper's `headers.raw` check.
2. **103 followed by valid 200:** original rejected the first section; candidate
   accepted the final response. With missing MIME on the final 200, candidate
   reported missing MIME instead of original first-section rejection. This is
   standard library HTTP behavior, but changes this project's approved policy and
   evidence boundary; it does not explain the recorded first-section 200 failure.
3. **Forbidden Content-Type trailer:** original rejected it; candidate accepted it.
   The public HTTPX body interface did not expose the trailer for project validation.
4. **Header section larger than 65,536 bytes:** original rejected it; candidate
   accepted it. HTTPX streaming does not supply the required exact header-size bound.
5. **LF-only delimiters:** original rejected an incomplete CRLF-delimited section;
   candidate accepted it. Parsing and normalization change syntax policy.
6. **Incomplete header:** both rejected, but with different raw exception types.
   A production proposal needs explicit sanitized failure mappings and precedence.

Compression coverage establishes header rejection before application collection,
not a general decompression/expansion-limit proof. The candidate intentionally uses
the library's raw-byte API and rejects non-identity encoding.

The local TLS server observed no negotiated ALPN for the original and `http/1.1`
for HTTPX on successful connections. Both handled the expected synthetic response.
That establishes only a local configuration/negotiation difference.

HTTPX's parsed response interface cannot reconstruct the exact delimiter-inclusive
first-section byte count, discarded field-line counts or original duplicate fields.
It can also buffer body bytes while parsing headers. Reconstructing a header section
from normalized fields would manufacture evidence and must not replace ticket 27's
raw-section observation contract.

## Verification and review

Mypy: **35 source files clean**, `/tmp/workflow-transport-study/mypy.log`.
Final full offline regression: **1,892 passed, 3 expected skips** in 377.12 seconds,
including Chromium and completed-pair replay. Command:
`AGENT_LAB_JUDGMENT=stub .venv/bin/python -m pytest -q`.
Console: `/tmp/workflow-transport-study/regression.log`. Skips were two opt-in live
Jev checks and the optional real Hermes plugin-loader check. Whitespace checks pass.
Production code, existing tests and dependencies were not changed. This confirms
existing behavior, not integration of the deliberately incomplete candidate.

Independent static Standards review: **0 documented violations**, one optional
assertion-strengthening note. Independent static Spec review: **0 blocking
deviations**, with qualifications about inherited proxy bypass variables, incomplete
outcome assertions, synthetic gzip labeling and incomplete connection-retry coverage.
The probe was strengthened afterwards: controlled both proxy-variable cases and
bypass variables, asserted the remaining outcome types, used actual compressed data,
counted socket connection attempts and added a refused-connection check. The revised
probe passed. Independent follow-up confirmed **0 Standards violations** and
**0 blocking Spec deviations**. Spec suggested optional stronger payload and exact-
code assertions; recorded observations support the current report, and that extra
hardening is deferred for this throwaway study. Reviewers did not execute tests or
independently inspect the installed Hermes source.

## Limits and next decision

This is transport characterization, not a public-adapter, durable-receipt or completed-
pair integration proof for the candidate. Those existing boundaries remain unchanged;
a future replacement needs its own integration tests and independent reviews.
No production remedy, live availability, successful generation, editorial quality,
response author or billing conclusion follows from this investigation.

No live provider/auth requests, credential-content reads, Hermes runtime invocation,
auth repair, smoke-store writes, retries/resumes, staging or commits occurred.
Only loopback test traffic was generated. All five prior live permissions remain
consumed. Preserve all evidence stores, guards and unrelated working-tree edits.
