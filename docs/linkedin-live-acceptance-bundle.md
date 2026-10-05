# Minimal LinkedIn live-acceptance bundle

**Status:** proposal for the parent after ticket38; no run or external send starts
from this document. The parent chooses the existing LinkedIn scenario under the
continuing bounded/test-only mandate. Scenario selection does not need a separate
user question. Actual recipient/channel and permissions beyond that mandate do.

## One useful acceptance journey

Use one operator-pinned source with its existing approved read-only capture and
current Generator/Guardian defaults. Privately verify their effective identities in
the preview before paid work; mismatch stops rather than substituting a model. Capture → one Generator draft → one independent
Guardian review → exact offline replay → declared private review packet → deliberately
missing packet repaired once locally → a separately labelled unrepairable packet
fault → one redacted alert to the destination Adam names. Both fault cases are
test-only artifact faults, not claims of a spontaneous editorial defect.

Keep the exact source, draft, review, attribution, usage and immutable evidence
private. All editorial verdicts are completed reviews; policy acceptance is explicit.
`human_decision: required` remains true even for Approved. No post, publication,
source-flag/archive write, production deployment or gate bypass is part of this run.

## Proposed bounds

| Resource | Bound for this one acceptance journey |
|---|---|
| Generation | At most **2** generation HTTP attempts: one existing Codex Generator, one existing Vertex Guardian |
| Authentication | At most **1** existing Vertex token exchange, in memory; Codex reads its existing authorized credential source |
| Provider HTTP | At most **3** POST attempts total: two generation plus one auth; no retry, redirect, model substitution or fallback |
| Per-role runtime | Existing **180-second** local elapsed deadline, including credential read/auth and response collection; at most **360 seconds** of sequential provider-stage local waits for the two roles |
| Response/output | Existing **65,536-byte** role response bounds and **3,000-code-point** post bound; local declared packet limit **1 MiB** |
| Packet remedy | **1** original local output step plus at most **1** repair step, reserved before work; **0** additional generation/auth calls |
| Alert | **1** explicitly requested attempt; proposed **2-second** total local timeout, no automatic resend; current loopback cap is 5 seconds |
| Credits/spend | Existing credits only; no purchase or account change. These are call/local-time bounds, not a hard dollar/token cap or remote cancellation guarantee |

Local artifact/replay I/O has fixed step/byte bounds but no new whole-journey hard
elapsed deadline. The 360-second bound concerns local provider waits; remote work
may continue after local timeout.

The existing adapters make one generation POST each; Vertex's one auth POST is
inside its deadline. Record actual generation/auth starts, configured/resolved
models, elapsed times and provider-reported usage in private evidence. Preserve
unknown token/cost fields as unknown, and label any estimate. Timeout/interruption
is uncertain completion, consumes its reservation, and permits no automatic retry.

Live editorial revision is a **later optional scope**, unnecessary for this minimal
packet-remedy demonstration. If the parent chooses it, the proposed maximum is one
Generator revision and one independent Guardian re-review: **4** generation attempts,
**2** Vertex auth exchanges, **6** provider POST attempts total, the same per-role
bounds and no retry. That requires a concrete runtime implementation/contract and
authorization within the mandate before any call; ticket38 does not implement it.

## Redacted alert contract

Example public portion of an unresolved packet alert:

```json
{
  "event": "workflow.outcome.unresolved",
  "original_run": "<fresh-local-outcome-id>",
  "repair_run": "<fresh-local-repair-id>",
  "status": "exhausted",
  "reserved_steps": 2,
  "step_allowance": 2,
  "terminal": "COMPLETED",
  "expected": {
    "file": "review-packet.json",
    "string_fields": [
      {"field": "scope", "allowed_values": ["copy-only"]},
      {"field": "human_decision", "allowed_values": ["required"]},
      {"field": "verdict", "allowed_values": ["Approved"]}
    ],
    "redacted_string_fields": [
      "snapshot", "run_request", "receipt_digest", "check_digest", "draft_digest", "review_digest"
    ]
  },
  "unmet": [{"code": "missing_file", "requirement": "review-packet.json"}],
  "action": "Inspect saved evidence; no further repair is authorized"
}
```

Ticket37's full envelope also includes the declared field names/byte limit and
local remedy-receipt digest. Exact original source/run/snapshot identifiers and
digests are redacted; fresh local output identities remain. No source filename/path,
draft/review text, original recording identifier/digest, model/profile configuration,
credential, endpoint secret, historical usage or provider response body belongs in
the outgoing alert. Private evidence supplies the detailed diagnosis.

Adam's exact remaining delivery decision: **which channel and exact recipient or
endpoint should receive this one redacted test alert, and which existing authorized
delivery mechanism may send it?** A connected-app grant is needed if that chosen
mechanism is unavailable. Ticket37 supports literal loopback only; external
delivery needs that decision and a bounded implementation/authorized connector.
Acknowledgement establishes transport receipt, not that a human read it.

## Execution and acceptance evidence

First run the mandatory checkout-local environment preflight in [HANDOFF.md](../HANDOFF.md).
The parent can settle bounded test execution/runtime details under the continuing
mandate. Ask Adam only for the actual recipient/channel or a genuinely consequential
change such as new source disclosure, credentials/permissions, credit purchase,
publishing or production writes. Do not re-ask for read-only checks or the already
selected LinkedIn scenario.

Retain actual request-bound recordings, both replay logs, original/repair verdicts,
one alert receipt and explicit human-gate state. Compare attributable baseline/run
measurements only where measured; ticket38 carries historical usage but proves no
savings. Complete browser integration and broader release acceptance separately.
No acceptance claim follows merely from a local fixture, recorded replay or 2xx.
