# 01: Promote the foundation and initialise the repo

**What to build:** The product repo is under version control, and the foundation's semantics are importable as the product's core rather than copied. Every later ticket builds on one shared implementation, and the foundation's own test suite passes from the product repo.

**Blocked by:** None (can start immediately).

**Source:** `spec.md` → "Build on the foundation"; `CONTEXT.md` §4; ADR-0002.

**Status:** resolved

- [x] `workflow-generator` is a git repository with an initial commit.
- [x] The foundation's typed state, transition allow-list, terminal states, budget, judgment sources, approval store, and run log are importable from the product as one core.
- [x] The foundation's full test suite runs from the product and is green (the two live-Jev skips excepted).
- [x] Reaching this state reads or writes no Hermes source, configuration, or authentication.

## Answer

Closed at Adam's explicit request. Implementation landed on `main` as `cddadc6`,
following baseline `e03a19d`. `agent_lab/` is the single repo-local runtime core;
see `docs/foundation/README.md` for provenance and verification evidence.

Closure verification: `AGENT_LAB_JUDGMENT=stub .venv/bin/python -m pytest -q`
reported **65 passed, 2 optional live-Jev skips**. No Hermes access was needed.
Ticket 02 is reserved for a fresh session; tickets 03–06 were not started.
