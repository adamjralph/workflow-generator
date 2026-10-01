# 34: Check a declared output against what a workflow actually produced

**Type:** task
**Status:** accepted by Adam — implemented and verified.
**Blocked by:** None.
**Approval boundary:** Adam authorized acceptance, commit and push. No paid call, new implementation slice or deployment authorized.

## What to build

A fixture-backed workflow declares one required JSON output file and its required
fields before running. After execution, a deterministic checker reads the actual
file and reports whether that declaration was met. Save a run-attributed verdict
that names unmet requirements, rather than trusting the agent's completion claim.

This is one complete slice: declaration → actual output → saved verdict. It checks
“produced what was declared,” not “produced good work.” Existing execution
conformance is not a substitute for checking the output.

## Acceptance criteria

- [x] The expectation is typed, validated before execution, and attached to a specific workflow step—not supplied afterward.
- [x] The checker reads the produced file under the approved output folder; it does not trust the agent saying it created one.
- [x] A present, valid file within the declared byte limit containing every required field passes.
- [x] The expectation declares a positive configurable `max_bytes` (default 1 MiB); exceeding it fails with `file_too_large`. Adam approved this bounded-read contract during implementation.
- [x] A missing file, invalid JSON, or missing required field fails, naming the unmet requirement.
- [x] An unsafe file reference is rejected without reading outside the approved folder.
- [x] The saved result identifies the run, checked step, declaration and findings. A workflow reaching `COMPLETED` does not automatically mean its output passed.
- [x] Offline demonstrations prove both a passing case and a deliberately failing case, with regression tests covering the failure conditions.

## Non-goals and limits

No model judgment, repair attempts, notifications, browser changes or paid calls.
No new node type or driver. No Hermes writes, private-source edits or publication.
No claim of semantic quality, real-workflow acceptance or full pillar completion.
V2–V5 remain open; alert delivery and repair-budget decisions do not block this slice.

## References

- [Expected-outcome verification pillar](../../../docs/outcome-verification-pillar.md)
- [Current project state](../../../CURRENT.md)
- [Implementation contract and verified evidence](../../../docs/outcome-ticket34.md)

## Completion requirements

Demonstrate the accepted criteria with real offline execution and saved evidence.
Run the project's applicable regression and typing checks within its permitted
evidence boundary. Record commands and actual results; a prior suite pass or
successful workflow terminal does not establish output compliance.
