"""Independent hand-authored cases; not expectations copied from a driver."""
import importlib.util
import hashlib
from pathlib import Path

import pytest

from agent_lab.gate_identity import RegisteredOperation
from agent_lab.gate_runtime import emit_gate
from test_gate_identity import specimen


@pytest.mark.parametrize("budget,decision,terminal,value,used", [
    (1, None, "FAILED_BUDGET", 1, 1),
    (2, "approved", "FAILED_BUDGET", 1, 2),
    (2, "rejected", "REJECTED", 1, 2),
    (3, None, "PENDING", 1, 2),
    (3, "approved", "DONE", 2, 3),
    (3, "rejected", "REJECTED", 1, 2),
])
def test_offline_checker_compares_actual_emitted_graph_with_expected_cases(tmp_path, budget, decision, terminal, value, used):
    assert importlib.util.find_spec("agent_lab.gate_conformance") is not None, "Offline checker missing"
    from agent_lab.gate_conformance import GateCase, GateExpected, check_gate
    spec = specimen(budget)
    ops = {"add": RegisteredOperation("add_int_v1", 1)}
    version = emit_gate(spec, ops, store=tmp_path / "store")
    prefix = [("before", "done", "review", 1, 1)]
    if budget == 1:
        prefix.append(("review", "FAILED_BUDGET", "FAILED_BUDGET", 1, 1))
        pending = GateExpected(terminal="FAILED_BUDGET", value=1, used=1, remaining=0, events=tuple(prefix))
    else:
        prefix.append(("review", "pending", "PENDING", 2, 1))
        pending = GateExpected(terminal="PENDING", value=1, used=2, remaining=budget-2, events=tuple(prefix))
    if decision:
        prefix.append(("review", decision, "after" if decision == "approved" else "REJECTED", 2, 1))
        if decision == "approved":
            prefix.append(("after", "done" if budget == 3 else "FAILED_BUDGET", terminal, used, value))
    expected = GateExpected(terminal=terminal, value=value, used=used, remaining=budget-used, events=tuple(prefix))
    case = GateCase(name="case", reference_decision=decision, graph_decision=decision,
                    pending=pending, expected=expected)
    report = check_gate(spec, ops, version, (case,))
    assert report.passed, report.findings
    assert len(report.results) == 2
    assert all(result.result.terminal == terminal for result in report.results)
    for observation in report.results:
        rows = sorted(Path(observation.audit_dir).glob("[0-9]*.json"))
        assert rows
        assert observation.audit_head == hashlib.sha256(rows[-1].read_bytes()).hexdigest()
        assert observation.audit_head == observation.result.head
    # Matching driver outputs are insufficient when a hand-authored oracle differs.
    wrong = case.model_copy(update={"name": "wrong", "expected": expected.model_copy(update={"value": 99})})
    assert not check_gate(spec, ops, version, (wrong,)).passed
    if decision == "approved":
        split = case.model_copy(update={"name": "independent", "graph_decision": "rejected"})
        mismatched = check_gate(spec, ops, version, (split,))
        assert not mismatched.passed
        assert any("independent drivers differ" in finding for finding in mismatched.findings)
    assert not check_gate(specimen(budget + 1), ops, version, (case,)).passed
