# Workflow Generator: completion assessment and proposed closeout

Assessment date: 2026-09-22 (AEST).
Inspected baseline: `f5f620fec7c0bace8183611f48d10ae1be612244`.
Status: investigation and recommendation, not a new implementation authorization, acceptance, or independent review. No production code was changed.

## Bottom line

This is a substantial, tested local application and a restricted workflow engine, not a finished general workflow generator. It has moved beyond a prototype, but the full product still lacks major execution/lifecycle capabilities. The LinkedIn example is much closer in offline implementation terms, but has never completed the recorded live Generator/Guardian journey.

The efficient route is to retain the current core, stop adding demonstration modes and diagnostic-only tickets, reconcile the actual capability inventory, and deliver against a frozen end-to-end acceptance checklist. Do not rewrite the runtime, remove independent checks, weaken safety, or equate a narrower release with completion of the original product.

There is no defensible percentage complete or calendar delivery estimate in the repository. Ticket counts and passing tests are not measures of remaining product work. Several remaining contracts are not settled, and the provider failure has no demonstrated remedy.

## What actually exists

- **Diagnosis:** read-only Kanban run attribution, four measurement units, worker/auxiliary/review breakdowns, per-role reports and baseline comparison. Delivered in tickets 03–07.
- **Core generation/checking:** typed in-memory specs; independent plain reference and generated pydantic-graph execution; structural and supplied-case behavioral conformance. Transform/Decision routes, restricted Intervention Judgment, and bounded Loop routes are implemented (tickets 08–12).
- **Browser front door:** an actual local browser designer, questionnaire/composition, graph display, checking, support-request examples, and custom inputs (tickets 13–16). Ticket 13's implementation is real despite its stale `ready-for-agent` status; its acceptance remains a separate question.
- **Bounded roles/data:** registry-derived role excerpt, compatible fixture workflow, controlled read-only source capture and replay (tickets 17–18). These are useful partial delivery of later map items, not arbitrary agent/skill composition or a permission sandbox.
- **LinkedIn workflow:** immutable source/guidance capture, explicit Generator operation, exact-draft Guardian review, receipts and offline completed-pair replay (tickets 20–23). The configured provider adapters exist; successful live availability is not established by fixture tests.
- **Provider hardening:** tickets 24–27 improve validation and diagnostic evidence. They do not demonstrate a successful live generation.

Source cross-check: `agent_lab/reference.py:243–303` still rejects non-Route edges and unsupported node kinds, including Gate. Its model-operation admission is limited to `draft_linkedin` and `review_linkedin`. `agent_lab/generation.py:56–150` constructs a route-based, in-memory GraphCandidate. This confirms that declared Fork/Gate support in the spec is not executable general Fork/Gate support.

## What remains

### Restricted LinkedIn parent (ticket 19)

Its component implementation and offline checking are largely present. The recorded live attempts all stopped at Generator; Guardian and successful completed-pair replay have not been demonstrated on an actual successful live pair. The latest recorded smoke returned HTTP 200 with missing Content-Type. The response author/body and root cause remain unknown. A new permission alone is not a fix.

Closure requires a demonstrated remedy if necessary, fresh explicitly bounded live authorization and private destination, successful generation and independent review within the agreed call limits, real-evidence offline replay, and Adam's acceptance. Changes requested is a valid completed Guardian review; execution failure is not. Do not silently change profile models or repurpose old one-shot authorizations.

### Full first-runtime product

These are substantial work packages, not polish:

1. **Checked parallel execution:** ticket 28 is approved and not implemented. Remaining declared parallel compositions need execution and conformance tests; a single Transform-only wave does not establish Decision/Loop/Judgment branches, multiple waves, or gates between waves.
2. **Executable identity and lifecycle:** immutable executable spec/bundle versions, exact-pair approval, rejection, continuation integrity, restart/resume semantics, no repeated completed work, and regeneration preserving user edits while invalidating stale approval. Existing draft receipts and foundation approvals do not substitute for this.
3. **Real role/skill boundary:** extend the existing bounded role/data work into inspectable runnable agent/skill artifacts and demonstrated permissions. Fresh-session denial testing needs its own approved plan. SOUL instructions and Python binding integrity are not a sandbox.
4. **Product integration:** expose supported parallel/Gate lifecycle through the existing browser; finish the bounded completeness-check requirement; connect diagnosis and generated-run attribution to real before/after measurements; prove the complete user journey.

The roadmap also includes a second Kanban emission target and opt-in distinct-model review. The delivery map explicitly treats these as extensions rather than blockers for the default first-runtime journey. They remain outstanding original-roadmap work, not silently completed or deleted. Public distribution, naming, non-Hermes targets and Hermes writes remain explicitly deferred.

## Why it feels slow

### 1. Local ticket success is not end-to-end product success

The sequence delivered threshold routing, triage, custom inputs, roles, source capture and LinkedIn operations. These are legitimate increments, but the core full-product lifecycle remains unfinished. In particular, ticket 28 does not close the live LinkedIn blocker, and closing ticket 19 would not deliver the general generator. Keeping those two finish lines separate is essential.

### 2. The provider investigation became a detour without a demonstrated remedy

Tickets 24–27 successively hardened/classified/observed HTTP responses. Five separately authorized smokes still stopped at Generator. The offline transport study found that plain HTTPX changes required byte-level observations and acceptance behavior; it was not a drop-in replacement. More diagnostic coverage improved failure evidence but did not produce the desired post and review.

The custom adapter carries low-level HTTP framing/header responsibilities alongside product code. That is a maintenance cost, but it is not proof that the adapter caused the live failure. A maintained client is an architectural option only if Adam explicitly reopens and approves the evidence/transport contract; simply relaxing validation is not an acceptable shortcut. The latest decision closes this investigation thread, so this assessment does not reopen it by implication.

### 3. The planning documents are inconsistent

- `README.md:9–33` stops its status account at ticket 08 and cites 238 passing tests.
- `map.md:17–24` calls the initial designer the implementation frontier; later sections identify ticket 28 instead.
- `issues/13...md` still says `ready-for-agent`, despite implementation, browser tests and subsequent extensions documented in `docs/designer-ticket13.md`.
- P21/P22/P26-style capabilities have partial or substantial implementations in later numbered tickets, but the original proposal rows still look wholly future-facing.
- `HANDOFF.md` is 1,578 lines and contains many historical “next” instructions. The latest section says 69 commits ahead; the inspected git state is 71 ahead of the local `origin/main` ref. No network fetch was performed.

This makes rediscovery, re-scoping and redundant acceptance questions likely. Historical evidence should be retained, but not presented as current status.

### 4. Contracts and permissions genuinely constrain the finish

Executable identity, arbitrary Judgment vocabulary, broader role composition, runtime permission proof and supported Kanban shape have unresolved decisions. Deferring public format/packaging was sensible, but executable identity still needs a deliberate private representation contract. Live failure recovery cannot be inferred from an offline test pass.

### 5. Delivery overhead is high, but removing assurance is the wrong fix

The handoff itself records Adam's request to reduce token use after ticket 22. The history contains repeated implementation, verification, acceptance and handoff updates for small slices. Review has caught real accounting and conformance defects, so retain Standards/Spec review. Reduce repeated context, stale documents and unnecessary ticket boundaries instead. Git history shows most of this repository's work occurring September 20–22; it does not establish weeks of calendar delay or a measured token/cost attribution.

## Recommended closeout sequence

### A. Freeze one release contract and current-state checklist

Agree whether the immediate release is the complete internal first-runtime product or only the LinkedIn workflow. My recommendation is the internal first-runtime product, with the LinkedIn workflow as its real model-backed acceptance scenario, not its definition.

Create one current capability checklist: implemented, independently reviewed, accepted, blocked. Link historical evidence rather than copying it. Reconcile ticket 13 and map coverage without declaring acceptance on Adam's behalf. Mark deferred extensions explicitly; deferring any previously required first-release capability needs approval.

### B. Keep the approved next core step; design the lifecycle before downstream work

Implement ticket 28 exactly against its accepted contract. Separately complete the already-authorized D2 identity/approval draft before writing Gate or artifact code. Reuse RunAccounting, RunLog, immutable-store patterns and the existing binding seams. Keep reference and generated execution control flow independently testable.

After those contracts are agreed, group downstream work into coherent end-to-end deliveries: supported parallel compositions; exact-version Gate/resume/regeneration; role/skill/permission integration; browser and measurement integration. Retain bounded changes and reviews, but do not require a new product-planning cycle for each header diagnostic or UI field.

### C. Treat live feasibility as a bounded release risk, not another blind retry

Do not repeat the same provider request expecting the diagnostics to fix it. Adam must decide whether to reopen a narrowly scoped provider/evidence-contract investigation or leave live functionality explicitly Blocked. Any reopened work needs a specific hypothesis, evidence to distinguish outcomes, call budget, stop condition and new private destination. No fallback model, harness substitution, auth repair or Hermes modification is implied.

If considering a maintained HTTP client, explicitly decide which raw observations are requirements, which are implementation detail, and how historical receipt/replay versions remain valid. Preserve TLS validation, credential isolation, no hidden retries/fallbacks, bounded responses/deadline, call reservation and truthful usage/failure recording. The existing offline study is the starting evidence, not a reason to repeat it.

### D. Finish by proving the journey, not by counting closed tickets

Release acceptance should demonstrate:

1. Diagnose a real attributable baseline.
2. Author and inspect a supported workflow in the browser using controlled roles/data.
3. Generate an inspectable version and pass independent reference/candidate checks, including adversarial mismatches.
4. Approve the exact executable pair, reject changed/wrong-run approval, pause and resume after restart without redoing completed work or spend.
5. Regenerate while preserving the user layer; require fresh approval.
6. Demonstrate real allowed behavior and a genuinely denied tool operation in the separately authorized fresh-session test.
7. Complete the authorized live Generator/Guardian scenario, then replay its real evidence offline with no extra provider call.
8. Present attributable before/after measurements with auxiliary/reasoning costs and unknown values explicit. A measured improvement is not assumed.
9. Run the full required regression, typing and browser checks; obtain independent Standards/Spec review and Adam's acceptance.

This reuses the application already built. It does not need another runtime, frontend framework, plugin mechanism or parallel team of implementation agents.

## Fresh verification in this assessment

- Working tree was clean at entry.
- `graft check`: wiring graph in sync with source; no deep/paid indexing performed.
- `.venv/bin/python --version`: Python 3.14.7.
- `.venv/bin/python -m mypy agent_lab`: success, no issues in 35 source files.
- `node --check agent_lab/designer/static/app.js`: exit 0.
- `.venv/bin/python -m agent_lab.designer --help`: exit 0; local application entry point available.
- Full offline regression command: `env -u HERMES_PLUGIN_TEST_SOURCE -u HERMES_PLUGIN_TEST_PYTHON AGENT_LAB_JUDGMENT=stub .venv/bin/python -m pytest -q`.
- Fresh result: **876 failed, 1,016 passed, 3 skipped in 139.16 seconds; exit 1**. This is not a green regression run. Skips were the two explicit opt-in live Jev tests and optional real Hermes plugin-loader integration.
- **Validation Blocked by environment/path-policy conflict:** this session mandates temporary files under `/home/hermes/.hermes/profiles/astra-pinned/cache/scratch`; pytest's `tmp_path` consequently falls inside `.hermes`. The application's read-only boundary intentionally rejects evidence/artifact destinations there. The log contains 800 direct evidence-directory guard errors and 43 direct artifact-store guard errors, plus downstream/assertion failures. These counts classify error lines, not a proven root-cause classification of every failed test. No claim is made that all failures would disappear after relocation.
- The documented historical baseline is 1,892 passed and 3 skipped; it was not reproduced here. A permitted test environment with temporary evidence outside Hermes and project source is required for a valid full rerun. Do not remove the guard, change its expected failures, disguise Hermes as a different home, or report the historical result as fresh validation.
- Full actual console log: `/home/hermes/.hermes/profiles/astra-pinned/cache/scratch/workflow-generator-closeout-pytest.log` (temporary; this report preserves the command, result and diagnosed conflict).
- Final `git status --short`: only this new assessment document is untracked; no tracked code/test/config changes. `git diff --check` and the explicit untracked-document whitespace check emitted no errors (the latter uses `--no-index`, whose exit 1 indicates a new-file difference). The report contains no credential contents or production source captures.

No independent reviewer was launched for this assessment. Historical independent reviews above are repository records, not new reviews. No live model/auth calls, external publication, source-content capture, model substitution, Hermes configuration change, commit or push was performed. The proposal is not implemented, and the project is not being declared complete.

## Key source documents

- `HANDOFF.md:33–134`: latest decisions, ticket 28 and consumed live permissions.
- `ROADMAP.md:43–149`: milestones and actual completion definitions.
- `.scratch/workflow-generator/map.md:31–43,127–180`: product journey and dependencies; beware stale headings/rows.
- `.scratch/workflow-generator/issues/28-execute-and-check-one-parallel-wave.md`: approved next implementation and acceptance criteria.
- `.scratch/workflow-generator/issues/19-refine-and-review-oldest-linkedin-draft.md:206–260`: parent acceptance and latest readiness decisions.
- `docs/designer-ticket13.md`, `designer-ticket17.md`, `designer-ticket18.md`, `designer-ticket23.md`: implemented surface/role/source/replay capabilities and their limits.
- `docs/designer-offline-transport-investigation.md:14–32,151–181,207–218`: no established remedy and why HTTPX is not a drop-in replacement.
