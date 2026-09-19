# Conformance is structural and behavioural, never semantic

A generated workflow is model-driven and therefore probabilistic, and no mechanical check can decide
whether it does what the user *meant*. Conformance therefore asserts only what a check can prove:
that the runnable workflow matches the spec **structurally** (node types, edges, transitions,
budgets, terminals, digests) and **behaviourally** (a recorded run replays through both drivers with
identical events and digests). Semantic correctness is explicitly out of scope, and the word
"conformant" must never be read as "correct". We chose this over a looser "looks right" claim so that
"trusted" stays falsifiable.

## Considered Options

- **Structural only** — provable, but too weak to catch driver drift.
- **Semantic** — not mechanically checkable; it would make "trusted" unfalsifiable.
