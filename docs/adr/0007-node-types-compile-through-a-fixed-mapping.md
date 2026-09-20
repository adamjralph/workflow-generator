# The five node types compile through a fixed, documented mapping

The five spec node types compile to the foundation through a **fixed, documented mapping**: each spec
node becomes a foundation node/stage, typed edges become allow-listed transitions, `Judgment` → the
judgment call, `Decision` → a code router, `Gate` → the approval node, `Transform` → deterministic
work, `Loop` → a bounded retry with an exit predicate; terminals and budgets are declared in the
spec. We chose a fixed mapping over per-emitter freedom so the mapping is itself testable and
target-independent. The foundation's existing six nodes become one *instance* of the mapping
(intake/verify are Transform, classify is Judgment, route is Decision, await_approval is Gate), not
the model.

## Accepted amendment

[ADR 0010](0010-explicit-model-operations-and-offline-replay.md) permits explicitly
declared model operations on Transform. Ordinary callable bindings remain deterministic;
Judgment remains the narrow classifier. No additional node kind is introduced.

## Considered Options

- **Reuse the foundation's six nodes as the spec model** — conflates the spec with one runtime.
- **Leave mapping to each emitter** — untestable, and target drift would be invisible.
