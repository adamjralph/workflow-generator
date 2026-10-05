# Ticket37 — bounded delivery of unresolved outcome to a local webhook

**Status:** implementation in progress under continuing autonomous release authorization.

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

**Still missing:** focused tests, typing, complete regression, independent review,
commit/push and remote verification. External channel/recipient V2 remains open;
this ticket does not settle it or prove real-workflow acceptance.
