# 35: Check declared string values in produced JSON

**Status:** technically complete under Adam's continued-development authorization (2026-10-05); technically complete under delegated review.
**Boundary:** offline only. No repair, alert delivery, live calls, source changes or publication permissions.

## Scope

Extend ticket 34 with immutable declarations of exact allowed string values for
required top-level fields. Use the existing LinkedIn Guardian vocabulary
(`Approved`, `Changes requested`, `Blocked`) and `copy-only` scope in synthetic,
public-safe output fixtures. This demonstrates a representative contract without
claiming a live or complete LinkedIn workflow acceptance.

## Verified criteria

- Typed constraints are admitted before execution; nonempty distinct string sets,
  distinct field constraints and membership in required fields are enforced, including copied models.
- Both existing drivers check the actual saved file against literal, case-sensitive
  values; null, booleans, numbers, arrays and objects fail constrained fields.
- Missing constrained fields report `missing_field` once; unexpected values report
  `unexpected_value` naming the field, without embedding observed content.
- Duplicate JSON keys fail visibly rather than resolving conflicting values silently.
- Saved declaration and verdict retain allowed values, step/run attribution and
  exact-byte digests. Existing field-presence and bounded unsafe-file behavior remains tested.
- Focused and full offline regression, typing and independent review verify the slice.

## Evidence

See [ticket 35 evidence](../../../docs/outcome-ticket35.md) for exact commands,
observed full-suite result, corrected environment failures and independent review.
Adam did not personally review this slice; parent assessment is next.

## Remaining

No repair or alerts; V2–V5 decisions and ticket 19's live/default-selection gaps
remain. Contract relaxations in the outcome pillar apply to future pillar work;
ticket 19's historical two-call proof and no-retry evidence remain intact.
