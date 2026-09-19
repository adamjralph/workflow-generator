# Promoted foundation — ticket 01

## Origin and ownership

Adopted from `~/Projects/agent-workflow-lab`, branch `main`, commit
`ce34093a2bf6dec23a837f6961a50a3656569642`. Its MIT notice is retained in
[LICENSE](LICENSE), covering the adopted files.

`agent_lab/` is now the product's one local runtime implementation, retaining the
existing import namespace and public boundary. Later product code imports it;
it must not copy state, routing, accounting, judgment, or approval logic into
separate front doors. This is a source promotion, not a wrapper importing a
sibling checkout, a symlink, or a runtime dependency on the teaching lab. The
source checkout is left unchanged as historical evidence; it is not a second
implementation used by this product.

Adopted byte-for-byte:

- All nine `agent_lab/*.py` modules.
- All three `lessons/lesson_*/test_*.py` files (67 collected tests).
- `.env.example`, the synthetic Northside case and its recorded judgment.

Root `conftest.py` retains its import-path setup, with its docstring updated to
name `pytest.ini`. The recordings README omits the unimported demo script.

Not adopted: the lab's `.env`, virtualenv, run artifacts, scripts, walkthrough,
spikes, or build/distribution metadata. `requirements-dev.txt` captures the four
measured direct dependency versions for local testing only; `pytest.ini` preserves
the lab's discovery, root-import, and warning settings. Neither chooses product
packaging or a distribution name.

## Boundary

- `agent_lab.state`: frozen typed state, transition allow-list, terminals, budget.
- `agent_lab.judgment`: `JudgmentSource`, `JevSource`, `RecordedSource`, `StubSource`.
- `agent_lab.approvals` and `agent_lab.runlog`: injected, explicit-path stores.
- `agent_lab.workflow`: `Deps`, shared node/step semantics, `run_plain` (reference).
- `agent_lab.graph_workflow`: `run_graph`, delegating to those same semantics.

Imports perform no credential discovery. Live Jev remains explicitly opt-in;
offline tests use stubs/recordings and temporary fake credential files. Nothing
in ticket 01 accesses Hermes source, config, authentication, or board/profile
state. Store paths remain caller-supplied and must stay outside Hermes; this is
not a claim that the later diagnosis read-only boundary has been implemented.

## Verification

From the product root, using its own `.venv` (Python 3.14.7):

```bash
AGENT_LAB_JUDGMENT=stub .venv/bin/python -m pytest
```

Expected foundation result: **65 passed, 2 skipped**, the two live-Jev tests only.
The workflow file first failed collection with `ModuleNotFoundError: agent_lab`
before promotion, then passed all 32 tests after the core was added. The other
files passed 14 encoding tests and 19 judgment tests with the two live skips.
All loaded `agent_lab` modules were checked to resolve under this repository.
Byte comparison confirmed all 12 core/test files match the source. `pip check`
reported no broken requirements.

The full suite also passed **65/2** in a one-off Bubblewrap sandbox with `/home`
hidden except for this read-only checkout, a temporary `/tmp`, and no network.
Thus neither the sibling lab nor Hermes was accessible to that test process:

```bash
bwrap --ro-bind / / --dev /dev --tmpfs /home \
  --ro-bind "$PWD" "$PWD" --tmpfs /tmp --unshare-net --die-with-parent \
  --chdir "$PWD" --setenv AGENT_LAB_JUDGMENT stub \
  --setenv PYTHONDONTWRITEBYTECODE 1 \
  .venv/bin/python -m pytest -p no:cacheprovider
```

This is ticket 01 verification, not the diagnosis adapter's future boundary test.

An exploratory typecheck with `mypy==2.3.1` found **11 inherited errors in 3 files**;
the same checker against the original checkout produced the same errors. No
clean static-typecheck claim is made. To reproduce (mypy is optional tooling):

```bash
.venv/bin/python -m pip install mypy==2.3.1
.venv/bin/python -m mypy agent_lab
```

Errors concern `normalise`'s form annotation, SDK answer unions/optional usage,
`Judgment.source`'s literal annotation, optional judgment access in verification,
and an optional next-node assignment. These are not suppressed or changed as
part of this semantics-preserving promotion.

## Limits deliberately retained

This is the foundation runtime, not the unticketed spec/conformance engine.
Its business-assessment route is an existing instance, not a new general graph
model. Approval still binds the foundation's run/draft digest, not a spec/bundle
pair; its JSON/JSONL formats do not decide spec serialization or the future
immutable artifact store.

Known parallel budget/sequence and shared-state defects remain for ticket 02.
The existing linear drivers do not claim parallel-safe accounting. Existing
exception behavior is retained too (for example, invalid intake raises; a
`JudgmentError` becomes recorded `FAILED_VALIDATION`). The green inherited suite
is not proof of all future product trust requirements or production readiness.
No diagnosis adapter, metrics, Hermes integration, generator, or plugin is added.
