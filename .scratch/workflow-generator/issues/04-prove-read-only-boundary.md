# 04: Prove the read-only boundary

**What to build:** Diagnosis runs against a live Hermes home without modifying Hermes. A test in a fresh home demonstrates that running a diagnosis leaves Hermes source, configuration, authentication, and live board/profile state untouched, and that the tool installs as a plugin without editing any of them.

**Blocked by:** 03.

**Source:** `spec.md` → "Never modify Hermes"; `CONTEXT.md` §9.3; ADR-0002.

**Status:** claimed

- [x] Running a diagnosis against a Hermes home leaves source, configuration, authentication, and board/profile state byte-identical (verified by digesting the tree before and after, or by mounting it read-only).
- [x] A test asserts the diagnosis adapter has no write path.
- [ ] The tool is installable as a Hermes plugin without editing Hermes source, configuration, or authentication.
- [x] A diagnosis succeeds in a fresh home with no pre-existing tool state.

## Comments

Implementation and proof: [ticket 04 evidence](../../../docs/read-only-ticket04.md).
User authorized the three test seams and review baseline `c3260ab`.

A native local directory plugin installs by symlink without protected edits and
passes isolated real-Hermes loader registration/invocation. However, the installed
Hermes requires `plugins.enabled` configuration for normal activation. No config
was changed and no production activation bypass was added. The plugin criterion
remains open pending the user's decision on installation versus activation; see
the evidence for the exact limitation. Tickets 05–06 are not started.
