# Ticket 22 — independent Signal Guardian review

Implementation of the [ticket-22 scope](../.scratch/workflow-generator/issues/22-independently-review-exact-linkedin-draft.md),
not ticket 23's completed-pair replay or parent-ticket acceptance.

## Approved readiness

Adam approved inheriting the ticket-19 authority set and numerical bounds, ticket-22
public test seams, and review baseline `538c1014534d5a4b35eedef604a4bdd398e26559`.
He then explicitly approved pinning the existing authorized-user credential file
`~/.config/gcloud/application_default_credentials.json`. This is Google's credential
file used by Hermes's Guardian, **not** `~/.hermes/auth.json`.
In-memory token acquisition was already approved; no live smoke is authorized.
Acceptance remains Adam's decision.

## Operator use

Use the existing ticket-20 capture manifest and an evidence destination outside
Hermes, this project and source inputs:

```sh
.venv/bin/python -m agent_lab.designer \
  --evidence-dir /your/private/generator-evidence \
  --draft-config /your/operator/capture.json \
  --codex-auth-file ~/.hermes/auth.json \
  --vertex-auth-file ~/.config/gcloud/application_default_credentials.json \
  --vertex-project project-54e16fcb-7c62-4041-bb1 \
  --vertex-region global
```

Those credential paths, project and region are explicit defaults, not discovery
rules. The project matches the statically inspected Guardian configuration; global
is the installed adapter's default. Operators may explicitly override these flags;
no browser-supplied credentials, endpoints or prompts are accepted. Runtime options,
source modes, operation/schema versions and credential-path identity (a digest, not
credential content) are bound to the fresh request. Changed options require a new
explicit request. Captured provider/model changes require recapture.

**Capture**, inspect the complete original source/authority, captured model defaults,
operation versions, limits and evidence destination, then explicitly **Run Generator
+ Guardian**. Recapture and request creation never authenticate or generate. At most
two generation attempts are reserved, one per role, independently of the two-step
workflow budget. No retry, revision, fallback, tool, Hermes session or background
review occurs. A valid Generator draft proceeds to Guardian in the same generated
workflow. Invalid, failed or blocked Generator output prevents Guardian.

Guardian receives the same exact original evidence as Generator (without local
filesystem provenance), plus the exact post and SHA-256 digest of its UTF-8 bytes.
It does not rely on Generator's summaries, support assertions or editorial rationale.
The strict result contains all ten criteria: brand voice, LinkedIn fit, strong hook,
AIDA, source-coherent CTA, supported claims, privacy, reader fit, one-point clarity
and current positioning. Verbatim draft excerpts and source references are checked;
missing support must be explained, not fabricated. Required fixes and optional
preferences remain separate. Criterion findings and verdict must agree.

**Approved**, **Changes requested** and **Blocked** are all completed editorial
reviews. None authorizes publication or scheduling. Guardian never replaces the
submitted copy. Every review says `copy-only` and `Image consistency not reviewed.`
Structural validation does not prove entailment, privacy permission or editorial
quality. Private folder membership grants no public-use authorization.

## Authentication and accounting

The dedicated Vertex adapter reads only the pinned owned regular authorized-user
file, refuses final symlinks, unsafe permissions, oversized/malformed input and
external-account/custom endpoint mechanisms. It makes at most one OAuth POST to
`https://oauth2.googleapis.com/token`, keeps the resulting access token in memory,
then makes at most one tool-free OpenAI-compatible Vertex generation POST. No
Google ADC discovery, credential persistence, SDK auto-refresh, retries, redirects,
environment proxy or Hermes import is used. Authentication requests are separately
reported on success and typed failures; they are not generation calls.

The 180-second deadline includes credential reading and authentication. Auth and
generation envelopes are each limited to 64 KiB. Copy remains at most 3,000 Unicode
code points. These are local bounds, not guarantees of remote cancellation, a hard
provider token cap or capped spend. Both captured model slugs are sent unchanged.
No verified endpoint/model context ceiling is asserted; full authority is never
silently dropped, and provider context rejection fails without a repair call.
Usage and actual provider-reported model/request identifiers are retained when
available. Unknown usage stays null; reasoning/cache counts remain separate.

## Evidence, failures and compatibility

Each opaque request is exclusively claimed and each role reservation is fsynced
before transport. Guardian also requires the Generator transition audit evidence.
Exchanges preserve canonical exact ordered messages, request identity, operation and
schema versions, source mode, limits, execution options, sanitized semantic response,
response digest, usage, auth activity and typed failure. Exchange publication precedes
response application. Credential echoes are rejected, including JSON-escaped echoes;
provider error bodies and secret headers are never stored or displayed.

A version-2 receipt binds the capture, request/claim, both available reservations,
ordered exchange digests, exact draft/review, version attribution and execution log.
The final log must agree with the driver's step count, route and terminal before
completion. Guardian failure retains valid Generator output; storage/audit errors
are uncertain, never editorial approval. Partial files remain inspectable without
retry. Hashes are local integrity bindings, not signatures or proof against an
owner rewriting all records.

Repeated/concurrent submissions return existing status, never new calls. A claimed
request without a valid receipt stays uncertain after restart: no resume, including
no resume from Generator into Guardian. New intentional runs need new explicit
identities and may select the same oldest source; a durable same-capture attempt
warning survives browser/server restart. Sources, processing flags, archives and
Hermes remain untouched.

Legacy request identities and receipts retain their Generator-only behavior and
`not_reviewed` attribution. They are never upgraded into completed pairs. The trusted
Python test seam can still explicitly inject only a Generator fixture to inspect
legacy behavior; it never fills missing fixture roles with live transports. Normal
operator server startup configures both adapters. Completed-pair Check is ticket 23.

## Offline evidence and review

Tests cover strict results through both actual independent drivers; real Codex and
Vertex adapters with injected transports; exact role input, reservation order,
separate step/attempt caps and auth bounds; malformed/blocked/failure stopping;
duplicate/concurrent submissions and interruption; source preservation and
reservation/exchange/log/receipt failures. Actual loopback HTTP and real Chromium
exercise all editorial verdicts, failure/uncertainty, inert text rendering, attribution,
usage, rerun warnings and stale responses. This is fixture evidence, not live model
availability or a real editorial-quality review.

Final full offline suite: **1,472 passed, 3 expected skips**, including real Chromium.
The skips are two opt-in live Jev checks and the optional real Hermes plugin-loader
check. Console: `/tmp/workflow-ticket22-full-suite-final.txt`. Mypy: **33 source
files, no issues**. JavaScript syntax and diff whitespace checks pass. Graft was
refreshed. No production changes followed the final suite.

The first full run found one stale ticket-21 Chromium assertion about the old
one-Generator policy. Updating it to assert the two-attempt, one-per-role policy
passed the focused browser file (14 tests), then the entire suite was rerun above.
No live authentication/model calls or real credential-content reads were used in
implementation tests.

## Standards

Independent review of `538c101...7695153`: **0 documented-standard violations**.
Three optional maintainability heuristics remain deliberately deferred: duplicated
exception sanitization, duplicated JSON duplicate-key rejection, and operation
identity/version/schema data repeated across metadata and declarations. These are
not correctness findings; provider-specific validation and legacy execution remain
explicit. Future cleanup should preserve those boundaries.

## Spec

Independent review: **0 actionable findings**, with 141 focused offline checks
rerun independently across drivers, adapters, HTTP and Chromium. The final policy
assertion update changes no production behavior. Acceptance remains Adam's decision;
live availability is unverified and completed-pair replay remains ticket 23.

**Review summary:** Standards 0 hard / 3 optional heuristics (duplication and metadata
maintenance); Spec 0 actionable. Implementation commit: `7695153`.
