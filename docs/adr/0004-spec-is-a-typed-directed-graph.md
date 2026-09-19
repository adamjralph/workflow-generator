# The spec is a typed directed graph of the five node types

A spec is a **directed graph** whose nodes are instances of the five fixed node types (Judgment,
Decision, Gate, Transform, Loop) and whose edges are typed moves between them, with declared budgets
and terminals. It is deliberately *not* a linear route, and it is *not* the foundation's
stage/transition shape: the foundation's stages are one **compilation target**, not the model.
We chose the graph because parallel branches, joins, and loops are already proven necessary, and a
linear model cannot express them. The concrete serialization format is not fixed by this decision.

## Considered Options

- **Linear route only** — simplest, but cannot express the parallel work the project exists to
  support.
- **Adopt the foundation's stage/transition shape directly** — conflates the spec with one runtime
  and would prevent other targets.
