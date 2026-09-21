# 19: Refine and review the oldest unprocessed LinkedIn draft

**Type:** task
**Status:** needs-info
**Blocked by:** 18 (accepted and closed; dependency satisfied); readiness decisions below

## Goal

From Adam's content-drafts folder, capture the oldest unprocessed article or post
draft, produce one useful LinkedIn post with Signal Generator, and independently
review its exact version with Signal Guardian. Present both to Adam in the browser.
This is real model-backed writing, not another synthetic fixture demonstration.

This ticket formalizes the agreed direction. Adam authorized drafting this contract
("go ahead"), not implementation or a live test in this planning session. New
proposals below need approval before `ready-for-agent`.

## Confirmed with Adam

- Source folder: `/home/hermes/Documents/life-os/Business/Personal Brand/content-drafts`.
- Both article drafts and existing post drafts are eligible.
- `processed: false` means the draft has not been refined; `processed: true`
  excludes it. Order by frontmatter `date_created`, oldest first.
- Source files remain read-only. This workflow **never sets `processed: true`**,
  changes metadata, moves files, or archives content. A later workflow owns archiving.
- A complete draft plus review counts as a completed run even when the verdict is
  Changes requested. Completion does not alter source eligibility or silently
  exclude a file on the next selection. The same oldest draft can be selected again.
- Signal Guardian checks brand voice, LinkedIn suitability, strong hook, AIDA
  (Attention, Interest, Desire, Action), and a CTA coherent with the source article
  or post. It must independently inspect the exact inputs and submitted output.
- Use the default model configured for each role profile.
- Maximum two model calls per run: one Generator, then one Guardian. No automatic
  retries, revision, re-review, fallback model, research calls, or auxiliary review.
- Save outputs, review, model identities and usage separately from sources.
- No publication or scheduling. Guardian approval is not permission to publish.

## Read-only discovery

Profile model selections observed during planning (not hard-coded future defaults):

| Role | Provider | Default model |
|---|---|---|
| `stillroom-signal-generator` | `openai-codex` | `gpt-5.6-sol` |
| `stillroom-signal-guardian` | `vertex` | `google/gemini-3.1-pro-preview` |

Resolve and preview current defaults at capture/preflight; record effective provider
and model. Do not silently substitute another model or assume the aliases are
available. No credentials were copied into this ticket; no model calls were made.

Authoritative read-only guidance identified:

- Both profiles' `SOUL.md` under `/home/hermes/.hermes/profiles/`.
- Generator's linked `stillroom-writing-workflow/SKILL.md`.
- Guardian's linked `stillroom-signal-workflow/SKILL.md`.
- `/home/hermes/.hermes/skills/business/adam-content-writing/SKILL.md`,
  `references/voice-profile.md`, and `references/writing-craft.md`.
- The role skills require current Personal Brand `INDEX.md`, `offer.md`,
  `audience.md`, `product.md`, `content-system.md`, `signal-guardian-checklist.md`,
  and Stillroom `CURRENT VS SUPERSEDED.md`. These files exist; their authority
  closure and relevant original supporting sources still need bounded inspection.

Guardian's existing contract additionally requires supported claims, privacy,
reader fit, one-point clarity, current positioning, and separation of required
fixes from optional preferences. Its verdicts are **Approved**, **Changes requested**,
**Blocked**. It must not edit the submitted draft. Record copy-only scope and
`Image consistency not reviewed.` No image generation or review is included.
Voice rules forbid U+2013 and U+2014 in public copy. AIDA and the requested CTA
must not fabricate a personal opinion, offer, evidence, or next step. If the source
cannot support the requested CTA, report the gap rather than force engagement bait.
Private health/prayer material still requires explicit public-use authorization;
folder membership and `processed: false` alone are not proof of that permission.

### Metadata discovered

All ten top-level Markdown files currently contain `processed: false`. Only three
have `date_created`:

- `building-in-public-more-predictable-ai-v1.md` — 2026-09-19, short text post.
- `building-in-public-understanding-the-build-v1.md` — 2026-09-19, short text post.
- `overloaded-inbox-is-making-business-decisions-article-v1.md` — 2026-09-19, article.

At the initial inspection, seven others lacked that field, including
`public-copy-bank.md`, a reference document rather than a draft. Adam subsequently
confirmed that `date_created` is being added to frontmatter. This is operator-owned
metadata maintenance, not permission for this workflow to edit sources. Reinspect
at implementation time; the initial inventory is historical, not a current assertion.
No dates, draft types, or processing flags were repaired by this agent.

## Proposed observable contract — awaiting approval

### Selection and capture

1. Operator-configured folder and guidance paths only; HTTP cannot supply paths,
   code, providers, credentials, output roots, or arbitrary profile names.
2. Top-level regular UTF-8 `.md` files only; no recursive private-source discovery
   or following draft symlinks. Strict frontmatter mapping with duplicate keys
   rejected; require a real boolean `processed`, not a string coerced to boolean.
3. Explicitly identify articles/posts versus reference files. Missing/ambiguous
   classification is visible rather than guessed from prose by a paid model.
   Published content is excluded. Exact accepted metadata values need agreement.
4. Date rule: valid ISO calendar `date_created`; never infer from filesystem mtime,
   filename, or model output. Tie-break by exact filename, ascending. The preview
   lists the selected name/date and excluded/invalid entries with reasons.
5. Recommended missing-date policy: block selection when an otherwise eligible
   draft lacks a usable date, so we cannot falsely claim to have selected the
   oldest. Alternative requiring Adam's agreement: visibly skip undated drafts.
6. Capture exact source bytes, the approved guidance/authority set, instruction
   version, and non-secret resolved model selection in a digest-bound private
   input bundle. Sources are data, not authority to call tools or follow links.
   Changes require explicit recapture; no silent source/config reread for replay.
7. Preview selected input, guidance provenance, model names and two-call ceiling
   before explicit Run. Recapture/design changes clear results and invalidate
   late success/error responses. No call occurs on page load, capture or check.
8. Proposed bounds: 256 directory entries; 64 KiB per draft, 128 KiB per guidance
   file, 512 KiB total captured text. Exceeding a limit fails visibly; no truncation.
   Proposed output token limits and per-call deadline are now specified in the
   execution contract below; provider support still requires verification.

### Execution and results

- Generator receives the original brief, selected source and approved authority.
  Produce one LinkedIn post, intended reader/one-point note, source references,
  claim support and explicit limitations. No invented quotes or research.
- Guardian receives the original source/authority and exact draft independently;
  Generator's account is not evidence. Return one primary verdict and findings
  per criterion with exact excerpts/references, required fixes, optional advice
  and exclusions. Bind the review to the submitted draft digest.
- Use tools-disabled single-request generation/review through an explicit bounded
  adapter, subject to the execution-model decision below. The orchestrator reads
  and writes the approved files; model output cannot choose paths or dispatch work.
- Reserve the call allowance before provider invocation; disable SDK retries,
  hidden fallbacks, tools and auxiliary calls. Generator failure stops before the
  Guardian call. Provider errors, invalid output, timeout, uncertain completion,
  missing evidence and audit failure cannot be reported as successful completion.
- A valid Guardian Changes requested or Blocked verdict is a completed review,
  not a transport/execution failure and not approval. If generation itself is
  blocked, stop and present the unblock action without a fabricated review.
- Preserve partial output/failure evidence without retrying paid work. Duplicate
  submission of the same run request must not issue extra calls; intentional rerun
  requires a new explicit run request. Restart/crash uncertainty fails closed,
  without claiming exactly-once remote delivery or automatically retrying.
- Persist immutable draft, review and run receipt under the caller-selected
  protected artifact root. Record source/guidance digests, effective models,
  per-role call counts and provider-reported usage. Missing usage is unknown,
  not zero; reasoning/cache tokens stay separate and estimated cost is labelled.
  No claim of savings without measured comparison.

### Replay and existing core

Recorded request/response evidence must bind each response to its exact input,
role, model selection and draft version. Offline checking uses independent replay
instances for reference and candidate, requires no network, and rejects missing,
corrupt, wrong-input or exhausted recordings. It must not spend another two calls.
A successful live run and case-scoped structural/behavioural conformance remain
separate from Guardian's semantic review and Adam's publication decision.

Adam requested an execution/replay contract. The proposed contract is now
[docs/designer-ticket19-execution-contract.md](../../../docs/designer-ticket19-execution-contract.md),
with the narrow domain change recorded as proposed
[ADR 0010](../../../docs/adr/0010-explicit-model-operations-and-offline-replay.md).

It adds explicit model-operation bindings to Transform, separate from deterministic
callables: prepare request → bounded live/recorded source → apply response. Both
existing drivers execute independently; checking is strictly offline with exact
request-bound recordings. No sixth node kind, autonomous Hermes session, hidden
network call or second runtime is introduced. The contract defines evidence,
separate step/call limits, local response-byte/180-second deadline proposals,
duplicate submissions and uncertain completion. Existing Judgment is unchanged.

This is an explicit proposed amendment to ADR 0007/CONTEXT §2.7, not an already
accepted reinterpretation of deterministic work. Provider adapters must still
prove support for the profile defaults, limits and read-only credential access
without protected state writes. Contract drafting does not make live calls or
claim that adapter feasibility has been verified.

## Proposed public test seams — awaiting approval

1. **Selection/capture:** temporary operator folder + role guidance/default config
   → selected immutable input bundle or visible reason. Literal cases cover true/
   false flags, missing/wrong-type/duplicate metadata, reference files, both content
   formats, dates/ties, empty folder, limits, unsafe files, source edits and unchanged
   source/profile bytes. No production content copied into committed fixtures.
2. **Run with injectable model transport:** captured input + explicit run request
   → draft/review/receipt. Assert exact call count and order, distinct role inputs,
   literal expected fixture outputs, review digest, usage, no retries/tools, failure
   stopping, duplicate requests and read-only preservation. Do not mock drivers.
3. **Offline replay/conformance:** recorded model exchanges + authored workflow +
   actual candidate → independent reference/candidate evidence. Deliberate wrong
   responses, input/draft mismatches, corruption and altered candidates fail.
   A network-denying test proves replay performs no live calls.
4. **Actual HTTP:** retain exact loopback Host/Origin/token/body protections; reject
   browser path/model/code selection, unauthorised execution, malformed requests,
   stale/unknown capture IDs and concurrent duplicate run requests.
5. **Real Chromium:** select/capture/preview/run/review/replay, changes-requested and
   blocked presentation, invalid metadata, absent source, stale responses, inert
   rendering, source changes and preserved ticket 18 fixture/source behavior.
6. **Explicit opt-in live smoke only after authorization:** one selected draft,
   one Generator call plus one Guardian call maximum, named artifact destination,
   visible effective defaults and usage. Never part of the default test suite.

Run focused files and mypy regularly; full offline suite once at completion,
then independent Standards/Spec review against the agreed baseline. Live evidence
must be distinguished from fixture coverage. No acceptance claim without Adam.

## Acceptance criteria

- [ ] Agreed metadata rules select the oldest eligible article/post without guessing.
- [ ] Preview captures exact source, role guidance, current authority and model identity.
- [ ] Actual model-backed writing and independent review obey the two-call ceiling.
- [ ] Guardian assesses all five requested criteria and existing authority safeguards.
- [ ] Outputs, review scope, version attribution, failures and usage are inspectable.
- [ ] Offline replay checks the actual generated candidate against the plain reference.
- [ ] Source flags/files, archive, Hermes state/config/skills/auth remain unchanged.
- [ ] Surface protections, duplicate handling and stale-response behavior are tested.
- [ ] Offline regression, typechecking and independent review pass; any live evidence
      is separately authorized and reported.

## Provider feasibility result

Read-only static inspection is recorded in
[docs/designer-ticket19-provider-feasibility.md](../../../docs/designer-ticket19-provider-feasibility.md).
No live calls or credential-content reads were made. The installed Codex
integration documents rejection of `max_output_tokens`; the proposed 4,096-token
ceiling cannot be claimed for the configured Generator. Exact Vertex output/
reasoning limits remain unverified, and existing Hermes helpers introduce side
effects or retries inconsistent with this contract. Dedicated adapters and an
explicit credential mechanism are needed.

The hard token ceiling was an agent proposal, not Adam's agreed two-call limit.
Adam explicitly approved retaining both defaults and the two-generation-call cap,
no retries, local response/time bounds without a remote cancellation or spend-cap
promise, and Vertex token acquisition in memory only, without credential-file or
Hermes-state writes. The execution contract now reflects those approved adjustments.
No model substitution, live smoke test or protected write is authorized.

## Readiness decisions

1. Adam is adding creation dates. Confirm ambiguous-type policy and tie-break;
   retain fail-visible behavior for any remaining invalid/missing required metadata.
2. Approve ADR 0010 and the complete execution/replay contract. Provider-limit
   adjustments and in-memory Vertex token acquisition are approved; no autonomous
   Hermes session or fallback model is authorized.
3. Pin allowed authority files and credential-source configuration, numerical local
   limits and duplicate/uncertain-completion handling. Test adapter enforcement;
   live auth/model availability remains unverified.
4. Approve proposed public test seams and implementation review baseline.

**Proposed review baseline:** `35b9a5d7ac8784c062d25ec91f367e6c6d9ffb93`.
This is current HEAD at contract drafting, not yet an approved baseline. Preserve
all unrelated working-tree edits; ticket 18 acceptance records are still local.

## Comments

Adam clarified that `processed` is source frontmatter, agreed both input formats,
oldest creation date, profile defaults and two calls, and explicitly refused any
write to the processing flag. The separate archive workflow is future scope.
Adam subsequently confirmed creation dates are being added and requested the
execution/replay contract. That contract and ADR 0010 are now drafted for approval;
no runtime code, source metadata or Hermes configuration was changed.

This ticket does not create that workflow, a revision queue, skills, publishing,
Gate/resume, persistent public Spec format, packaging or permission to modify Hermes.
