---
status: accepted
accepted: 2026-09-25
---
# Gate binds immutable executable identity and a one-use local decision

For the first Gate slice, approval binds both the re-derived canonical **internal spec** digest and the re-derived **executable bundle** digest, scoped to one workflow version, run, Gate and pause attempt. The bundle must attest its executable configuration and a small registered set of deterministic, side-effect-free bindings with frozen, verified code/config/dependency artifacts. Today's arbitrary Python caller mappings are not eligible. An import name, object identity, mapping proxy or function source hash alone is not executable identity. This is a private identity protocol; it does not settle public persistent spec serialization or community packaging (ADRs 0004, 0005, 0009).

A Gate consumes one budget step when visited. Pending is a durable pause; explicit approval permits only the approved route; rejection terminates and invalid decisions fail closed. Submission and continuation do not re-spend the Gate. Decisions are one-use for that exact run/Gate/pause and cannot be transferred across versions. Both independent drivers and the checker must preserve the same canonical event/budget semantics using independently supplied offline decisions.

The first real decision seam is an owner-only **local operator CLI under the OS account**, deriving the account identity rather than trusting a caller-supplied approver label. This is account-level trust only: another agent or process under the same UID can approve. Remote approval or protection from same-UID agents requires a separate trust decision. A stored JSON decision or an existing business-draft approval is not an authorization for this Gate.

Restart is promised only from a **durably committed Gate pause** with immutable artifacts, checkpoint, decision and continuous event evidence. A fresh process re-derives identities and resumes only remaining work under a per-run exclusive claim. Missing/torn/corrupt evidence fails closed; an in-flight step at crash is indeterminate and is never automatically replayed. The first slice excludes Forks, regeneration, live model/tool side effects and Hermes writes. The detailed accepted contract and required negative evidence are in [D2 Gate identity contract](../gate-identity-contract.md).

## Decision and limits

Adam approved the recommended D2 boundary and then specifically approved OS-account trust for the first offline Gate slice on 2026-09-25. This records the contract, **not** an implemented, tested or human-person-authenticated Gate, nor authorization to commit/push or launch a build. If the binding dependency closure, durable transaction boundary or operator trust cannot be demonstrated as specified, return for a scope decision; do not weaken the claim silently.

## Rejected alternatives

- Hash an in-memory graph or Python callable name and call that exact executable identity: its behavior and dependencies can change under the same digest.
- Treat a rejection, a caller-supplied digest or an approver string as consent: would let the wrong or untrusted decision unlock work.
- Promise automatic replay after arbitrary mid-step crash: can duplicate effects without transactional/idempotent effect protocols.
- Require a public interchange spec format or freeze an entire arbitrary Python environment for this first bounded slice: expands a deferred product decision and the implementation far beyond the Gate demonstration.
