# 04: Prove the read-only boundary

**What to build:** Diagnosis runs against a live Hermes home without modifying Hermes. A test in a fresh home demonstrates that running a diagnosis leaves Hermes source, configuration, authentication, and live board/profile state untouched, and that the tool installs as a plugin without editing any of them.

**Blocked by:** 03.

**Source:** `spec.md` → "Never modify Hermes"; `CONTEXT.md` §9.3; ADR-0002.

**Status:** ready-for-agent

- [ ] Running a diagnosis against a Hermes home leaves source, configuration, authentication, and board/profile state byte-identical (verified by digesting the tree before and after, or by mounting it read-only).
- [ ] A test asserts the diagnosis adapter has no write path.
- [ ] The tool is installable as a Hermes plugin without editing Hermes source, configuration, or authentication.
- [ ] A diagnosis succeeds in a fresh home with no pre-existing tool state.
