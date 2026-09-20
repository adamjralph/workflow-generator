"""Generated target tested through compilation, execution and public evidence."""
import pytest
from pydantic import BaseModel, ConfigDict

from agent_lab.generation import GraphCandidate, generate_graph
from agent_lab.reference import AuditError, TransformResult, compile_reference
from agent_lab.runlog import RunLog
from agent_lab.spec import DecisionNode, GateNode, Route, TransformNode, WorkflowSpec


class State(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)
    value: int


def example(budget=2):
    return WorkflowSpec(
        entry="double it / arbitrary", budget=budget,
        nodes=(TransformNode(id="double it / arbitrary", operation="double"),
               DecisionNode(id="choose", value="sign", cases=("positive", "other"))),
        edges=(Route(source="double it / arbitrary", outcome="done", target="choose"),
               Route(source="choose", outcome="positive", target="ACCEPTED"),
               Route(source="choose", outcome="other", target="DECLINED")),
        terminals=("ACCEPTED", "DECLINED", "FAILED_VALIDATION", "FAILED_BUDGET"),
    )


def bindings():
    return {"double": lambda s: TransformResult(State(value=s.value * 2), "done"),
            "sign": lambda s: "positive" if s.value > 0 else "other"}


@pytest.mark.parametrize("value,terminal", [(3, "ACCEPTED"), (-2, "DECLINED")])
def test_generated_graph_routes_typed_inputs_and_matches_plain_evidence(tmp_path, value, terminal):
    generated = generate_graph(example(), state_type=State, bindings=bindings())
    assert not generated.findings
    candidate = generated.candidate
    assert candidate is not None
    plain = compile_reference(example(), state_type=State, bindings=bindings()).plan
    assert plain is not None
    graph_log, plain_log = RunLog(tmp_path / "graph"), RunLog(tmp_path / "plain")
    result = candidate.run(State(value=value), run_id="same", log=graph_log)
    assert result.state == State(value=value * 2)
    assert result.terminal == terminal
    assert result.used_steps == 2
    assert [e.node for e in result.trace] == ["double it / arbitrary", "choose"]
    assert result == plain.run(State(value=value), run_id="same", log=plain_log)
    assert graph_log.digest() == plain_log.digest()
    assert graph_log.read_bytes() == plain_log.read_bytes()


def test_inspection_is_detached_execution_configuration_and_changed_candidates_are_independent(tmp_path):
    spec = example()
    supplied = bindings()
    candidate = generate_graph(spec, state_type=State, bindings=supplied).candidate
    assert candidate.state_type is State
    inspected = candidate.inspect_structure()
    assert inspected == spec
    supplied["double"] = lambda s: TransformResult(State(value=99), "done")
    object.__setattr__(inspected, "budget", 1)
    assert candidate.inspect_structure().budget == 2
    assert candidate.run(State(value=3), run_id="original", log=RunLog(tmp_path / "original")).state.value == 6
    changed = generate_graph(spec.model_copy(update={"budget": 1}), state_type=State, bindings=supplied).candidate
    assert changed.inspect_structure().budget == 1
    result = changed.run(State(value=3), run_id="changed", log=RunLog(tmp_path / "changed"))
    assert result.state.value == 99
    assert result.terminal == "FAILED_BUDGET"


def test_replaced_executable_method_is_rejected_before_binding_execution():
    candidate = generate_graph(example(), state_type=State, bindings=bindings()).candidate
    original = GraphCandidate.run
    try:
        GraphCandidate.run = lambda *args, **kwargs: None
        with pytest.raises(ValueError, match="Unsupported candidate"):
            candidate.inspect_structure()
    finally:
        GraphCandidate.run = original


def test_bypassed_frozen_configuration_is_rejected(tmp_path):
    candidate = generate_graph(example(), state_type=State, bindings=bindings()).candidate
    object.__setattr__(candidate, "_entry", "choose")
    with pytest.raises(ValueError, match="Unsupported candidate"):
        candidate.inspect_structure()
    with pytest.raises(ValueError, match="Unsupported candidate"):
        candidate.run(State(value=1), run_id="bad", log=RunLog(tmp_path / "bad"))


def test_unreachable_nodes_are_retained_and_never_invoked(tmp_path):
    spec = example()
    spec = spec.model_copy(update={
        "nodes": spec.nodes + (TransformNode(id="unreachable", operation="never"),),
        "edges": spec.edges + (Route(source="unreachable", outcome="done", target="ACCEPTED"),),
    })
    def never(state):
        pytest.fail("Unreachable binding invoked")
    candidate = generate_graph(spec, state_type=State, bindings=bindings() | {"never": never}).candidate
    assert candidate.inspect_structure() == spec
    assert candidate.run(State(value=1), run_id="unreachable", log=RunLog(tmp_path / "log")).terminal == "ACCEPTED"


@pytest.mark.parametrize("change,code,path", [
    ({"budget": 0}, "invalid_declaration", ("budget",)),
    ({"terminals": ("ACCEPTED", "DECLINED")}, "missing_safety_terminal", ("terminals", "FAILED_VALIDATION")),
])
def test_generation_rejects_invalid_declarations_without_binding_calls(change, code, path):
    def never(state):
        pytest.fail("Compilation invoked a binding")
    result = generate_graph(example().model_copy(update=change), state_type=State,
                            bindings={"double": never, "sign": never})
    assert result.candidate is None
    assert (code, path) in {(f.code, f.path) for f in result.findings}


@pytest.mark.parametrize("unsupported", [False, True])
def test_generation_checks_unreachable_declarations(unsupported):
    spec = example()
    extra = GateNode(id="dead") if unsupported else TransformNode(id="dead", operation="missing")
    spec = spec.model_copy(update={
        "nodes": spec.nodes + (extra,),
        "edges": spec.edges + tuple(Route(source="dead", outcome=label, target="ACCEPTED")
                                    for label in extra.route_labels),
    })
    result = generate_graph(spec, state_type=State, bindings=bindings())
    assert result.candidate is None
    assert result.findings[0].code == ("unsupported_node" if unsupported else "unbound_reference")
    assert result.findings[0].path[:2] == ("nodes", 2)


def test_generation_rejects_mutable_state_type():
    class Mutable(BaseModel):
        value: int
    result = generate_graph(example(), state_type=Mutable, bindings=bindings())
    assert result.candidate is None
    assert result.findings[0].code == "invalid_state_type"


@pytest.mark.parametrize("mode,terminal,steps", [
    ("exception", "FAILED_VALIDATION", 1),
    ("wrong_state", "FAILED_VALIDATION", 1),
    ("wrong_label", "FAILED_VALIDATION", 1),
    ("wrong_result", "FAILED_VALIDATION", 1),
    ("wrong_decision", "FAILED_VALIDATION", 2),
    ("short_budget", "FAILED_BUDGET", 1),
    ("terminal_stop", "ACCEPTED", 1),
])
def test_failure_budget_and_terminal_evidence_match_plain(tmp_path, mode, terminal, steps):
    def bad(state):
        raise RuntimeError("excluded from trace")
    supplied = bindings()
    spec = example(budget=1 if mode == "short_budget" else 2)
    if mode == "exception":
        supplied["double"] = bad
    elif mode == "wrong_state":
        supplied["double"] = lambda s: TransformResult(State.model_construct(value="bad"), "done")
    elif mode == "wrong_label":
        supplied["double"] = lambda s: TransformResult(State(value=99), "missing")
    elif mode == "wrong_result":
        supplied["double"] = lambda s: s
    elif mode == "wrong_decision":
        supplied["sign"] = lambda s: 1
    elif mode == "terminal_stop":
        spec = spec.model_copy(update={"edges": (Route(source=spec.entry, outcome="done", target="ACCEPTED"),) + spec.edges[1:]})
    if mode in ("short_budget", "terminal_stop"):
        def forbidden(state):
            pytest.fail("Stopped graph invoked later work")
        supplied["sign"] = forbidden
    candidate = generate_graph(spec, state_type=State, bindings=supplied).candidate
    plain = compile_reference(spec, state_type=State, bindings=supplied).plan
    graph_log, plain_log = RunLog(tmp_path / "graph"), RunLog(tmp_path / "plain")
    result = candidate.run(State(value=3), run_id="same", log=graph_log)
    assert (result.terminal, result.used_steps) == (terminal, steps)
    assert result == plain.run(State(value=3), run_id="same", log=plain_log)
    assert graph_log.read_bytes() == plain_log.read_bytes()
    assert graph_log.digest() == plain_log.digest()


def test_audit_failure_stops_before_later_work(tmp_path):
    log = RunLog(tmp_path / "audit")
    def break_audit(state):
        log.path.mkdir()
        return TransformResult(state, "done")
    def forbidden(state):
        pytest.fail("Audit failure allowed later work")
    candidate = generate_graph(example(), state_type=State,
                               bindings={"double": break_audit, "sign": forbidden}).candidate
    with pytest.raises(AuditError):
        candidate.run(State(value=1), run_id="failure", log=log)


def test_invalid_initial_and_fresh_run_policy(tmp_path):
    candidate = generate_graph(example(), state_type=State, bindings=bindings()).candidate
    log = RunLog(tmp_path / "audit")
    with pytest.raises(ValueError, match="Invalid initial state"):
        candidate.run(State.model_construct(value="bad"), run_id="invalid", log=log)
    candidate.run(State(value=1), run_id="fresh", log=log)
    before = log.read_bytes()
    with pytest.raises(ValueError, match="already recorded"):
        candidate.run(State(value=1), run_id="fresh", log=log)
    with log.fresh_run("other"):
        with pytest.raises(ValueError, match="already active"):
            candidate.run(State(value=1), run_id="another", log=log)
    assert log.read_bytes() == before


def test_nested_state_detaches_input_and_decision_result(tmp_path):
    class Nested(BaseModel):
        model_config = ConfigDict(frozen=True)
        values: list[int]
    def transform(state):
        state.values.append(2)
        return TransformResult(state, "done")
    def decide(state):
        state.values.append(3)
        return "positive"
    candidate = generate_graph(example(), state_type=Nested,
                               bindings={"double": transform, "sign": decide}).candidate
    initial = Nested(values=[1])
    result = candidate.run(initial, run_id="nested", log=RunLog(tmp_path / "log"))
    assert initial.values == [1]
    assert result.state.values == [1, 2]
