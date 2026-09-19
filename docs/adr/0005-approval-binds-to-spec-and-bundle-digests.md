# Approval binds to both the spec digest and the emitted bundle digest

An approval binds to the **exact spec digest and the exact emitted bundle digest**, each re-derived
at the gate and never trusted from stored state. Binding to the spec alone would let a changed
emission inherit consent; binding to the bundle alone would let a changed design inherit consent and
would not survive a legitimate re-emission. Both must match, and a rejection of either stops the run.
This extends the foundation's exact-digest approval rule to a two-artifact design.

## Considered Options

- **Spec digest only** — an edited emission could ship under the same approval.
- **Bundle digest only** — a changed design could ship, and every re-emission would need fresh
  approval even when the design is unchanged.
