"""Ticket 36: one bounded local repair through both independent drivers."""
import hashlib
import json
import os
from pathlib import Path

import pytest
from pydantic import BaseModel, ConfigDict

from agent_lab.remedy import run_with_remedy
from agent_lab.reference import TransformResult
from agent_lab.spec import JsonOutputExpectation, Route, TransformNode, WorkflowSpec


class State(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)
    value: int = 0


def workflow():
    return WorkflowSpec(entry="produce", budget=1,
        nodes=(TransformNode(id="produce", operation="write",
            expected_output=JsonOutputExpectation(file="result.json", required_fields=("title", "body"))),),
        edges=(Route(source="produce", outcome="done", target="COMPLETED"),),
        terminals=("COMPLETED", "FAILED_VALIDATION", "FAILED_BUDGET"))


def factory(payload, calls, outcome="done"):
    def bindings(output):
        def write(state):
            calls.append(state.value)
            (output / "result.json").write_text(json.dumps(payload))
            return TransformResult(State(value=state.value + 1), outcome)
        return {"write": write}
    return bindings


@pytest.mark.parametrize("driver", ["reference", "graph"])
@pytest.mark.parametrize("repaired", [True, False])
def test_repair_checks_fresh_output_and_preserves_failed_attempt(driver, repaired):
    original_calls, repair_calls, received = [], [], []
    def repair(output, failed):
        received.append(failed)
        return factory({"title": "fixture", **({"body": "completed"} if repaired else {})}, repair_calls)(output)
    result = run_with_remedy(workflow(), State(value=7),
        bindings_factory=factory({"title": "fixture"}, original_calls),
        repair_bindings_factory=repair, step_allowance=2,
        evidence_dir=Path(os.environ["WORKFLOW_VALIDATION_DIR"]), driver=driver)
    assert original_calls == repair_calls == [7]  # original input, not last output state
    assert received == [result.original.verdict]
    assert received[0].findings[0].requirement == "body"
    assert result.repair is not None
    assert result.original.root != result.repair.root
    assert result.original.verdict.passed is False
    assert json.loads((result.original.root / "output/result.json").read_text()) == {"title": "fixture"}
    assert result.repair.verdict.passed is repaired
    assert result.passed is repaired
    assert result.receipt.status == ("repaired" if repaired else "exhausted")
    assert result.receipt.reserved_steps == 2
    assert result.original.execution.used_steps + result.repair.execution.used_steps == 2
    saved = json.loads(result.receipt_path.read_text())
    assert saved["original_run"] == result.original.run_id
    assert saved["repair_run"] == result.repair.run_id
    assert saved["original_verdict_digest"] == hashlib.sha256(result.original.verdict_path.read_bytes()).hexdigest()
    assert saved["repair_verdict_digest"] == hashlib.sha256(result.repair.verdict_path.read_bytes()).hexdigest()
    assert result.original.verdict.spec_digest == result.repair.verdict.spec_digest
    assert json.loads((result.original.root / "remedy-policy.json").read_text())["step_allowance"] == 2
    assert json.loads((result.original.root / "repair-reserved.json").read_text())["reserved_steps"] == 2


@pytest.mark.parametrize("driver", ["reference", "graph"])
@pytest.mark.parametrize("case", ["pass", "no_allowance", "invalid_execution"])
def test_no_repair_when_passing_exhausted_or_execution_failed(driver, case):
    calls = []
    def forbidden(*args):
        raise AssertionError("repair invoked")
    result = run_with_remedy(workflow(), State(),
        bindings_factory=factory({"title": "fixture", **({"body": "present"} if case == "pass" else {})}, calls,
                                 outcome="unknown" if case == "invalid_execution" else "done"),
        repair_bindings_factory=forbidden, step_allowance=1 if case == "no_allowance" else 2,
        evidence_dir=Path(os.environ["WORKFLOW_VALIDATION_DIR"]), driver=driver)
    assert calls == [0]
    assert result.repair is None
    assert result.receipt.reserved_steps == 1
    assert result.receipt.status == {"pass": "passed", "no_allowance": "exhausted", "invalid_execution": "ineligible"}[case]
    assert result.passed is (case == "pass")
    assert not (result.original.root / "repair-reserved.json").exists()


@pytest.mark.parametrize("driver", ["reference", "graph"])
@pytest.mark.parametrize("failure", ["factory", "binding", "invalid_route"])
def test_failed_repair_consumes_reservation_without_leaking_exception(driver, failure):
    calls = []
    def repair(output, failed):
        assert (output.parents[2] / "repair-reserved.json").exists()
        calls.append("factory")
        if failure == "factory":
            raise RuntimeError("private callback content")
        def write(state):
            calls.append("binding")
            if failure == "binding":
                raise RuntimeError("private callback content")
            (output / "result.json").write_text('{"title":"fixture","body":"present"}')
            return TransformResult(state, "unknown")
        return {"write": write}
    result = run_with_remedy(workflow(), State(), bindings_factory=factory({"title": "fixture"}, []),
        repair_bindings_factory=repair, step_allowance=2,
        evidence_dir=Path(os.environ["WORKFLOW_VALIDATION_DIR"]), driver=driver)
    assert result.passed is False
    assert result.receipt.reserved_steps == 2
    assert result.receipt.status == ("repair_failed" if failure == "factory" else "exhausted")
    assert calls == (["factory"] if failure == "factory" else ["factory", "binding"])
    assert "private callback content" not in result.receipt_path.read_text()


@pytest.mark.parametrize("allowance", [0, 3, True, "2", 2.0])
def test_invalid_allowance_rejected_before_any_work(allowance):
    def forbidden(*args):
        raise AssertionError("work invoked")
    with pytest.raises(ValueError, match="allowance"):
        run_with_remedy(workflow(), State(), bindings_factory=forbidden,
            repair_bindings_factory=forbidden, step_allowance=allowance,
            evidence_dir=Path(os.environ["WORKFLOW_VALIDATION_DIR"]))


def test_multistep_declaration_rejected_before_any_work():
    spec = workflow()
    extra = TransformNode(id="earlier", operation="write")
    spec = spec.model_copy(update={"nodes": (*spec.nodes, extra), "budget": 2,
        "edges": (*spec.edges, Route(source="earlier", outcome="done", target="produce")), "entry": "earlier"})
    def forbidden(*args):
        raise AssertionError("work invoked")
    with pytest.raises(ValueError, match="one offline Transform"):
        run_with_remedy(spec, State(), bindings_factory=forbidden, repair_bindings_factory=forbidden,
            step_allowance=2, evidence_dir=Path(os.environ["WORKFLOW_VALIDATION_DIR"]))


@pytest.mark.parametrize("driver", ["reference", "graph"])
def test_audit_failure_propagates_without_completed_receipt(driver):
    from agent_lab.reference import AuditError
    roots = []
    def original(output):
        roots.append(output.parent)
        return factory({"title": "fixture"}, [])(output)
    def repair(output, failed):
        raise AuditError("audit unavailable")
    with pytest.raises(AuditError):
        run_with_remedy(workflow(), State(), bindings_factory=original,
            repair_bindings_factory=repair, step_allowance=2,
            evidence_dir=Path(os.environ["WORKFLOW_VALIDATION_DIR"]), driver=driver)
    assert (roots[0] / "repair-reserved.json").exists()
    assert not (roots[0] / "remedy.json").exists()


@pytest.mark.parametrize("change", ["model", "budget", "safety_terminal", "route"])
def test_unsupported_execution_boundaries_rejected_before_factory(change):
    spec = workflow()
    if change == "model":
        node = spec.nodes[0].model_copy(update={"model_operation": True})
        spec = spec.model_copy(update={"nodes": (node,)})
    elif change == "budget":
        spec = spec.model_copy(update={"budget": 2})
    elif change == "safety_terminal":
        spec = spec.model_copy(update={"terminals": ("COMPLETED", "FAILED_VALIDATION")})
    else:
        spec = spec.model_copy(update={"edges": (Route(source="produce", outcome="done", target="FAILED_VALIDATION"),)})
    def forbidden(*args):
        raise AssertionError("work invoked")
    with pytest.raises(ValueError):
        run_with_remedy(spec, State(), bindings_factory=forbidden, repair_bindings_factory=forbidden,
            step_allowance=2, evidence_dir=Path(os.environ["WORKFLOW_VALIDATION_DIR"]))


def test_runnable_demonstration_reports_repaired_and_exhausted(capsys, monkeypatch):
    from agent_lab.remedy_demo import main
    monkeypatch.setattr("sys.argv", ["remedy_demo", "--store", os.environ["WORKFLOW_VALIDATION_DIR"]])
    main()
    rows = json.loads(capsys.readouterr().out)
    assert {(row["driver"], row["status"]) for row in rows} == {
        ("reference", "repaired"), ("reference", "exhausted"),
        ("graph", "repaired"), ("graph", "exhausted")}
    assert all(row["reserved_steps"] == 2 for row in rows)
    for row in rows:
        assert json.loads(Path(row["receipt"]).read_text())["status"] == row["status"]
