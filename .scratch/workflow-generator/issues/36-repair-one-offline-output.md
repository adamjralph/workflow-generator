# 36: Repair one failed offline output

**Status:** implemented and focused-verified under Adam's continued-development instruction, 2026-10-05; complete post-change regression blocked by interrupted run.
**Boundary:** single offline Transform; trusted local bindings; no paid calls,
source edits, gates, whole-workflow redispatch, alert delivery or restart/resume.

## Scope and acceptance

After successful execution fails its declared output check, pass the declaration
and unmet requirements to one explicitly supplied repair binding. Use a fresh
output directory and the original detached input. Check actual output using the
same declaration and existing driver. Preserve original output and verdict.

The caller declares an aggregate step allowance of one (no repair) or two (one
repair). Reserve each step before invoking its factory. Save policy, reservation,
original/repair verdict identities and exact-byte digests, and a final receipt.
Failed execution is ineligible. An unrepairable result or callback failure stops;
no further retry. Interrupted calls have no completed receipt and no automatic resume.

Exercise both independent drivers for success, exhaustion, ineligible execution,
callback failure, attribution and preserved evidence; run typing and self-review.
This bounded local allowance does not settle V3's future live/spend policy.
Real alert channel, representative real workflow and internal release remain open.

## Evidence and remaining verification

[Evidence](../../../docs/outcome-ticket36.md): 188 focused tests passed, typing
clean in 47 files, standalone demo passed through both drivers, self-review no
remaining code blockers. Complete ticket35 baseline passed before implementation.
**Still missing:** complete post-ticket36 full regression. Its run was interrupted;
no aggregate success is claimed. Rerun the full command in the evidence document
before technical completion or another ticket. No personal Adam acceptance claimed.
