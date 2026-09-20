# Ticket 21 — one Signal Generator draft, explicitly not reviewed

Adam approved ADR 0010, the execution/replay contract, ticket-20 authority inputs,
public seams, numerical limits and duplicate/uncertain handling, then confirmed
using the existing Hermes Codex subscription login read-only. Review baseline:
`f0e0eded07dfe6f7b0d91424a40d46d3ca036da6`.

## Operator use

Use the [ticket-20 capture manifest](designer-ticket20.md). Start the loopback
server with an evidence directory outside Hermes, project and source inputs:

```sh
.venv/bin/python -m agent_lab.designer \
  --evidence-dir /your/private/generator-evidence \
  --draft-config /your/operator/capture.json \
  --codex-auth-file ~/.hermes/auth.json
```

The auth-file option is operator-only; its explicit default is `~/.hermes/auth.json`.
The token file must be an owned regular file, not a symlink. It is not an OpenAI API key: the dedicated adapter reads the existing valid Codex
subscription access token from `providers.openai-codex.tokens.access_token`. The
JWT expiry must be in the future and its account claim supplies the account header.
There is no credential discovery, refresh, lock, repair, quota probe, Hermes import,
Hermes session, auxiliary call or auth/config write. Missing/expired/malformed tokens
require the operator to log in using Hermes separately. Do not paste tokens into
the browser or manifest. Credential content is read only on explicit Run.

Choose **LinkedIn draft capture + Generator**, capture and inspect the exact source,
14 authority texts, model defaults and evidence destination. **Run Signal Generator**
executes that immutable capture, not current source/config contents. A valid draft
is always **Not reviewed**. Other visible outcomes are **Blocked**, **Failed** and
**Uncertain**. No Guardian, publishing, revisions or completed-pair Check exists in
this slice. Ticket 19 remains incomplete.

The provider must be the captured `openai-codex` selection; the captured model slug
is sent unchanged. No substitution is made. One step and one durable model attempt
are reserved before sending, with no retries or repair calls. Local bounds are a
180-second whole-request deadline, 64-KiB complete SSE envelope and 3,000 Unicode
code points in the post. There is no universal provider output-token/spend cap,
remote-cancellation guarantee or claim that local input bounds prove endpoint
context acceptance. Endpoint context rejection fails visibly without retry; no
model-specific context limit is asserted without verified documentation.

The strict JSON response contains `post`, `reader`, `one_point`, `support`,
`limitations`, and `blocked_reason`. A blocked result has `post: null` and a nonempty
reason. Support entries bind exact public-copy claims to a captured filename or
guidance label and a verbatim source quote. Unknown fields, invented references,
invalid shape, overlength copy and en/em dashes fail rather than being repaired.
Structural support validation does not prove entailment, privacy or writing quality.
The request explicitly requires blocking on missing public-use authorization, and
never treats private folder membership as publication permission.

## Execution and evidence boundaries

- `ModelOperation` is explicit on Transform (`model_operation`, operation and schema
  versions). Ordinary callable bindings stay deterministic; Judgment is unchanged.
  Admission checks every declaration, including unreachable ones. Both the plain
  and actual generated drivers independently prepare/invoke/apply. Inspection
  reconstructs the actual owned executable configuration and versions.
- `DraftRuns.create_request(snapshot)` creates an opaque input-bound identity,
  without model work. `run(snapshot, run_request)` executes the real generated
  driver. It takes a trusted Python `ModelSource` injection for offline tests;
  browser clients cannot supply a transport, prompt, path, provider or binding.
- Capture issues the first identity. `POST /api/drafts/request` explicitly issues
  another for the same verified snapshot; `POST /api/drafts/run` submits one.
  Exact loopback Host/Origin/token, strict JSON keys and bounded bodies are retained.
- Private per-request directories contain an exclusive flock, immutable request
  identity and durable claim. Concurrent submissions return running; repeats return
  saved status after evidence integrity checks. Claimed-but-incomplete attempts are
  uncertain after restart, never resent or resumed. An intentional new request is
  distinct. UI warns on same-capture reruns and invalidates stale responses, not work.
  Same-capture warning memory is page-local; request deduplication is durable.
- A fsynced attempt records exact canonical UTF-8 provider request, semantic digest,
  operation/schema version, captured-input digest, source mode, ordinal and limits.
  The digest-bound capture supplies guidance digests and exact instruction inputs.
  Sanitized exact semantic response text, provider metadata and separate input,
  output, reasoning and cache usage are atomically persisted **before** application.
  Unknown usage is `null`, never fabricated zero. No secret headers/auth stores or
  raw provider error text are persisted. Reasoning items are validated but not
  exposed as copy; provider reasoning-token usage remains separate.
- Immutable exchange and run-log records are content-addressed. The receipt binds
  their digests, reservation, result and usage. Invalid responses stay inspectable;
  storage/audit errors cannot become successful results. Failed or uncertain records
  are not completed Generator/Guardian pairs. Hashes are local integrity bindings,
  not signatures, provider authenticity or protection against an owner rewriting
  all evidence. General durable resume/exactly-once remote delivery is not claimed.
- Codex's injectable async byte transport is the external-network seam. Its standard
  library HTTPS implementation has no retry/redirect path; stream framing, reasoning
  lifecycle, tool refusal, secret echoes and usage types are validated. Deadlines
  bound local waiting even across slow credential reads; a late read never sends.

## Offline verification

Tests exercise public admission, both independent drivers, actual candidate
inspection/conformance, real captured runs with fixture/injected Codex transport,
immutable evidence, source preservation, interruption, duplicate/concurrent HTTP,
reservation/exchange/audit/receipt storage failures, literal structured outcomes,
exact-request offline replay, and real Chromium rendering/stale/network failures.
Full completed-pair replay UI remains ticket 23, not a claim of this ticket.

Validation: **1,331 passed, 3 expected skips** in the complete offline suite,
including real Chromium. Skips are two opt-in live Jev checks and the optional
real Hermes loader check. Console: `/tmp/workflow-ticket21-full-suite.txt`.
Mypy: **31 source files, no issues**. Focused ticket-21 checks: **192 passed**.
Diff whitespace checks passed; Graft refreshed. No runtime changes after the full run.

## Standards

Independent review found **0 hard violations** and one optional naming heuristic
(`Source`/`setup`/`RESULT` in temporary-fixture tests). It remains intentionally
deferred; these local fixture names match surrounding tests. The duplicated driver
execution logic is explicitly required by ADR 0010, not an outstanding finding.

## Spec

Independent review identified missing typed failure detail, blanket browser
uncertainty on HTTP rejection, and missing final-symlink protection in auth reads.
Red-first regressions now cover each: whitelisted typed failure code/status in
exchange and receipt, explicit pre-execution HTTP failure versus uncertain missing
response/evidence, and `O_NOFOLLOW` plus current-user ownership on token reads.
Storage that cannot establish whether an earlier request ran remains uncertain;
that is deliberately not mislabeled as known remote failure. Independent follow-up
confirmed all three fixes and **0 outstanding actionable Spec findings**, with
**89 focused tests** rerun. Standards follow-up confirmed **0 hard findings and
0 new heuristics** (one deferred fixture-naming heuristic total).

**Review summary:** Standards 0 hard / 1 optional naming finding; Spec 0 outstanding.
Implementation `3bf1bf9`; review fixes `56438c6`. Ready for Adam's acceptance.

No production source text, real credential content, authentication traffic or live
model invocation is part of the offline evidence. Live availability and post quality
remain unverified; live smoke needs separate approval and a named destination.
