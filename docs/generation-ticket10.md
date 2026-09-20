# Ticket 10 — deterministic generation and conformance slice

Implements the approved in-memory Transform/Decision + Route target and checking
seam. The authoritative plain reference remains independent of graph control
flow (ADRs 0001, 0004, 0007 and 0008). See [ticket 09](reference-ticket09.md)
for frozen state, trusted deterministic bindings, reservation and audit rules.

## Public APIs

```python
from pathlib import Path
from agent_lab.generation import generate_graph
from agent_lab.conformance import check_conformance

# spec, State, bindings and typed initial states are supplied by the caller.
generation = generate_graph(spec, state_type=State, bindings=bindings)
if generation.candidate is not None:
    report = check_conformance(
        spec, generation.candidate, state_type=State, bindings=bindings,
        cases={"positive": State(value=0), "negative": State(value=-2)},
        evidence_dir=Path("/tmp/workflow-evidence"),
    )
    print(report.passed, report.findings)
```

`generate_graph` returns `Generation`: a runnable `candidate` or located admission/
compilation findings, never a partial candidate. Each spec node becomes a graph
step; framework decisions select subsequent nodes. The graph does not call the
whole plain runner. Both drivers share foundation node invocation, reservation,
snapshot and event writing mechanics, not their control loops.

`GraphCandidate.run(initial, run_id=..., log=RunLog(...))` returns the same
`ReferenceResult` shape as the plain driver: state, terminal, used steps and
persisted trace. Binding maps and declarations are copied. The candidate's
`inspect_structure()` reconstructs configuration used to build each execution,
including unreachable nodes; it is not a copied authoritative manifest.
Configuration is immutable and unsupported executable/configuration mutations
are rejected. This integrity boundary is not a Python sandbox. To deliberately
alter a candidate, generate another candidate from changed declarations or
bindings and supply it independently to the checker.

`check_conformance(spec, candidate, *, state_type, bindings, cases, evidence_dir,
protected_roots=())` compiles its own plain reference from the authoritative spec
and **reference** bindings. It accepts only the exact owned `GraphCandidate`
type, not subclasses or duck-typed claims. It invokes captured public inspection,
which checks candidate integrity even if a caller replaces the inspection method.
The independently supplied candidate is executed, never silently regenerated.

`ConformanceReport` contains:

- `attempted`: names whose execution has begun, in caller order;
- `completed`: names for which both runs and every evidence comparison completed
  (completion does not imply agreement);
- `evidence`: `CaseEvidence(case, run_id, reference_log, candidate_log)` paths for
  attempted cases, including partial/missing evidence after failure;
- `findings`: admission/compilation findings or `ConformanceFinding(code, path,
  message)`; checker codes are `structural_mismatch`, `behavioral_mismatch`,
  `unsupported_candidate`, `empty_cases`, and `incomplete`;
- derived `passed`: nonempty completed cases, every attempted case completed,
  and no findings. An empty case set never passes.

## Comparison and evidence

Before bindings execute, compare entry, budget, terminals, every node identity,
kind, opaque operation/value reference, outcome vocabulary and every route,
including unreachable declarations. Declaration, terminal and vocabulary order
is ignored where it has no execution meaning. Structural findings use identity
locations such as `("nodes", "choose")` or `("edges", "choose", "positive")`;
compilation findings retain their original declaration locations. Different
state types also prevent execution.

Each check creates a unique `check-*` subdirectory in the caller's evidence
location. Case names are nonblank strings used only as report labels, never path
components. Index-derived run IDs are identical for the two drivers and scoped
to separate fresh logs. Repeat checks use different paths but reproduce identical
bytes for deterministic cases in the same order.

For each case compare final state (strictly validated by the owned drivers,
with type-sensitive recursive Python-data comparison), terminal, used steps,
all ordered persisted `RunEvent` fields, exact public `RunLog.read_bytes()` and
`RunLog.digest()` results. No normalized digest, spec digest or bundle identity
is invented. Public `read_bytes()` is required: a missing log cannot masquerade
as an empty trace or empty digest. Behavioral paths name the case and differing
field, e.g. `("cases", "positive", "state")`.

Binding exceptions/malformed results and budget refusal are comparable recorded
terminal outcomes, not incomplete checks. `AuditError` or filesystem `OSError`
produces an `incomplete` finding at `evidence_dir` or the case's `reference`,
`candidate`, or `comparison` phase and immediately stops the entire check.
Evidence paths identify intended locations, not a promise that writing succeeded.
Invalid inputs/freshness violations retain `ValueError`; unexpected programming
errors propagate rather than becoming mismatch findings.

Evidence destinations are resolved before writing, rejecting descendants of
`~/.hermes`, configured `HERMES_HOME`, project source, loaded `hermes_cli` source,
and optional explicit `protected_roots`. This follows diagnosis's protected-root
convention, including symlink resolution and host discovery without importing
Hermes. Callers must provide additional undiscoverable Hermes source/install
locations through `protected_roots`. No Hermes source/config/auth/live-state
writes, live model calls, packaging or persistent bundle are introduced.

Passing is evidence for this restricted target and supplied cases only: not
semantic correctness, arbitrary Python equivalence, universal workflow
conformance, savings or production readiness. Bindings and state validators/
serializers remain trusted deterministic local code. Crash durability,
recovery, model replay, Gate/Loop/Fork execution and full artifact identity remain
out of scope.

## Focused checker TDD evidence

Approved seam: authoritative spec + independent candidate + explicit reference
bindings + named typed cases → typed report + real persisted logs.

Observed red → green cycles in `tests/test_conformance.py`:

1. Missing conformance module → branching same-ID/separate-log evidence (1 pass).
2. Altered binding incorrectly passed; empty cases lacked findings → behavioral
   comparisons and explicit empty-case finding (3 pass).
3. Changed declarations executed bindings; unsupported candidates raised or ran
   → complete order-independent structure checks and integrity admission (14 pass).
4. Real directory-at-log-path audit failures escaped; protected destinations
   were accepted → located incomplete stopping and protected-root policy (22 pass).
5. Strict union state `True` compared equal to `1`; invalid case names were
   accepted → type-sensitive comparison and input validation (40 pass).

Additional public-seam regressions cover compilation rejection, unreachable
unsupported declarations, short/exact budgets, malformed state/label/exception
outcomes, immediate terminal stopping, repeat fresh evidence, missing persisted
logs, method/configuration tampering, vocabulary order, explicit freshness
violations and propagating programming errors. Filesystem failures use actual
temporary files/directories, not internal dispatch/compiler/log mocks.

Latest focused checker verification:

```text
.venv/bin/python -m pytest -q tests/test_conformance.py
45 passed
.venv/bin/python -m pytest -q tests/test_conformance.py tests/test_generation.py tests/test_reference.py
92 passed
.venv/bin/python -m mypy agent_lab
Success: no issues found in 19 source files
git diff --check
(clean)
```

Mypy ran throughout the cycles; one intermediate missing list annotation was
fixed. Full-suite verification, graph refresh and final review are intentionally
left to the coordinating parent task; this worker made no commits or user-file
changes.
