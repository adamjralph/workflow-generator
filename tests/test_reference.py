import pytest
from pydantic import BaseModel, ConfigDict

from agent_lab.reference import TransformResult, compile_reference
from agent_lab.runlog import RunLog
from agent_lab.spec import (
    DecisionNode, Fork, GateNode, JudgmentNode, LoopNode, Route, TransformNode,
    WorkflowSpec, validate_spec,
)


class State(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)
    value: int


def example(budget=2):
    return WorkflowSpec(
        entry="double it", budget=budget,
        nodes=(TransformNode(id="double it", operation="double"),
               DecisionNode(id="choose", value="sign", cases=("positive", "other"))),
        edges=(Route(source="double it", outcome="done", target="choose"),
               Route(source="choose", outcome="positive", target="ACCEPTED"),
               Route(source="choose", outcome="other", target="DECLINED")),
        terminals=("ACCEPTED", "DECLINED", "FAILED_VALIDATION", "FAILED_BUDGET"),
    )


def test_compile_rejects_invalid_and_unbound_declarations_without_running_code():
    def forbidden(state):
        pytest.fail("compilation invoked a binding")

    invalid = compile_reference({}, state_type=State, bindings={})
    assert invalid.plan is None
    assert invalid.findings[0].code == "invalid_declaration"
    spec = example().model_copy(update={
        "nodes": example().nodes + (TransformNode(id="unreachable", operation="os.system"),),
        "edges": example().edges + (Route(source="unreachable", outcome="done", target="ACCEPTED"),),
        "terminals": ("ACCEPTED", "DECLINED"),
    })
    compiled = compile_reference(spec, state_type=State, bindings={"double": forbidden, "sign": forbidden})
    assert compiled.plan is None
    assert {(f.code, f.path) for f in compiled.findings} == {
        ("unbound_reference", ("nodes", 2, "operation")),
        ("missing_safety_terminal", ("terminals", "FAILED_VALIDATION")),
        ("missing_safety_terminal", ("terminals", "FAILED_BUDGET")),
    }


@pytest.mark.parametrize("node", [
    JudgmentNode(id="unused", options=("yes",)), GateNode(id="unused"),
    LoopNode(id="unused", max_iterations=2, exit_predicate="stop"),
])
def test_even_unreachable_unsupported_or_unbound_nodes_are_rejected(node):
    spec = example().model_copy(update={
        "nodes": example().nodes + (node,),
        "edges": example().edges + tuple(
            Route(source="unused", outcome=label, target="ACCEPTED") for label in node.route_labels
        ),
    })
    assert validate_spec(spec).valid
    result = compile_reference(spec, state_type=State, bindings=bindings())
    assert result.plan is None
    expected = (("unsupported_options", ("nodes", 2, "options")) if isinstance(node, JudgmentNode)
                else ("unbound_reference", ("nodes", 2, "exit_predicate")) if isinstance(node, LoopNode)
                else ("unsupported_node", ("nodes", 2)))
    assert (result.findings[0].code, result.findings[0].path) == expected


def test_fork_is_not_executable_even_when_structurally_valid():
    spec = WorkflowSpec(entry="a", budget=4, terminals=example().terminals,
        nodes=tuple(TransformNode(id=n, operation="double") for n in ("a", "b", "c", "join")),
        edges=(Fork(source="a", outcome="done", branches=("b", "c"), join="join"),
               Route(source="b", outcome="done", target="join"),
               Route(source="c", outcome="done", target="join"),
               Route(source="join", outcome="done", target="ACCEPTED")))
    assert validate_spec(spec).valid
    result = compile_reference(spec, state_type=State, bindings=bindings())
    assert result.plan is None
    assert result.findings[0].code == "unsupported_edge"


@pytest.mark.parametrize("bad", [
    lambda s: None,
    lambda s: TransformResult(s, "unknown"),
    lambda s: TransformResult(s, 1),
    lambda s: TransformResult(State.model_construct(value="not an int"), "done"),
    lambda s: TransformResult({"value": 2}, "done"),
    lambda s: 1 / 0,
])
def test_invalid_transform_result_records_failure_and_retains_previous_state(tmp_path, bad):
    configured = bindings() | {"double": bad, "sign": lambda s: pytest.fail("later work ran")}
    plan = compile_reference(example(), state_type=State, bindings=configured).plan
    log = RunLog(tmp_path / "failure.jsonl")
    result = plan.run(State(value=3), run_id="bad", log=log)
    assert result.terminal == "FAILED_VALIDATION"
    assert result.state == State(value=3)
    assert result.used_steps == 1
    assert len(log.read()) == 1
    assert log.read()[0].terminal == "FAILED_VALIDATION"
    assert log.read()[0].detail["failure"] == "invalid_binding_result"


@pytest.mark.parametrize("bad", [lambda s: "unknown", lambda s: 1, lambda s: 1 / 0])
def test_invalid_decision_is_recorded(tmp_path, bad):
    plan = compile_reference(example(), state_type=State, bindings=bindings() | {"sign": bad}).plan
    result = plan.run(State(value=3), run_id="bad", log=RunLog(tmp_path / "log"))
    assert result.terminal == "FAILED_VALIDATION"
    assert result.state == State(value=6)
    assert result.used_steps == 2
    assert result.trace[-1].node == "choose"


def test_budget_refuses_next_binding_without_overspend(tmp_path):
    configured = bindings() | {"sign": lambda s: pytest.fail("over-budget work ran")}
    plan = compile_reference(example(budget=1), state_type=State, bindings=configured).plan
    result = plan.run(State(value=3), run_id="capped", log=RunLog(tmp_path / "log"))
    assert result.terminal == "FAILED_BUDGET"
    assert result.used_steps == 1
    assert result.state == State(value=6)
    assert [(e.node, e.transition, e.terminal, e.detail["used_steps"]) for e in result.trace] == [
        ("double it", "done", None, 1), ("choose", None, "FAILED_BUDGET", 1),
    ]


def test_terminal_route_spends_no_extra_step_and_stops_immediately(tmp_path):
    spec = example(budget=1).model_copy(update={"edges": (
        Route(source="double it", outcome="done", target="ACCEPTED"), *example().edges[1:],
    )})
    plan = compile_reference(spec, state_type=State, bindings=bindings() | {
        "sign": lambda s: pytest.fail("work ran after terminal"),
    }).plan
    result = plan.run(State(value=3), run_id="done", log=RunLog(tmp_path / "log"))
    assert (result.terminal, result.used_steps, len(result.trace)) == ("ACCEPTED", 1, 1)


def test_compiled_bindings_and_declarations_are_snapshots_and_runs_repeat(tmp_path):
    from dataclasses import asdict
    configured = bindings()
    spec = example()
    plan = compile_reference(spec, state_type=State, bindings=configured).plan
    configured["double"] = lambda s: pytest.fail("changed binding ran")
    object.__setattr__(spec.nodes[0], "operation", "changed")
    results = [plan.run(State(value=3), run_id=str(i), log=RunLog(tmp_path / "log")) for i in range(2)]
    assert results[0].state == results[1].state == State(value=6)
    traces = [[{k: v for k, v in asdict(e).items() if k != "run_id"} for e in r.trace] for r in results]
    assert traces[0] == traces[1]


def test_state_type_must_be_frozen():
    class Mutable(BaseModel):
        value: int
    result = compile_reference(example(), state_type=Mutable, bindings=bindings())
    assert result.plan is None
    assert result.findings[0].code == "invalid_state_type"


def test_decision_cannot_mutate_nested_state_or_caller_input(tmp_path):
    class Nested(BaseModel):
        model_config = ConfigDict(frozen=True)
        values: list[int]
    retained = []
    def transform(state):
        retained.append(state)
        return TransformResult(state, "done")
    def decide(state):
        state.values.append(99)
        return "positive"
    plan = compile_reference(example(), state_type=Nested, bindings={"double": transform, "sign": decide}).plan
    initial = Nested(values=[1])
    result = plan.run(initial, run_id="nested", log=RunLog(tmp_path / "log"))
    retained[0].values.append(42)
    assert initial.values == result.state.values == [1]


def test_reused_identity_is_refused_without_appending_or_running(tmp_path):
    log = RunLog(tmp_path / "log")
    plan = compile_reference(example(), state_type=State, bindings=bindings()).plan
    plan.run(State(value=1), run_id="same", log=log)
    before = log.digest()
    forbidden = compile_reference(example(), state_type=State, bindings={
        "double": lambda s: pytest.fail("restarted work"), "sign": lambda s: "positive",
    }).plan
    with pytest.raises(ValueError, match="already"):
        forbidden.run(State(value=1), run_id="same", log=RunLog(log.path))
    assert log.digest() == before


def test_parallel_execution_is_explicitly_refused(tmp_path):
    log = RunLog(tmp_path / "log")
    def transform(state):
        with pytest.raises(ValueError, match="active"):
            plan.run(state, run_id="other", log=RunLog(log.path))
        return TransformResult(state, "done")
    plan = compile_reference(example(), state_type=State, bindings=bindings() | {"double": transform}).plan
    result = plan.run(State(value=1), run_id="first", log=log)
    assert result.terminal == "ACCEPTED"
    assert [e.run_id for e in log.read()] == ["first", "first"]


def test_audit_write_failure_is_visible_and_stops_before_later_work(tmp_path):
    from agent_lab.reference import AuditError
    log = RunLog(tmp_path / "log")
    def transform(state):
        # Real filesystem failure at the public audit boundary, not a writer mock.
        log.path.mkdir()
        return TransformResult(state, "done")
    plan = compile_reference(example(), state_type=State, bindings={
        "double": transform, "sign": lambda s: pytest.fail("work after failed audit"),
    }).plan
    with pytest.raises(AuditError):
        plan.run(State(value=1), run_id="audit", log=log)


def test_decision_only_result_is_detached_from_input(tmp_path):
    class Nested(BaseModel):
        model_config = ConfigDict(frozen=True)
        values: list[int]
    spec = example().model_copy(update={
        "entry": "choose", "nodes": (example().nodes[1],), "edges": example().edges[1:],
    })
    plan = compile_reference(spec, state_type=Nested, bindings={"sign": lambda s: "positive"}).plan
    initial = Nested(values=[1])
    result = plan.run(initial, run_id="decision", log=RunLog(tmp_path / "log"))
    initial.values.append(99)
    assert result.state.values == [1]


@pytest.mark.parametrize("initial", [State.model_construct(value="bad"), {"value": 1}])
def test_invalid_initial_state_is_refused_before_work(tmp_path, initial):
    plan = compile_reference(example(), state_type=State, bindings={
        "double": lambda s: pytest.fail("invalid input reached work"), "sign": lambda s: "positive",
    }).plan
    log = RunLog(tmp_path / "log")
    with pytest.raises(ValueError, match="initial state"):
        plan.run(initial, run_id="invalid", log=log)
    assert log.read() == []


def bindings():
    return {
        "double": lambda state: TransformResult(State(value=state.value * 2), "done"),
        "sign": lambda state: "positive" if state.value > 0 else "other",
    }


def test_typed_inputs_take_declared_routes_and_record_arbitrary_node_identities(tmp_path):
    compiled = compile_reference(example(), state_type=State, bindings=bindings())
    assert compiled.findings == ()
    assert compiled.plan is not None
    for run_id, value, terminal in (("one", 3, "ACCEPTED"), ("two", -2, "DECLINED")):
        log = RunLog(tmp_path / "runs.jsonl")
        result = compiled.plan.run(State(value=value), run_id=run_id, log=log)
        assert result.state == State(value=value * 2)
        assert result.terminal == terminal
        assert result.used_steps == 2
        assert [event.node for event in result.trace] == ["double it", "choose"]
        assert [event.seq for event in result.trace] == [0, 1]
        assert result.trace == tuple(event for event in log.read() if event.run_id == run_id)
