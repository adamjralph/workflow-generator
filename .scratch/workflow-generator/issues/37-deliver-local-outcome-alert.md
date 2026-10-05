# Ticket37 — bounded delivery of unresolved outcome to a local webhook

**Type:** task

**Status:** technically complete under continuing autonomous release authorization;
independent Standards/Spec review and full regression passed. No personal Adam acceptance.

Complete the existing offline declared-output → bounded-remedy journey with one
explicit HTTP delivery to a caller-selected literal loopback endpoint. Reuse
`run_with_remedy` and the representative internal report/checklist contract. Both
drivers must yield the same public delivery behavior. Suppress passed/repaired
results; deliver exhausted, ineligible and repair_failed results with expected
output, unmet requirements, attempted remedy, run attribution and next action.

Reserve before delivery; one attempt, timeout at most five seconds, no redirect,
proxy, retry or implicit recipient. Persist acknowledgement/failure separately
from outcome success; HTTP 2xx only proves receiver acknowledgement. Re-entry
must not resend, and interrupted delivery remains unknown. Validate saved evidence
before sending. Never persist endpoint, response content or exception text. Reject
external addresses and credentials. No live provider, real recipient, deployment,
ongoing access, human gate changes or private-source changes.

**Validation (2026-10-05):** final focused tests 135 passed; typing clean in 48
files; complete regression 2,534 passed, 3 expected skips, exit 0. Independent
Standards and Spec review cleared the total-deadline correction with no remaining
findings. [Commands and evidence](../../../docs/outcome-ticket37.md).

**Release gaps:** external channel/recipient V2, live/spend policy V3,
real-workflow acceptance V4 and expanded contract V5 remain open. No external
message or real-workflow acceptance is claimed. Publication: inspect Git/remote
and the handoff for the observed push/read-back result.
