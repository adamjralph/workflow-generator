# Observe rejected response-header shape

Type: task
Status: resolved

## Approval and baseline

Adam approved the versioned secret-safe schema, persistence and offline public-adapter/durable-failure test seams in this session ("approve"). Baseline: `6149bcf1a4fbb65a5d2b982c2bc62f8dbda7e974`, as retained by the handoff. Ticket 26 stays closed; parent 19 stays open. No live requests or real credential reads are authorized.

## Contract

Add optional `header_observation` to sanitized failures, with `version: 1`, `section_bytes` (including the first CRLF-CRLF delimiter, at most 65536), `field_lines` (nonempty lines following the status line, before metadata discard), and boolean `content_type`, `content_length`, `transfer_encoding`, `content_encoding`. Presence means an exact case-insensitive field name before a colon in that section, not a claim that its value or syntax is valid. Existing failure code and status remain authoritative.

Observe only a complete, within-limit first header section rejected during status/header validation. Missing, incomplete, oversized sections and failures after header acceptance have no observation. No extra reads, arbitrary names, values, hashes, bodies, credentials or exception text are retained. Observation is diagnostic, not a change to acceptance policy. Preserve validation order, limits, request identity, no retries and wire behavior.

Carry observations through Codex and Vertex (generation and OAuth) public adapters, durable failed exchange and receipt/view, and duplicate inspection. Old failures lacking the optional field remain valid and serialize without a new null field. Receipt/replay versions are unchanged. Failed recordings remain ineligible for completed-pair replay.

## Delivery

Adam explicitly accepted ticket 27 ("accept"). This slice is closed. Evidence: `docs/designer-ticket27.md`.
Final offline suite: 1,892 passed, 3 expected skips, including Chromium and completed-pair replay. Mypy: 35 files clean. Independent Standards: no documented violations, one optional readability heuristic deferred. Independent Spec: no blocking deviations; suggested boundary coverage added. No live activity occurred. Implementation and acceptance are being committed separately from unrelated working-tree changes.

## Answer

Accepted: bounded version-1 header observations propagate through public provider adapters and durable failures without changing validation, reads, request identities or retries. Parent 19 remains open. Acceptance does not authorize live execution.

## Validation

Red-first public adapter tests with synthetic credentials and denied real connections/DNS; first-section-only reads, writer closure, field counts including discarded metadata, casing, all presence flags, validation precedence, limits and omitted observations outside the boundary. Public HTTP run plus durable exchange/receipt/duplicate/offline rejection coverage. Strict schema validation at persisted-failure boundary. Independent Standards and Spec reviews, regular mypy, final full offline regression including Chromium. No live test authorization.
