# 22: Independently review the exact draft with Signal Guardian

**Parent:** 19: Refine and review the oldest unprocessed LinkedIn draft

**What to build:** Extend the captured-input Run so a valid Generator draft proceeds to one independent Signal Guardian review in the same run. Present the exact draft, verdict, required fixes, optional advice and usage in the browser. A complete draft plus review is completed even when changes are requested; no verdict authorizes publication.

**Blocked by:** 21: Generate one LinkedIn draft with Signal Generator.

**Status:** resolved

## Readiness

Adam approved implementation with the inherited ticket-19 contract, authority inputs and numerical bounds, ticket-22 test seams, and review baseline `538c1014534d5a4b35eedef604a4bdd398e26559`. He explicitly approved pinning `~/.config/gcloud/application_default_credentials.json` as the existing authorized-user Vertex credential source. In-memory token acquisition is approved without discovery fallback, credential-file or Hermes-state writes. Live authentication/model availability remains unverified. Live smoke requires separate explicit authorization and a named output destination.

**Accepted and closed:** Adam explicitly accepted ticket 22 ("accept 22"). Implementation and independent review are complete. See [ticket-22 execution and offline evidence](../../../docs/designer-ticket22.md). Full offline suite: 1,472 passed, 3 expected skips; mypy passed (33 source files). Standards review: 0 hard violations, 3 optional maintainability heuristics. Spec review: 0 actionable findings. No live auth/model calls were made. Acceptance below records Adam's decision on the offline evidence; it does not claim verified live availability.

## Acceptance criteria

- [x] A fresh explicit run independently gives Guardian the original captured source/authority and exact Generator draft, not merely Generator's account. The review is bound to that draft's digest.
- [x] Guardian checks brand voice, LinkedIn fit, strong hook, AIDA and a source-coherent CTA, plus supported claims, privacy, reader fit, one-point clarity and current positioning. Missing support is reported rather than fabricated.
- [x] Strict results distinguish Approved, Changes requested and Blocked, with criterion findings, excerpts/references, required fixes and optional preferences. Guardian does not edit the submitted draft; record copy-only scope and `Image consistency not reviewed.`
- [x] A dedicated tool-free Vertex adapter preserves the captured configured default and uses the explicitly approved credential source. Token acquisition is bounded, in-memory only, without discovery fallback, persistence or retries; disclose auth network activity separately from generation calls.
- [x] Enforce two workflow steps and a separate maximum of two generation attempts per run, at most one per role. Reserve before sending; Generator failure/blocked output prevents Guardian. No retries, revisions, fallback models, tools or background review.
- [x] Retain immutable sanitized exchange evidence and a receipt binding inputs, operation versions, draft, review, usage and execution log. Distinguish completed editorial verdicts from execution failure or uncertainty; preserve partial evidence without retrying.
- [x] Duplicate/concurrent submissions and restart uncertainty never send extra calls or resume into Guardian. Intentional rerun needs a new explicit request and may select the same oldest source; warn when the capture has already run.
- [x] Browser shows exact version attribution, both role results, usage and visible failure/uncertain states with stale-response protection and inert rendering.
- [x] Injectable-transport tests verify exact role inputs, order, call reservations and limits, review digest, auth boundaries and failure stopping through the actual drivers. Actual HTTP and real Chromium tests cover complete, changes-requested, blocked and failed runs.
- [x] Sources, processing flags, archives and Hermes remain untouched. No publication or scheduling occurs; private material is not authorized for public use merely by folder membership.
- [x] Agreed offline regression, typechecking and independent review pass. Fixture coverage is distinguished from separately authorized live evidence; acceptance remains Adam's decision.

## Scope boundary

This completes the draft/review path, not offline conformance or parent-ticket acceptance. Ticket 23 supplies completed-pair replay. Earlier Generator-only results are not silently resumed or relabelled as complete reviewed pairs. Acceptance does not authorize live smoke or implementation of ticket 23.
