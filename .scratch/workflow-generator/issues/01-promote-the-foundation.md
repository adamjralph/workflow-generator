# 01: Promote the foundation and initialise the repo

**What to build:** The product repo is under version control, and the foundation's semantics are importable as the product's core rather than copied. Every later ticket builds on one shared implementation, and the foundation's own test suite passes from the product repo.

**Blocked by:** None (can start immediately).

**Source:** `spec.md` → "Build on the foundation"; `CONTEXT.md` §4; ADR-0002.

**Status:** ready-for-agent

- [ ] `workflow-generator` is a git repository with an initial commit.
- [ ] The foundation's typed state, transition allow-list, terminal states, budget, judgment sources, approval store, and run log are importable from the product as one core.
- [ ] The foundation's full test suite runs from the product and is green (the two live-Jev skips excepted).
- [ ] Reaching this state reads or writes no Hermes source, configuration, or authentication.
