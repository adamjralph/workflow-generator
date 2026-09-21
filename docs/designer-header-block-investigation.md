# Offline response-header block investigation

Adam authorized this investigation after live smoke 04 failed with
`missing_http_content_type`, provider status 200. Baseline:
`6149bcf1a4fbb65a5d2b982c2bc62f8dbda7e974`. This is investigation only, not approval
for implementation, relaxed validation, new diagnostics or another live run.

## Method and results

Exercised public Codex and Vertex adapters with synthetic credentials and response
bytes: Codex generation, Vertex generation and Vertex OAuth; 16 response shapes;
whole-buffer, one-byte and seven-byte asynchronous delivery. All 144 cases
completed with real socket connections and DNS denied. Synthetic credential bytes
remained unchanged. Results were identical across provider phases and fragmentation
sizes. Existing response-header tests: 247 passed.

- Normal headers, lowercase/mixed-case Content-Type names and metadata preceding
  Content-Type: accepted.
- Absent Content-Type or an extra blank line before it: `missing_http_content_type`,
  status 200. The first blank line terminates the HTTP header section.
- A synthetic `200 Connection established` block followed by a complete response,
  or a second 200 response following a headerless 200: the same missing-type failure.
  These are characterizations, not valid reasons to skip arbitrary 200 blocks.
- Informational 100 or 103 before a final response: `provider_rejected` with status
  100 or 103. The adapters do not advance through informational responses. A 101
  response is likewise rejected; protocol switching must not be treated as an
  ordinary informational response to skip.
- LF-only headers: `transport_incomplete`; leading blank line: `invalid_http_status`;
  whitespace before the field colon or folded fields: `invalid_http_header`.

Artifacts: `/tmp/workflow-header-block-investigation.py`,
`/tmp/workflow-header-block-investigation.json`,
`/tmp/header-block-existing-tests.txt`.

## Code interpretation

`agent_lab/designer/codex.py:136–229` and
`agent_lab/designer/vertex.py:218–316` read through the first CRLF-CRLF delimiter,
parse that block's status and fields, and require status 200. `header_field` in
`agent_lab/designer/http_response.py:23–29` lowercases field names. Content-Type is
not in the discarded metadata allowlist. Fragmented delivery did not drop fields
in these cases.

Both transports use direct TLS `asyncio.open_connection`; their request is POST,
not CONNECT, and the shown implementations contain no environment-proxy resolver.
A synthetic CONNECT-style preamble therefore does not demonstrate that a proxy
was involved in the live exchange. No live network route was inspected.

## Conclusions and next decision

No demonstrated framing bug explains smoke 04. It remains established only that
the header block parsed by the adapter had no Content-Type field. Existing stored
evidence cannot recover raw response headers or identify the body format.

The lack of 100/103 handling is a separate compatibility limitation; its observed
failure category/status does not match smoke 04. Fixing it should not be presented
as a remedy for that smoke. Skipping arbitrary 200 blocks, accepting a missing
Content-Type or sniffing a body is not justified.

Recommend agreeing a more informative but bounded observation contract before any
new live attempt. Potential fields are header-block byte/field counts and booleans
for fixed framing fields (Content-Length, Transfer-Encoding), never raw values,
arbitrary field names, credentials, bodies or exception text. The precise schema,
persistence surface and public regression seams require approval before adding it;
any live execution would still require separate fresh permission and destination.
No production code or tests were changed, no live/model/auth requests or real
credential reads occurred, and all smoke stores and guards remain untouched.
Ticket 26 remains accepted and parent 19 remains open.
