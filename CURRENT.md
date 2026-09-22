# Current project state

Updated 2026-09-22 after Adam authorized triage, closure of finished tickets and routine pending decisions, while reserving decisions assessed to need his direct approval.

**Start here for current status.** `HANDOFF.md` retains historical session evidence; old “next” instructions do not override this file. `ROADMAP.md` defines capability completion, not ticket authorization. The delivery map's P-identifiers are not issue numbers.

## Latest implementation — Codex correction offline-tested, reviews outstanding

See `docs/codex-protocol-diagnosis.md`. Three authorized synthetic requests returned
HTTP 200, exact reported `gpt-5.6-sol` and exact streamed `OK`, but lacked
Content-Type. At the diagnostic baseline, production rejected that header;
diagnostic parsing exposed a second incompatibility: a completed streamed message
with empty final `response.output`. The third actual body failed `_parse:386`.
Network-denied offline characterization
reproduces this with a sanitized structural derivative; changing only its final
output to the done item makes the existing parser accept. This is not live
workflow acceptance or a production change.

**Adam approved the correction scope** with “Approve”: a narrowly scoped
Codex missing-MIME exception and validated completed-item assembly, preserving
all other validation/evidence boundaries described in the diagnosis report.
Do not re-ask for this scope approval. Adam subsequently explicitly authorized
necessary safe work to unblock the environment and get the system working,
while preserving Hermes. This is not a remaining user-permission question.
The correction is now **implemented and offline-tested**, not independently
reviewed or accepted live. See `docs/codex-compatibility-correction.md` for frozen
regression seams, red/green evidence, code hashes and exact validation commands.
Only Codex permits absent MIME; explicit MIME and Vertex rules remain enforced.
Empty final output assembles validated completed items with identity/index/text
agreement and fail-closed lifecycle checks. Production evidence guards are unchanged.

Final full regression: **1,977 passed, 3 expected skips in 467.61s**, exit 0;
focused Codex/header suite: **509 passed**; mypy: **35 source files clean**;
JavaScript syntax and diff checks passed. All validation ran through the mandated
runner. Its long temporary path caused 160 Chromium setup errors in the first
full run; fresh short `0700` sibling directories under the same approved root
resolved that without modifying the runner, HOME, profiles or guards. Retain both
directories. The report documents this command-local adjustment and an existing
browser timing failure that passed in isolation and in the final complete run;
the browser tests were not changed. No stability-fix claim is made.

**Next: independent Standards/Spec reviews — now explicitly authorized by Adam**
for the next session; none was launched during handoff. See the latest HANDOFF
section for scope and route-verification requirements. No different reviewer model
has been selected. Adam also authorized a local checkpoint commit, not a push.
A private-draft/Guardian live acceptance run is still a separate decision. Ticket 19
remains **Blocked** on actual reviews/live acceptance; ticket 28 remains unimplemented.
No live model call or profile edit occurred.
Older diagnostic/validation statements below are historical and do not override
this latest section.

This finding supersedes older statements below that the immediate rejection cause
is unknown. Why the server/intermediary omitted MIME remains unknown; historical
uninspected bodies cannot be inferred from these new responses.

## Latest authorization — diagnostic scope widened

Adam explicitly approved widening Codex diagnostic boundaries as required to find
the cause, within sensible safety limits, and carrying that approval into the next
session. See the top of `HANDOFF.md` for his exact instruction and operational
bounds. Necessary diagnostic model calls, private sanitized header/bounded-body
inspection and controlled client comparisons are authorized; do not re-ask for
this generic approval. This supersedes older diagnostic-permission restrictions
below, not production acceptance checks, runtime rules or unrelated safety limits.
No additional call was made while recording this approval.

## Latest resume evidence

See `docs/codex-alpn-comparison.md`: the approved two-request synthetic comparison
reproduced HTTP 200 / `missing_http_content_type` with both default TLS and explicit,
negotiated `http/1.1` ALPN. No production fix is established. The proposed experiment
below is now consumed, not a next action. The validation-root conflict was freshly
reproduced (one server test failed); 329 focused Codex/header tests passed.
After the environment change, that exact server file passed 60 tests through a
fresh external directory. No production code changed; the full regression has
not been rerun and parent 19 remains Blocked.

## Destination and next step

Follow the recommended **complete internal first-runtime journey**, not another demo and not a claim of public distribution: diagnose → author/inspect → generate/check → exact-version approve/run/resume → regenerate safely → measure. Keep the existing core and browser. The LinkedIn workflow is a real-model acceptance scenario, not the entire product definition.

- Next approved implementation: **ticket 28**, one Transform-only parallel wave. Not started; do not mark delivered.
- Next design dependency: **D2 executable identity/approval/continuation**. Drafting is approved, but the semantics are not settled. Gate/resume/regeneration must not invent a binding/identity policy.
- No runtime implementation was attempted during this triage. A valid external validation environment is now available through the profile-scoped runner; do not weaken the protection that originally exposed the blocker.
- Do not create more header-diagnostic tickets or repeat a failed provider call without a discriminating hypothesis.

## Ticket disposition

- **01–12:** already accepted/closed; unchanged.
- **13:** accepted and closed under Adam's present closure authorization. The implementation and independent reviews already existed (`0bad1d0`, `3e47b2b`, `docs/designer-ticket13.md`). Historical handoff records Adam trying the UI and saying “good work. next”. This corrects stale `ready-for-agent` bookkeeping; no self-review or new green regression is claimed.
- **14–18:** already accepted/closed; unchanged.
- **19:** **Blocked**, not closed. Its offline components exist; a successful live Generator/Guardian pair and acceptance are still missing. The new DeepSeek synthetic probe does not satisfy the parent.
- **20–27:** already accepted/closed; unchanged. Header hardening completion does not imply provider availability.
- **28:** ready-for-agent, not implemented. Its acceptance criteria and independent implementation reviews remain open.

## Actual capability inventory

- Delivered: read-only diagnosis and measured baselines; restricted in-memory generation and independent conformance; Transform/Decision, restricted Judgment and bounded Loop routes; local browser authoring and checking; bounded role fixtures/data snapshots; LinkedIn capture, model-operation plumbing and offline completed-pair replay.
- **P26 / D6:** initial browser scenario delivered by tickets 13–14. Do not rebuild it or ask again whether the initial surface is browser or TUI.
- **P21 / D4:** tickets 17–18 deliver a bounded registry-derived role composition and controlled source. General role/agent/skill generation and verification remain incomplete.
- **P22:** controlled input snapshot/replay exists (ticket 18); do not count it as wholly unstarted. Broader supported compositions still need explicit acceptance cases.
- Not delivered: generated parallel execution/compositions; exact executable identity and Gate/resume lifecycle; safe generated/user-layer regeneration; complete agent/skill artifacts and permission proof; complete browser/measurement journey.
- Kanban emission and opt-in generated-version review remain later roadmap extensions, not silently discarded. Distribution/naming/public packaging, non-Hermes targets and Hermes activation/writes stay deferred.

## Decision disposition

### Closed or already settled; no repeat approval prompt

- **A2:** default wave concurrency `min(branch_count, 4)`, range 1–16, maximum 16.
- **A3:** P14 worst case counts `max_iterations + 1` Loop visits.
- **D1:** accepted parallel-wave contract and ADR 0011; ticket 28 is the implementation.
- **B6 interpretation:** retain the existing conclusion: no drop-in HTTPX replacement and no further raw-header diagnostic project. Current provider triage does not change this safety/evidence contract.
- **B7 interpretation:** missing usable `date_created` on a selectable draft blocks selection; exact-filename ascending tie break; preserve approved metadata/test seams and read-only source behavior.
- **D6:** browser selected and initial bounded authoring scenario delivered.
- **C12:** preserve the existing deferrals; no packaging or Hermes-write project is opened.

### Preparation authorized; not falsely closed as delivered contracts

- **B5 / D2:** executable identity and approval/continuation contract drafting. Final identity, restart/durability and permission semantics remain consequential and require direct acceptance.
- **C8 / D3:** prepare one non-Intervention vocabulary and invalid-output example using the existing source seam. This is not approval to widen executable vocabularies without a tested contract.
- **C9 / D4:** reuse the representative registry evidence and bounded Generator/Guardian fixture contracts already delivered; scope only the remaining agent/skill/permission gap, not another role demo.
- **C10 / D5:** prepare an isolated fresh-session permission-test plan. Actual fresh agent sessions, denied tool attempts and protected writes require direct approval of that plan.
- **C11 / D7:** describe one supported Kanban emission shape and explicit rejections when this later target is scheduled. No board activation, live writes or broad second-target implementation is authorized by triage.

### Direct decisions still required

**Provider direction settled in this triage:** Adam selected “Keep the existing model pair and investigate the Codex Generator failure.” Keep `openai-codex / gpt-5.6-sol` Generator and `vertex / google/gemini-3.1-pro-preview` Guardian. Do not create a DeepSeek production adapter or substitute either profile. The DeepSeek probe remains a separate observation, including its requested/reported identity difference.

1. **Next bounded live Codex experiment:** the offline/static continuation found no proven remedy. A discriminating live control requires explicit request budget, exact synthetic input, one variable, truthful identity and a fresh private destination; no private draft, retries, fallback or automatic Guardian call. No additional Codex request was authorized or sent by the in-turn selection. Any final private-draft acceptance run is a separate decision.
2. **Lifecycle semantics and fresh-session permissions:** D2 and D5 as above.
3. **Validation environment:** resolved for fresh `astra-pinned` sessions by the narrow external runner documented at the top of `HANDOFF.md`; project evidence guards and real HOME remain unchanged. A full regression has not yet been run in that environment.

These are the material remaining decisions, not another blanket questionnaire about previously approved details.

## New provider evidence

Read-only config inspection:

- `stillroom-research-assistant`: `openai-codex / gpt-5.6-sol` (not DeepSeek).
- `stillroom-signal-generator`: `openai-codex / gpt-5.6-sol`.
- `stillroom-signal-guardian`: `vertex / google/gemini-3.1-pro-preview`.
- `stillroom-content-scout`: `custom / deepseek-v4.1-flash:cloud`, endpoint `http://127.0.0.1:11434/v1`.

One tools-disabled synthetic request used content-scout's configured route, not a spawned agent. No draft, SOUL or private guidance was sent. The profile was byte-identical afterwards. Result: HTTP 200, exact `OK`, 0.613 seconds, reported model `deepseek-v4.1-flash`, reported 52 prompt / 33 completion / 85 total tokens. The strict exact-model check returned `unexpected_result` (exit 1) because requested and reported identifiers differ. Connectivity/content succeeded; exact-model acceptance and workflow integration did not pass. No retries or fallback were issued by the probe; backend retry behavior is unknown.

Detailed preserved result: `docs/provider-triage-2026-09-22.md`.

The previous live smoke 05 explicitly invoked only Codex Generator and stopped at `missing_http_content_type`, HTTP 200. **Gemini Guardian was not invoked.** The available evidence therefore does not attribute that failure to Vertex rate limiting. A successful DeepSeek response does not diagnose the Codex response or prove Guardian availability.

## Validation and closure limits

- Historical source baseline `f5f620fec7c0bace8183611f48d10ae1be612244`: 1,892 passed, 3 skipped in the recorded prior environment; not freshly reproduced here.
- Fresh assessment run: 876 failed, 1,016 passed, 3 skipped, exit 1. Dominant failures reject pytest temporary evidence paths inside `.hermes`. See `docs/closeout-assessment-2026-09-22.md`; not every failure is independently attributed.
- Fresh typecheck at assessment and again after triage: no issues in 35 source files; JavaScript syntax check passed. Final documentation validation found no whitespace or added relative-link errors; the diff contains only Markdown (no runtime/test/profile changes).
- After Adam retained the existing pair, fresh targeted Codex/response-header tests passed: **329 passed in 2.25 seconds**. The subsequently unblocked external runner passed the exact formerly blocked server file (**60 passed in 29.36 seconds**), but the full regression has not been rerun. See the provider-triage report for the static findings and proposed bounded next experiment.
- Ticket 13 closure relies on existing implementation/review evidence and Adam's current authorization, not on a fabricated new green suite.
- No new implementation reviews, live workflow pair, Gemini test, private-draft capture, profile change, commit or push occurred during triage.
