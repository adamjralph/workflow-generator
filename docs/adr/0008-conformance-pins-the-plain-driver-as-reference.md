# Behavioural conformance pins the plain driver as the reference execution

Conformance compiles the spec to a **reference execution** — the plain state-machine driver — and
requires the emitted artifact (the pydantic-graph driver) to behave identically on a recorded run:
same events, same digests. We chose this over structural-only comparison because it catches semantic
drift in the emitter, and over a golden file because a golden file can silently encode the emitter's
own bug. It also fixes which implementation is authoritative when the two disagree, which the
foundation's driver-equivalence tests require but do not name.

## Considered Options

- **Structural comparison only** — cannot catch an emitter that emits the right shape but wrong
  behaviour.
- **Golden-file comparison** — freezes whatever the emitter produced, including its bugs.
