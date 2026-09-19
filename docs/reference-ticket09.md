# Ticket 09 — deterministic plain reference slice

Adam approved the restricted contract, frozen Pydantic state/result contract,
public test seam and review baseline `e6c1c9bc3d7920c518f210e05bcc271b685eebb8`.

## Public API

`agent_lab.reference.compile_reference(spec, state_type=State, bindings=bindings)`
returns `Compilation`: a `plan` with no findings, or no plan and located findings.
Ticket 08 findings are preserved; target-specific `CompileFinding` categories are
`unsupported_node`, `unsupported_edge`, `unbound_reference`,
`missing_safety_terminal` and `invalid_state_type`.

All declarations are checked, including unreachable ones. Only Transform,
Decision and Route are executable. Both `FAILED_VALIDATION` and `FAILED_BUDGET`
must be declared. Compilation validates/copies declarations and copies the binding
map; references are exact opaque keys, never imports or expressions. Compilation
does not invoke bindings. Callables themselves are trusted local code: mutating a
callable's closure or doing external I/O violates the deterministic binding
contract; this API is not a sandbox.

The agreed seam is **spec + bindings + typed input → reference result + trace**.
After checking `compilation.plan is not None`, call:

```python
result = compilation.plan.run(initial_state, run_id="example-1", log=run_log)
```

- `state_type` is a caller-defined frozen Pydantic model. Initial state and
  Transform states must be instances of exactly that type. State snapshots are
  strictly revalidated and detached by deep copying Python data; no persistent
  state/spec serialization format is defined. State validators/serializers must
  themselves be deterministic and support Python round-trip validation.
- A Transform callable receives a snapshot and returns
  `TransformResult(new_state, outcome)`. A Decision callable receives a detached
  snapshot and returns a case string. Mutating nested snapshot data cannot change
  the caller's input or the retained state through a Decision.
- Labels must be declared strings. There is no coercion or default route. New
  state is committed only after validating the complete Transform result.
- `ReferenceResult` exposes `state`, `terminal`, `used_steps`, and `trace`.
  `trace` contains the run's persisted `RunEvent` records, also readable through
  `RunLog.read()`. Records identify arbitrary spec node IDs, kind, selected label,
  target/failure, terminal, used steps and maximum steps. They introduce no time
  or random fields. Compare traces excluding only `run_id` across independent runs.

## Foundation integration and failure policy

`RunAccounting.reserve(run_id, budget)` extracts the existing reservation
mechanics without business fields; existing `spend(RunState)` delegates to it.
The existing `Budget.spend` still enforces the cap. Every node invocation reserves
one step, including Decisions and failing bindings. A refused invocation records
`FAILED_BUDGET` without spending or invoking. Routing to a terminal is free.
Ordinary binding exceptions and malformed results record `FAILED_VALIDATION`;
exception text is deliberately excluded from the deterministic trace.

The plain state-machine loop is authoritative. No graph emitter, conformance
verdict, scheduler, approval store or second event writer is introduced. Existing
`Deps`, business workflow and plain/graph execution behavior are unchanged.

`RunLog.append_next` remains the only sequence allocator for reference events.
`RunLog.fresh_run` holds a nonblocking sidecar file lock for the reference pass;
parallel reference passes on the same log are refused rather than queued.
Already recorded identities in that log are refused, including incomplete runs;
there is no resume API. Use one audit log as the identity scope and choose a fresh
identity for each independent execution. The sidecar contains no events or
sequence counter. Existing business drivers do not opt into this restriction.

Malformed initial state and invalid/reused run identities raise `ValueError`
before invoking bindings. Audit filesystem errors raise `AuditError` and stop
further work; malformed existing logs also fail visibly. No result is returned
claiming persistence after a failed write or read. Process interruption,
crash-durable execution and recovery from partial audit writes are not promised.

## Evidence

`tests/test_reference.py` contains the hand-authored Transform → Decision example,
with arbitrary node identities and both positive/negative routes. Tests operate
through compilation/execution and the public log reader, with deterministic local
bindings and real temporary filesystem failures, not compiler/dispatch mocks.

Observed red → green slices: missing module → typed route execution; admitted
unsupported/unbound declarations → complete target rejection; escaping malformed
results/exceptions → recorded failures; budget exception → recorded refusal;
mutable input/result sharing and reused identities → isolated fresh execution;
audit errors → explicit failure with no later binding execution.

Reproduce offline:

```bash
.venv/bin/python -m pytest -q tests/test_reference.py
.venv/bin/python -m mypy agent_lab
AGENT_LAB_JUDGMENT=stub .venv/bin/python -m pytest -q
```

Final verification and two-axis review results are recorded below when complete.
