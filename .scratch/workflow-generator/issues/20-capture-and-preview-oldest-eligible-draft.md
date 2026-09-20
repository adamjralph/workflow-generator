# 20: Capture and preview the oldest eligible draft

**Type:** task
**Parent:** 19: Refine and review the oldest unprocessed LinkedIn draft

**What to build:** From the browser, capture the oldest eligible unprocessed article or post and preview its exact source, creation date, approved role guidance and configured role models. Explain exclusions and invalid inputs without changing any source. This is the first vertical slice of the approved ticket-19 breakdown, not a substitute for the model-backed workflow.

**Blocked by:** 18: Run role workflow with controlled data source (accepted and closed; dependency satisfied).

**Status:** ready-for-human

## Readiness

Adam approved implementation of ticket 20 and its capture, actual HTTP and real Chromium test seams, bounded explicit authority inputs, limits and review baseline `35b9a5d7ac8784c062d25ec91f367e6c6d9ffb93`.

Folder membership defines drafts: scan only top-level regular UTF-8 Markdown files in content-drafts; do not scan content-inbox (ideas) or published. Another workflow moves published content; this workflow never moves files. Exclude exact public-copy-bank.md before metadata parsing; Adam explicitly confirmed exclusion and removed its frontmatter. Retain actual frontmatter spelling date_created (confirmed read-only), not the conversational created_date shorthand. Require explicit boolean processed; otherwise eligible drafts need a valid ISO calendar date. Missing/invalid required metadata blocks selection visibly. Sort by date_created, then exact filename ascending. Defensively exclude explicit published metadata and processed true.

Approved limits: 256 directory entries, 64 KiB per draft, 128 KiB per guidance file and 512 KiB total captured text; fail rather than truncate. Capture the explicitly configured complete guidance set identified by ticket 19 (both SOULs, both role skills, writing skill, voice/craft references, brand index, offer, audience, product, content system, Guardian checklist and current-versus-superseded authority). No automatic link-following or recursive authority discovery. Resolve only non-secret provider/default-model selections from both configured profiles.

The operator supplies a local manifest; HTTP cannot select paths, credentials, models or output roots. No model calls, authentication checks, credential-content reads or protected writes are authorized. This slice does not accept or implement ADR 0010 or ticket 19's later execution/replay mechanisms.

## Acceptance criteria

- [x] Agreed metadata rules select the oldest eligible article/post with boolean `processed: false` and a valid `date_created`; no inferred dates or silently skipped ambiguities while claiming oldest.
- [x] Invalid metadata, reference/published files, date ties, empty sources, unsafe files and exceeded limits produce the agreed visible outcomes. No source metadata is repaired.
- [x] Capture binds exact source and approved guidance bytes, instruction versions and non-secret configured model selections in an immutable digest-bound input bundle. No credentials are captured.
- [x] Browser preview identifies the selection, exclusions, guidance provenance, both configured defaults and the eventual two-generation-call ceiling. Capture and page load perform no model calls.
- [x] Explicit recapture is required for source/config changes; recapture invalidates stale results and late responses without silently rereading captured inputs.
- [x] Actual HTTP tests retain loopback Host/Origin/token/body protections and reject browser-selected paths, providers, credentials, code and output roots.
- [x] Temporary-source tests and real Chromium tests exercise capture/preview and failures without committing production content; existing ticket-18 behavior remains covered.
- [x] Sources and Hermes files remain unchanged; capture artifacts stay in the caller-selected protected output root. A receipt never changes eligibility.
- [x] Agreed offline checks, typechecking and independent review pass; acceptance remains Adam's decision.

## Scope boundary

No model execution, publication, archival, processing-flag edits or autonomous Hermes sessions. Downstream run/review/replay actions are not represented as delivered by this slice.

## Answer

Implemented in `e000f8a`, with independently reviewed follow-up fixes in `3b6224a`.
Evidence and operator manifest/startup instructions: `docs/designer-ticket20.md`.
Full offline suite: **1,139 passed, 3 expected skips**, including **114 Chromium tests**;
mypy **27 files clean**. Independent follow-up: Standards no outstanding hard
findings (one optional duplication heuristic), Spec no outstanding actionable findings.
No model calls, authentication traffic, credential-content reads or protected writes.

Ready for Adam's inspection and acceptance; not accepted/closed automatically.
Parent ticket 19 and tickets 21–23 remain unchanged.

## Comments

Adam approved folder-based classification, populated creation dates, the proposed
limits and remaining ticket-20 capture decisions; then explicitly excluded the
public copy bank and removed its frontmatter. Runtime code retains the observed
`date_created` spelling. The complete guidance set is an explicit operator manifest,
not recursive authority discovery or a request to implement model operations.
