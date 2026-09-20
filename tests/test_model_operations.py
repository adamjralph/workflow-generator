from typing import Literal

import pytest
from pydantic import BaseModel, ConfigDict

from agent_lab.generation import generate_graph
from agent_lab.model_operation import ModelOperation, ModelRequest, ModelResponse
from agent_lab.reference import TransformResult, compile_reference
from agent_lab.runlog import RunLog
from agent_lab.spec import Route, TransformNode, WorkflowSpec


class State(BaseModel):
    model_config = ConfigDict(frozen=True)
    text: str = "input"


class Fixture:
    mode: Literal["fixture"] = "fixture"

    def __init__(self):
        self.requests = []

    def invoke(self, request):
        self.requests.append(request)
        return ModelResponse(body="written")


def prepare(state):
    return ModelRequest(operation="draft_linkedin", operation_version="1", schema_version="1",
                        input_digest="input", request_json='{"prompt":"input"}')


def apply(state, response):
    return TransformResult(State(text=response.body), "done")


def operation(source=None, **changes):
    values = dict(operation="draft_linkedin", version="1", schema_version="1", state_type=State,
                  prepare=prepare, source=source or Fixture(), apply=apply)
    return ModelOperation(**(values | changes))


def spec():
    return WorkflowSpec(entry="draft", budget=1,
                        nodes=(TransformNode(id="draft", operation="draft_linkedin", model_operation=True,
                                             operation_version="1", schema_version="1"),),
                        edges=(Route(source="draft", outcome="done", target="DONE"),),
                        terminals=("DONE", "FAILED_VALIDATION", "FAILED_BUDGET"))


@pytest.mark.parametrize("compiler,attribute", [(compile_reference, "plan"), (generate_graph, "candidate")])
def test_explicit_operation_runs_through_public_drivers(tmp_path, compiler, attribute):
    source = Fixture()
    result = compiler(spec(), state_type=State, bindings={},
                      model_operations={"draft_linkedin": operation(source)})
    driver = getattr(result, attribute)
    assert driver is not None, result.findings
    run = driver.run(State(), run_id="fixture", log=RunLog(tmp_path / "run.jsonl"))
    assert run.terminal == "DONE"
    assert run.state == State(text="written")
    assert run.used_steps == 1
    assert len(source.requests) == 1
    if attribute == "candidate":
        node = driver.inspect_structure().nodes[0]
        assert node.model_operation is True
        assert node.operation_version == "1"
        assert node.schema_version == "1"


def test_conformance_executes_independent_prepare_and_apply_and_detects_drift(tmp_path):
    from agent_lab.conformance import check_conformance

    reference, candidate_source = Fixture(), Fixture()
    candidate = generate_graph(spec(), state_type=State, bindings={},
                               model_operations={"draft_linkedin": operation(candidate_source)}).candidate
    report = check_conformance(spec(), candidate, state_type=State, bindings={}, cases={"input": State()},
                               model_operations={"draft_linkedin": operation(reference)}, evidence_dir=tmp_path)
    assert report.passed
    assert len(reference.requests) == len(candidate_source.requests) == 1
    altered = generate_graph(spec(), state_type=State, bindings={}, model_operations={
        "draft_linkedin": operation(apply=lambda state, response: TransformResult(State(text="drift"), "done"))
    }).candidate
    drift = check_conformance(spec(), altered, state_type=State, bindings={}, cases={"input": State()},
                              model_operations={"draft_linkedin": operation()}, evidence_dir=tmp_path)
    assert not drift.passed
    assert any(f.code == "behavioral_mismatch" for f in drift.findings)


@pytest.mark.parametrize("compiler,attribute", [(compile_reference, "plan"), (generate_graph, "candidate")])
def test_budget_is_reserved_before_prepare_or_source(tmp_path, compiler, attribute):
    calls = []
    source = Fixture()
    declaration = spec()
    declaration = declaration.model_copy(update={
        "entry": "first",
        "nodes": (TransformNode(id="first", operation="identity"), *declaration.nodes),
        "edges": (Route(source="first", outcome="done", target="draft"), *declaration.edges),
    })
    op = operation(source, prepare=lambda state: calls.append(state) or prepare(state))
    compiled = compiler(declaration, state_type=State,
                        bindings={"identity": lambda state: TransformResult(state, "done")},
                        model_operations={"draft_linkedin": op})
    run = getattr(compiled, attribute).run(State(), run_id="budget", log=RunLog(tmp_path / "budget.jsonl"))
    assert run.terminal == "FAILED_BUDGET"
    assert run.used_steps == 1
    assert not calls and not source.requests


@pytest.mark.parametrize("compiler,attribute", [(compile_reference, "plan"), (generate_graph, "candidate")])
def test_source_failure_consumes_reserved_step_and_never_applies(tmp_path, compiler, attribute):
    class Broken(Fixture):
        def invoke(self, request):
            self.requests.append(request)
            raise TimeoutError("uncertain")

    calls = []
    source = Broken()
    compiled = compiler(spec(), state_type=State, bindings={}, model_operations={
        "draft_linkedin": operation(source, apply=lambda state, response: calls.append(response))})
    run = getattr(compiled, attribute).run(State(), run_id="failure", log=RunLog(tmp_path / "failure.jsonl"))
    assert run.terminal == "FAILED_VALIDATION"
    assert run.used_steps == 1
    assert run.state == State()
    assert len(source.requests) == 1 and not calls


@pytest.mark.parametrize("change", ["ambiguous", "wrong_state", "version", "schema", "unsupported", "implicit"])
@pytest.mark.parametrize("compiler", [compile_reference, generate_graph])
def test_admission_rejects_invalid_model_contracts_even_unreachable(compiler, change):
    declaration = spec()
    op = operation()
    bindings = {"identity": lambda state: TransformResult(state, "done")}
    if change == "ambiguous":
        bindings["draft_linkedin"] = lambda state: TransformResult(state, "done")
    elif change == "wrong_state":
        op = operation(state_type=BaseModel)
    elif change == "version":
        op = operation(version="2")
    elif change == "schema":
        op = operation(schema_version="2")
    elif change == "unsupported":
        op = operation(operation="arbitrary")
    else:
        declaration = declaration.model_copy(update={"nodes": (
            TransformNode(id="draft", operation="draft_linkedin"),)})
    declaration = declaration.model_copy(update={
        "entry": "first",
        "nodes": (TransformNode(id="first", operation="identity"), *declaration.nodes),
        "edges": (Route(source="first", outcome="done", target="DONE"), *declaration.edges),
    })
    compiled = compiler(declaration, state_type=State, bindings=bindings,
                        model_operations={"draft_linkedin": op})
    assert any(f.code == "invalid_model_operation" for f in compiled.findings)
    assert not op.source.requests


@pytest.mark.parametrize("mode", ["live", "shared"])
def test_conformance_refuses_live_or_shared_model_sources_before_invocation(tmp_path, mode):
    from agent_lab.conformance import check_conformance

    left, right = Fixture(), Fixture()
    if mode == "live":
        right.mode = "live"
    else:
        right = left
    candidate = generate_graph(spec(), state_type=State, bindings={},
                               model_operations={"draft_linkedin": operation(right)}).candidate
    with pytest.raises(ValueError, match="offline|independent"):
        check_conformance(spec(), candidate, state_type=State, bindings={}, cases={"input": State()},
                          model_operations={"draft_linkedin": operation(left)}, evidence_dir=tmp_path)
    assert not left.requests and not right.requests
