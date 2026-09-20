# Ticket 11 — recorded Judgment routes

Review baseline: `467f1b2f7e76f8288892650c0bdf70462df0598b`.

## Public contract

`compile_reference`, `generate_graph`, and `check_conformance` accept an optional
`judgments` mapping keyed by **Judgment node ID**, separately from opaque
Transform/Decision `bindings` keys. Each value is
`JudgmentBinding(source, assessment)`, imported from `agent_lab.reference`:

```python
from agent_lab.judgment import RecordedSource
from agent_lab.reference import JudgmentBinding

reference_judgments = {
    "judge": JudgmentBinding(RecordedSource(recording_path), lambda state: state.assessment),
}
candidate_judgments = {
    "judge": JudgmentBinding(RecordedSource(recording_path), lambda state: state.assessment),
}
# generate_graph(spec, state_type=State, bindings={}, judgments=candidate_judgments)
# check_conformance(spec, generated.candidate, state_type=State, bindings={},
#                   judgments=reference_judgments, cases={"business": State(...)},
#                   evidence_dir=caller_named_directory)
```

The adapter must deterministically return assessment text from the declared frozen
Pydantic state. Each invocation receives a detached snapshot. Judgment does not
write into retained state. Compilation copies declarations and binding maps and
checks every declaration, including unreachable ones, without calling adapters
or sources. Explicit bindings remain trusted local code, not a sandbox.

Only `review_follow_up`, `payment_follow_up`, and `not_a_fit` options execute.
Other options remain valid conceptual spec declarations but return located
`unsupported_options` compilation findings. Missing/invalid bindings return
`unbound_reference`; no runnable artifact is returned.

The existing `JudgmentSource.judge(assessment)` boundary is unchanged. Returned
models are strictly revalidated without coercing unchecked string/boolean fields,
then routed only on a declared Intervention. One budget
step is reserved before the adapter/source. Budget refusal does not call either;
invalid results and ordinary adapter/source errors record FAILED_VALIDATION.
Terminal routes cost nothing and stop immediately.

Every Judgment event adds `judgment` (the full validated model, or null) and
`assessment_sha` (SHA-256 of exact UTF-8 source input, or null if unavailable).
Valid but undeclared choices retain their evidence while failing validation.
Input digests prevent differing adapters from silently agreeing through a fixed
stub; they avoid adding raw business assessments to logs. Choice, confidence,
review-gap probability and source provenance are never normalized away.

## Offline inputs and replay ownership

Supply separate equivalent recorded/stub sources for the two drivers. The checker
rejects known `JevSource` instances and directly shared source objects with
`ValueError`, before behavior or evidence creation. This includes unreachable
Judgment declarations. Custom sources must be offline and must not conceal a
shared cursor behind separate wrappers; trusted local bindings cannot be sandboxed.

Sources are caller-owned inputs, not silently cloned/reset. A stateful source's
cursor advances across ordered cases. To repeat a check, supply fresh equivalent
sources **and generate the independently supplied candidate with its own fresh
source**. Stateless `RecordedSource`/`StubSource` instances can be reused across
checks (but not shared between drivers). Compilation never advances replay.

The plain control loop remains authoritative; graph scheduling uses framework
steps/branches, sharing only invocation/audit mechanics. Structural checks inspect
actual candidate configuration including options and unreachable declarations;
the checker runs that candidate, never regenerates a replacement. Same run IDs,
separate fresh logs, strict final state, terminal/spend, every event, raw bytes and
digests remain required. Audit I/O failure stops work and yields no passing report.
Evidence locations retain the existing outside-Hermes/project protection.

A pass applies only to this restricted target and the supplied cases. It proves
neither semantic correctness nor universal conformance. Gate/Loop/Fork execution,
arbitrary judgment vocabularies, live checking and arbitrary state writes remain
out of scope.

## Verification

Public-seam tests: `tests/test_judgment_routes.py` and
`tests/test_judgment_routes_failures.py`. Red/green cycles reproduced missing
Judgment support, shared/live-source acceptance, and differing assessment inputs
silently passing. Additional tests cover independent stateful replay, repeated
exact logs, full evidence drift, all-declaration checking, invalid judgments,
recording mismatch, budgets, detached state, and real filesystem audit failures.
Existing admission tests now expect `unsupported_options` rather than
`unsupported_node` for conceptual arbitrary-option Judgment declarations.

Final verification after review fixes:

- Judgment public-seam files: **55 passed**.
- Full `.venv/bin/pytest -q`: **391 passed, 3 skipped** (two live Jev tests and
  optional real-Hermes integration; no live calls were made).
- `.venv/bin/mypy agent_lab`: **zero errors, 19 source files**.
- `git diff --check`: clean. `graft build`: refreshed.

## Independent review

Standards and Spec reviewers ran in parallel against the approved baseline and
implementation commit `2e9848e`.

### Standards

Zero documented-standard violations. Two optional heuristics:

1. Possible Duplicated Code: the short node-reference selection in generation
   and structural comparison. Retained: a two-line fixed mapping does not yet
   justify another abstraction, and scheduling remains deliberately independent.
2. Possible Feature Envy: checking reads the candidate's private Judgment source
   map after integrity inspection. Retained: this is an internal owned-target
   boundary; adding a public source-inspection API solely for one internal check
   would expand the supported surface unnecessarily.

### Spec

One substantive finding: non-strict model revalidation coerced unchecked string
choices/confidence/probability into valid evidence, permitting a false pass.
Seven new cases reproduced it before the fix. Commit `cfa2151` uses strict
revalidation at the new execution boundary without changing business sources.
Independent follow-up review confirmed resolution with no remaining substantive
finding in scope; 55 focused tests and mypy passed there as well.

Summary: Standards 0 hard findings, 2 optional heuristics retained; Spec 1 defect
fixed and independently confirmed. Ticket awaits human acceptance.
