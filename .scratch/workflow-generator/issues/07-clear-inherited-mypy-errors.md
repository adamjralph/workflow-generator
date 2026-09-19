# 07: Clear inherited mypy errors without weakening runtime validation

**What to build:** Resolve the 11 inherited mypy errors in `agent_lab/encoding.py`,
`agent_lab/judgment.py`, and `agent_lab/workflow.py`. Distinguish annotation-only
mismatches from runtime assumptions, pin meaningful failure cases with tests,
and restore a green typechecking baseline without hiding errors.

**Source:** Adam's ticket-05 acceptance and request for a cleanup ticket;
`docs/measurement-ticket05.md` → Verification; `CONTEXT.md` §2.6.

**Status:** resolved — accepted and closed

## Scope

The current `.venv/bin/python -m mypy agent_lab` reports:

- `encoding.py`: normalization form is typed as arbitrary `str`, but
  `unicodedata.normalize` expects one of four literal forms.
- `judgment.py`: SDK input/output token counts may be `None`; answer objects are
  unions whose expected variants are assumed without narrowing; `_build` passes
  an arbitrary `str` into the judgment's restricted source field.
- `workflow.py`: verification dereferences an optional judgment without an
  explicit check; the routing loop assigns an optional lookup to a variable
  inferred as non-optional.

These are typechecker findings, not eleven confirmed runtime defects. Verify
actual behavior before deciding whether each needs validation or only a more
precise annotation. In particular, inspect the installed SDK's answer and usage
contracts rather than asserting types through unchecked casts.

## Acceptance criteria

- [x] `.venv/bin/python -m mypy agent_lab` passes with zero errors.
- [x] No blanket ignores, disabled checks, broad `Any`, unchecked casts, or
      dependency downgrades are used merely to silence diagnostics.
- [x] Jev response variants and nullable token counts have explicit handling
      consistent with the SDK contract; unavailable usage is not silently
      represented as measured zero.
- [x] Malformed/missing judgment data fails explicitly and preserves the
      workflow's recorded failure-terminal behavior rather than leaking an
      accidental attribute error or allowing unsafe continuation.
- [x] Normalization forms and judgment-source annotations express the supported
      values without weakening existing runtime validation.
- [x] Routing behavior, budgets, digest-bound approvals, and plain/graph driver
      equivalence are preserved.
- [x] Meaningful runtime weaknesses are reproduced with failing offline tests
      before fixes, at public seams confirmed with Adam before writing tests.
- [x] Targeted tests and the full offline suite pass; optional live calls remain
      opt-in and no live Hermes source/configuration/authentication/state is edited.
- [x] Independent Standards and Spec reviews are completed and recorded.

## Boundaries

No new workflow features, diagnosis baseline management, Hermes activation
changes, or unrelated refactors. Do not suppress the errors and call the work
complete. Update the README/handoff's typechecking status only after verification.

## Answer

Implemented with Adam's explicit authorization and confirmed judgment/driver seams;
review baseline `70624c1`. Evidence: `docs/typechecking-ticket07.md`.
Mypy: zero errors in 14 files. Offline suite: 158 passed, 3 optional skips.
Independent Standards/Spec reviews completed and recorded; overflow finding
reproduced test-first and fixed. No Hermes edits or live calls.

## Comments

Adam explicitly accepted ticket 07 after implementation, verification and independent
reviews. Closed at that approval. Implementation commits: `2077d7d`, `12db524`.

Adam requested creation of this cleanup ticket while explicitly accepting and
closing ticket 05. This records future work; it does not authorize starting
implementation. Confirm test seams and review baseline before beginning.
