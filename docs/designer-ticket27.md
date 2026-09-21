# Ticket 27 — rejected response-header observations

Implemented against retained baseline `6149bcf1a4fbb65a5d2b982c2bc62f8dbda7e974` after Adam approved the observation schema, persistence and offline public test seams ("approve").
Contract: [ticket 27](../.scratch/workflow-generator/issues/27-observe-rejected-header-shape.md).
Adam explicitly accepted ticket 27 ("accept"); it is closed.
Ticket 26 stays closed and parent 19 stays open.

## Behavior

Codex generation, Vertex generation and Vertex OAuth now attach an optional
`header_observation` to failures rejecting a complete, within-limit first HTTP
header section. Version 1 contains:

- `section_bytes`, including the first CRLF-CRLF delimiter (maximum 65,536);
- `field_lines`, counting nonempty lines after the status line before metadata discard;
- `content_type`, `content_length`, `transfer_encoding`, `content_encoding` booleans.

A presence flag means an exact case-insensitive field name before a colon. It does
not certify valid syntax or values. Existing failure codes and parsed status remain
authoritative. Invalid status/header syntax, duplicate fields, representation
rejections and provider status rejections retain their original precedence.

Missing, incomplete or oversized sections have no observation. The observation
boundary ends before framing/body processing. No additional reader calls are made;
body bytes and second sections are not inspected for diagnostics. No raw header
names, values, hashes, bodies, credentials or exception text are persisted.

The typed observation survives the public adapter worker boundary, failed exchange,
receipt/view and duplicate inspection. Historical failures remain valid and omit
the optional field rather than gaining a null. Request identities, receipt/replay
versions, limits, request wire format, validation policy and no-retry behavior are
unchanged. Failed recordings remain ineligible for completed-pair replay.

## Verification

Red-first evidence:

- `/tmp/t27-red1.txt`: three public-adapter failures for absent observation, then
  `/tmp/t27-green1.txt`: three passing cases after transport/adapter propagation.
- `/tmp/t27-red2.txt`: 21 durable HTTP/receipt failures for missing propagation,
  then `/tmp/t27-green2.txt`: 271 passing header/adapter/durable cases.
- `/tmp/t27-boundaries.txt`: rejected-schema test exposed Pydantic's acceptance of
  boolean `True` as literal version 1; an explicit integer validator fixes it.
  The same run exposed a test expectation mismatch: empty Codex SSE already means
  `transport_incomplete`, not `invalid_response_body`; existing behavior was retained.
- `/tmp/t27-focused.txt`: 315 passing focused tests before review additions.
- `/tmp/t27-boundaries-final.txt`: 56 passing observation tests, including review-
  suggested exact 65,536/65,537-byte boundaries and whitespace-prefixed names.

Public adapter tests deny real socket connections and DNS, use synthetic credentials,
check unchanged credential bytes, first-section-only reads, writer closure, discarded
metadata counts, all four flags, precedence and omission outside the boundary.
Durable HTTP tests verify exchange/receipt equality, redaction, duplicate retrieval
without resending and offline rejection of incomplete pairs. Historical serialization
and strict observation validation are covered through the public failure model.

Final full offline regression: **1,892 passed, 3 expected skips**, including real
Chromium and completed-pair offline replay, in
`/tmp/workflow-ticket27-full-suite-final.txt`. The skips are two opt-in live Jev
checks and the optional real Hermes loader. An earlier full run passed 1,883 tests;
the final run includes nine review-suggested boundary cases. No production or test
changes followed the final full regression.

Mypy: **35 source files clean**, checked during implementation and after final code
changes (`/tmp/t27-mypy-final.txt`). JavaScript syntax and whitespace checks pass.
Graft refreshed. No production changes followed independent review.

## Standards

Independent review: **0 documented violations; 1 optional low-priority test
readability heuristic**. Positional expected presence flags could become a named
mapping. Deferred: literal expected values are independently asserted, and the
suggestion does not affect correctness. Static review only.
Report: `/tmp/ticket27-standards.md`.

## Spec

Independent review: **0 blocking deviations**. Reviewer independently ran all
47 observation tests then present. Suggested inclusive-limit and exact-name tests
were added afterwards; all 56 observation tests pass. Main agent owns full suite,
Chromium and typechecking evidence. Report: `/tmp/ticket27-spec.md`.

## Limits and next decision

This is instrumentation, not a fix or diagnosis for smoke 04. It can distinguish
zero fields from fields lacking Content-Type, but cannot identify the response
author, prove a bot rule, recover a body or establish successful generation.

No real credential-content reads, live provider/auth requests, production captures,
retries/resumes, credential repair, protected source/Hermes writes or smoke-store
changes occurred. All four prior live authorizations remain consumed. A new live
attempt requires separate fresh permission and a new private evidence destination.
Keep request identity unchanged; an A/B experiment needs separate authorization for
multiple requests. Implementation and acceptance are committed separately from
unrelated changes; local handoff/map and investigation reports remain unstaged.
Acceptance changed documentation only; verification above was not rerun.
