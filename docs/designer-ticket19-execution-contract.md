# Ticket 19 — approved execution and replay contract

**Status: approved for the ticket 21/22/23 breakdown.** Adam approved all outstanding
contract decisions and ticket-21 public test seams, then confirmed proceeding with
the existing Hermes Codex subscription login read-only. Ticket-21 review baseline:
`f0e0eded07dfe6f7b0d91424a40d46d3ca036da6`. The approved authority is ticket 20's
complete manifest set. Codex defaults to `~/.hermes/auth.json`, with an explicit
operator-only `--codex-auth-file` override; no credential discovery or refresh.
No live smoke is authorized. This approval is not completion of tickets 19, 22 or 23.

Originally requested by Adam while refining
[ticket 19](../.scratch/workflow-generator/issues/19-refine-and-review-oldest-linkedin-draft.md).
This is a bounded extension of the existing execution/checking core, not a new
runtime or an authorization to make live calls during planning.

**Approved provider adjustments:** after reviewing the
[static provider findings](designer-ticket19-provider-feasibility.md), Adam explicitly
approved retaining both profile defaults, two generation calls maximum with no
retries, local response-size/time bounds without remote cancellation or capped-spend
claims, and Vertex token acquisition in memory only. The previously proposed hard
4,096-token ceiling is withdrawn. This approves those adjustments, not an implicit
model substitution, Hermes write, live smoke test or all remaining ticket decisions.

## 1. Explicit model-backed operations

Keep the five node kinds. For this slice only, permit a Transform to bind to an
explicit **model operation**, distinct from its existing deterministic callable
binding. See accepted [ADR 0010](adr/0010-explicit-model-operations-and-offline-replay.md).
This deliberately amends the no-model Transform restriction; it must not be
implemented as a network call hidden inside an ordinary callable.

A model operation has three parts:

- **Prepare:** deterministic validated state → immutable role request.
- **Source:** one request → recorded model response or typed failure.
- **Apply:** deterministic validated state + validated response → next state/outcome.

Only the source can contact a model. The source explicitly identifies its mode as
live, recorded, or fixture. The reference and generated drivers independently
schedule steps and invoke these parts. Shared request/schema/validation helpers
are allowed; neither execution driver delegates its control flow to the other.

The authored operation key and generated execution configuration distinguish
model operations from deterministic ones. Admission rejects ambiguous, unbound,
wrong-state or unsupported bindings, including unreachable declarations, before
any source is invoked. Actual-candidate inspection and conformance compare the
operation identity/version and request/apply contract, not just a display label.
Candidate response application is actually executed, not replaced by stored final
state or by the reference implementation.

This ticket supports exactly two registered operations, `draft_linkedin` and
`review_linkedin`, not arbitrary browser-authored prompts, plugins or executable
bindings. Existing deterministic Transforms and restricted Judgment keep their
current behavior. Guardian's editorial verdict is structured response data, not
an expansion of Jev's Intervention vocabulary or a publication Gate.

## 2. Live run

Shape: Generator → Guardian → completed. Generator may instead stop blocked.
One step is reserved before each operation using the existing run accounting;
the authored workflow budget is two steps. A separate per-run model-attempt cap
is two. Both constraints are enforced, not equated implicitly.

1. Validate the entire captured input, guidance set, operation versions, destination,
   and configured model selections before paid work. Show these in the preview.
2. Claim the run request durably and exclusively in the protected artifact store.
3. Prepare the Generator request. Append its durable attempt reservation before
   sending. Perform at most one provider generation request; retries, tool calls,
   fallback models and auxiliary background work are disabled.
4. Persist the sanitized response exchange before applying it. Validate strict
   output structure, source references, limits and allowed outcomes. Invalid
   responses do not trigger a repair call. A valid blocked result stops the run.
5. For a valid draft, derive its exact digest and prepare the Guardian request
   from the original captured article/authority and that exact draft. Generator
   summaries are optional navigation, never substitutes for original evidence.
6. Reserve/send/record/validate Guardian's one response. Bind its verdict to the
   draft digest; persist the final artifacts and completion receipt.

`Approved`, `Changes requested`, and `Blocked` are valid completed Guardian reviews.
Only Approved means editorial approval, within the stated scope; none authorizes
publication. A Generator blocked result is stopped-before-review, not a fabricated
completed pair. Provider, validation, storage or audit errors produce failed or
uncertain execution, clearly distinct from an editorial verdict.

### Approved limits

- At most two generation requests per run, at most one per role; no automatic retry.
- No universal hard output-token or monetary ceiling is promised. Use provider
  output/reasoning parameters only where their semantics are verified; record the
  effective options and any unavailable cap. Do not send an unsupported cap and
  retry without it. Both configured profile defaults remain selected.
- 180-second wall-clock deadline per request; timeout is uncertain remote
  completion and never refunds the attempt allowance.
- Strict response envelope, bounded to 64 KiB; post body at most 3,000 Unicode
  code points. Overlength is visible failure, never silent truncation.
- Inputs retain ticket 19's file/total-byte limits. Check known provider/model
  context limits with a documented output allowance where applicable; never silently
  drop authority text. Local size validation is not proof of endpoint acceptance.

The two-call ceiling is not a monetary guarantee. Local deadline and response-byte
limits bound what the application waits for/collects, not remote token generation,
remote cancellation or spend. Usage may be unknown on failure. Adapters must enforce
local bounds and no-retry behavior; unavailable provider caps are disclosed, not
fabricated or substituted with a different model.

### Model and credential boundary

Resolve each profile's configured provider/default at capture. Record that
non-secret selection and use it for the captured run; deliberate changes require
recapture. Record provider-reported resolved model identity where available and
never invent one. A profile default is configuration, not permission to launch
an autonomous Hermes agent session.

Use a tool-free provider adapter with credentials available through an explicitly
approved read-only mechanism. Vertex may acquire an access token in memory using
an explicitly configured credential source; no discovery fallback, saved token,
credential-file update or Hermes-state write is permitted. Bound authentication
traffic separately, disable its retries, and record its occurrence without secrets.
It is network activity but not a model-generation call. The enclosing deadline
includes token acquisition. Codex uses an existing valid token read without refresh,
locks, recovery or persistence; expired/missing credentials require operator action.
Do not launch Hermes sessions, write usage into Hermes databases, or modify profile/
config/skill/auth files. No credentials, authorization headers, full provider config
or secret URLs enter snapshots, browser results or logs. Any provider path requiring
protected writes fails with an operator-action message.

The configured OpenAI Codex and Vertex adapters still require read-only feasibility
verification before implementation readiness. No model substitution is authorized.

## 3. Exchange evidence

Each exchange contains:

- Private format version; logical operation ID, ordinal and operation version.
- Captured-input and guidance digests, provider/model selection, instruction and
  output-schema versions, effective non-secret request options and limits.
- Exact ordered role messages and their digest, plus the sanitized response body
  and its digest (or typed failure). No truncation of recorded semantic inputs.
- Draft digest for the Guardian exchange, strict parsed result, and source mode.
- Actual provider request ID/model metadata when supplied; reported input, output,
  reasoning and cache usage separately. Unknown remains unknown, not zero.

Use deterministic canonical JSON encoding for request identity: UTF-8, sorted
object keys, compact separators, no NaN; preserve array order and text exactly.
Identity includes request-affecting options, not secrets or transport timestamps.
Record invocation/run attribution and elapsed time separately from semantic
request identity so fresh offline replay does not require the original run ID.

Persist exact replayable response content in immutable digest-addressed records.
Publish complete records atomically; never use an incomplete file as a response.
A completion receipt binds the input bundle, operation versions, exchanges, draft,
review, usage provenance and execution log. Partial/uncertain records cannot be
upgraded to a completed receipt by omission or guessing.

Hashes provide local integrity/binding, not signatures, provider authenticity,
proof that guidance was obeyed, or proof that a file owner cannot rewrite history.

## 4. Offline replay and conformance

The Check action never has live credentials or access to a live transport. It:

1. Validates the input bundle, completion receipt, expected operation versions,
   all referenced digests and exchange ordering before executing.
2. Constructs independent, fresh recorded sources for the plain reference and
   actual generated candidate. Shared mutable replay cursors are rejected; neither
   source may fall back to network or filesystem source discovery.
3. Runs both drivers with the captured initial state. Each driver independently
   prepares its request. A recorded response is supplied only for the exact
   operation/ordinal/request digest (including Guardian's exact draft input).
4. Revalidates the recorded response, applies the real operation and compares
   structure, state, routes, budgets and deterministic event/log evidence through
   the existing conformance mechanism. Wrong/missing/duplicate/unused exchanges,
   altered request preparation, altered application and candidate drift fail.
5. Reports case-scoped conformance with fresh reference/candidate evidence and
   attribution to the original input/recording. It does not report two new paid
   calls, re-bill historical usage, or imply a new Guardian review happened.

Live timestamps, network latency and provider request IDs are transport provenance,
not values regenerated for equality by the checker. Their stored integrity stays
bound by the receipt; semantic exchange identifiers and response content participate
in the deterministic execution evidence. The two fresh replay logs must agree;
there is no claim that a live wall-clock log equals a replay log byte for byte.

A recorded run can replay exactly without proving that the post is good. Guardian
review, driver conformance and Adam's final decision remain separate.

Failed/uncertain live attempts remain inspectable but cannot be submitted as a
successful completed-pair recording. Failure semantics are tested through fixture
and recorded-failure cases, without declaring a failed live run successful.

## 5. Duplicate submissions and interruption

The server issues an opaque run-request identity bound to a captured input.
Submission claims it exclusively before any attempt. Concurrent/repeated HTTP
requests with that identity return running, the existing result, failed or
uncertain; they never repeat paid work. Reject reuse with different input.

An intentional new run requires an explicit new request. It may select the same
oldest draft: source eligibility is unchanged and the receipt is not a processing
flag or hidden skip list. The browser warns when the same capture has already run.

Persisted reservation without a complete response after interruption is uncertain.
Restart does not resend it, resume into Guardian, or replenish the allowance.
There is no exactly-once remote delivery or general durable workflow resume claim.
An operator can explicitly start a new run after inspecting the uncertainty.
A disconnect or UI recapture invalidates display state, not evidence, and does not
imply the remote request was cancelled or unpaid.

## 6. Public acceptance evidence

Extend ticket 19's proposed seams with literal offline fixtures demonstrating:

- A source-aware operation is admitted/inspected distinctly; ambiguous or hidden
  live binding cannot enter the supported designer mode or a conformance check.
- Two live-adapter invocations at most, reserved first; generator failure prevents
  Guardian; timeout, malformed result and audit failure never retry or claim success.
- Guardian sees original evidence plus the exact draft; wrong draft binding fails.
- Independent plain/candidate request preparation and response application execute;
  altered candidate behavior fails even with an otherwise valid recording.
- Missing, corrupt, reordered, duplicate, wrong-request or unused exchanges fail;
  network-denying replay passes without loading credentials.
- Duplicate/concurrent submissions and restart after an incomplete reservation do
  not issue new model calls. New explicit runs do not alter `processed` or ordering.
- Provider errors and unknown usage remain visible; credentials never appear in
  stored artifacts or browser output; all protected source/profile files unchanged.

These are approved requirements, not claims that the entire ticket-19 workflow is
implemented. Ticket 21 delivers one Generator attempt and not-reviewed output;
Guardian and completed-pair Check remain separate slices.
