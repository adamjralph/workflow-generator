# Ticket 07 — typechecking and judgment validation

Baseline: `70624c1`. Adam confirmed the `JevSource.judge()` and plain/graph driver
public test seams before tests were written, and authorized implementation.

## Findings and changes

- `normalise` accepted a broad string annotation; runtime already delegates form
  validation to `unicodedata.normalize`. Narrowed to the four supported literals,
  leaving runtime behavior unchanged.
- `_build` now declares the same source literals as `Judgment`; Pydantic's runtime
  source validation is unchanged.
- Inspected installed **typesafe-sdk 0.6.0** classes (`ChoiceAnswer`, `NoulAnswer`,
  `ScoreAnswer`, `SystemOneResponse`, `Usage`). Responses contain a union of answer
  variants; SDK dispatch skips unknown future variants. Missing keys therefore
  need explicit handling, not casts. Nullable usage means *not reported*; `None`
  is retained, separately from measured zero.
- Missing/wrong SDK answers previously leaked `KeyError`/`AttributeError`.
  They now raise `JudgmentError`, recorded by the existing shared step boundary.
- Invalid source objects and unchecked model copies are revalidated before routing.
  Judgment-dependent stages explicitly reject missing/malformed judgments, including
  verification and resumed approval. No broad exception catch was added to drivers.
- Malformed JSON, non-object recordings, missing fields and invalid values previously
  leaked decoding/key/type exceptions. They now produce recorded validation failures.
- The routing lookup uses a separate optional local and narrows it before assignment;
  routing semantics are unchanged.

## Red → green evidence

`tests/test_judgment_validation.py` uses real SDK answer/response types and an offline
client double only at the external SDK boundary. Observed before each fix:

1. Four missing/wrong SDK-answer cases failed with key/attribute errors.
2. Four invalid source judgment cases failed with attribute errors through both drivers.
3. Five missing state judgment cases failed with assertion/attribute/value errors.
   Plain exercises route/prepare/verify/approve; graph exercises its supported
   approval re-entry, not an invented intermediate resume interface.
4. Eight malformed recording cases failed with JSON/key/type/attribute errors.

Nullable usage already behaved correctly at runtime; three characterization cases
pin unknown, partially reported, and measured-zero usage while the annotation is fixed.
Two driver cases prove SDK failures become recorded terminals and spend two steps.

## Verification

- `.venv/bin/python -m mypy agent_lab`: **zero errors, 14 source files**.
- Targeted new regression file: **26 passed**.
- Full `.venv/bin/python -m pytest -q`: **156 passed, 3 skipped** (two live Jev
  calls and the optional real-Hermes loader check).
- Existing routing, budget, digest-bound approval and driver-equivalence tests pass.
- No dependencies changed; no ignores/casts/check disabling; no live Hermes edits.

## Independent review

Review baseline `70624c1`; independent Standards and Spec reviewers run in parallel.
Results will be recorded after review.
