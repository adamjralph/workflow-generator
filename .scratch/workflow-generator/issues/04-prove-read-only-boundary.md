# 04: Prove the read-only boundary

**What to build:** Diagnosis runs against a live Hermes home without modifying Hermes. A test in a fresh home demonstrates that running a diagnosis leaves Hermes source, configuration, authentication, and live board/profile state untouched, and that the tool installs as a plugin without editing any of them.

**Blocked by:** 03.

**Source:** `spec.md` → "Never modify Hermes"; `CONTEXT.md` §9.3; ADR-0002.

**Status:** accepted and closed (Adam's explicit approval)

- [x] Running a diagnosis against a Hermes home leaves source, configuration, authentication, and board/profile state byte-identical (verified by digesting the tree before and after, or by mounting it read-only).
- [x] A test asserts the diagnosis adapter has no write path.
- [x] The tool is installable as a Hermes plugin without editing Hermes source, configuration, or authentication. Accepted as installation only; activation remains a separate, explicit Hermes config opt-in.
- [x] A diagnosis succeeds in a fresh home with no pre-existing tool state.

## Comments

Implementation and proof: [ticket 04 evidence](../../../docs/read-only-ticket04.md).
User authorized the three test seams and review baseline `c3260ab`.

A native local directory plugin installs by symlink without protected edits and
passes isolated real-Hermes loader registration/invocation. However, the installed
Hermes requires `plugins.enabled` configuration for normal activation. No config
was changed and no production activation bypass was added. Adam explicitly
approved the installation-versus-activation distinction and accepted and closed
ticket 04. Activation remains a separate operator config opt-in; this approval
does not authorize config changes or bypassing the host gate. Tickets 05–06 are
also accepted and closed; see `HANDOFF.md`.

Implementation: `6271106`. Full suite with isolated real-loader check opted in:
106 passed, 2 live-Jev skips. Mypy retains 11 inherited errors, no new diagnosis
errors. Independent review: Standards 0 violations + 1 nonblocking duplication
heuristic; Spec 1 acknowledged partial activation criterion, no further defects.
