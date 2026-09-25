"""Ticket 31: Decision routes inside one checked parallel wave."""
from threading import Event
import socket

import pytest
from pydantic import BaseModel, ConfigDict

from agent_lab.conformance import check_conformance
from agent_lab.generation import generate_graph
from agent_lab.reference import TransformResult, compile_reference
from agent_lab.runlog import RunLog
from agent_lab.spec import DecisionNode, Fork, Route, TransformNode, WorkflowSpec


class State(BaseModel):
    model_config = ConfigDict(frozen=True)
    values: tuple[int, ...] = ()


def spec(budget=8):
    return WorkflowSpec(
        entry="dispatch", budget=budget,
        terminals=("DONE", "FAILED_VALIDATION", "FAILED_BUDGET"),
        nodes=(TransformNode(id="dispatch", operation="dispatch"),
               DecisionNode(id="choose", value="choose", cases=("short", "long")),
               TransformNode(id="extra", operation="extra"),
               TransformNode(id="finish", operation="finish"),
               TransformNode(id="right", operation="right"),
               TransformNode(id="join", operation="join")),
        edges=(Fork(source="dispatch", outcome="done", branches=("choose", "right"), join="join"),
               Route(source="choose", outcome="short", target="finish"),
               Route(source="choose", outcome="long", target="extra"),
               Route(source="extra", outcome="done", target="finish"),
               Route(source="finish", outcome="done", target="join"),
               Route(source="right", outcome="done", target="join"),
               Route(source="join", outcome="done", target="DONE")),
    )


def bindings(choice="short"):
    return {"dispatch": lambda s: TransformResult(State(values=(10,)), "done"),
            "choose": lambda s: choice,
            "extra": lambda s: TransformResult(State(values=s.values + (3,)), "done"),
            "finish": lambda s: TransformResult(State(values=s.values + (1,)), "done"),
            "right": lambda s: TransformResult(State(values=s.values + (2,)), "done")}


def reducers():
    return {"join": lambda entry, branches: TransformResult(
        State(values=branches[0].values + branches[1].values), "done")}


def run(driver, tmp_path, budget=8, choice="short", bound=None, reduced=None):
    built = driver(spec(budget), state_type=State, bindings=bound or bindings(choice),
                   reducers=reduced or reducers())
    plan = built.plan if driver is compile_reference else built.candidate
    assert plan is not None, built.findings
    log = RunLog(tmp_path / f"{driver.__name__}-{budget}-{choice}.jsonl")
    return plan.run(State(), run_id="decision", log=log), log


@pytest.mark.parametrize("driver", [compile_reference, generate_graph])
@pytest.mark.parametrize("choice,expected,visits", [
    ("short", (10, 1, 10, 2), 5), ("long", (10, 3, 1, 10, 2), 6)])
def test_chosen_paths_and_spend(tmp_path, driver, choice, expected, visits):
    result, log = run(driver, tmp_path, choice=choice)
    assert (result.state.values, result.terminal, result.used_steps) == (expected, "DONE", visits)
    left = [event for event in log.read() if event.node in {"choose", "extra", "finish"}]
    assert [event.node for event in left] == (["choose", "finish"] if choice == "short"
                                              else ["choose", "extra", "finish"])
    assert left[0].transition == choice


@pytest.mark.parametrize("driver", [compile_reference, generate_graph])
@pytest.mark.parametrize("budget,choice,terminal,visits", [
    (5, "short", "FAILED_BUDGET", 1),
    (6, "short", "DONE", 5),
    (6, "long", "DONE", 6),
])
def test_longest_path_budget_even_when_short_route_chosen(tmp_path, driver, budget, choice, terminal, visits):
    result, log = run(driver, tmp_path, budget=budget, choice=choice)
    assert (result.terminal, result.used_steps) == (terminal, visits)
    if budget == 5:
        assert [event.node for event in log.read()] == ["dispatch", "dispatch"]
        assert log.read()[-1].detail["branch_worst"] == [3, 1]
        assert log.read()[-1].detail["required"] == 5
        assert log.read()[-1].detail["remaining_steps"] == 4


def test_conformance_alternative_paths_and_candidate_mutation(tmp_path):
    def case_bindings():
        return {**bindings(),
                "dispatch": lambda s: TransformResult(State(values=(10, *s.values)), "done"),
                "choose": lambda s: "short" if s.values[-1] == 0 else "long"}
    candidate = generate_graph(spec(), state_type=State, bindings=case_bindings(), reducers=reducers()).candidate
    assert candidate is not None
    report = check_conformance(spec(), candidate, state_type=State, bindings=case_bindings(),
                               reducers=reducers(), cases={"short": State(values=(0,)),
                                                          "long": State(values=(1,))},
                               evidence_dir=tmp_path)
    assert report.passed, report.findings
    for evidence, chosen in zip(report.evidence, ("short", "long")):
        reference = RunLog(evidence.reference_log).read()
        candidate_events = RunLog(evidence.candidate_log).read()
        assert next(event.transition for event in reference if event.node == "choose") == chosen
        assert next(event.transition for event in candidate_events if event.node == "choose") == chosen
    changed = generate_graph(spec(), state_type=State, bindings=bindings("long"), reducers=reducers()).candidate
    assert changed is not None
    mismatch = check_conformance(spec(), changed, state_type=State, bindings=bindings(),
                                 reducers=reducers(), cases={"short": State()}, evidence_dir=tmp_path)
    assert any(f.code == "behavioral_mismatch" for f in mismatch.findings)


def test_reference_and_graph_agree_on_distinct_routes(tmp_path):
    for choice in ("short", "long"):
        candidate = generate_graph(spec(), state_type=State, bindings=bindings(choice), reducers=reducers()).candidate
        assert candidate is not None
        report = check_conformance(spec(), candidate, state_type=State, bindings=bindings(choice),
                                   reducers=reducers(), cases={choice: State()}, evidence_dir=tmp_path)
        assert report.passed, report.findings
        assert report.evidence[0].reference_projection_digest == report.evidence[0].candidate_projection_digest


def test_reversed_completion_retains_raw_order_and_declared_reducer_order(tmp_path):
    right_finished = Event()
    class Log(RunLog):
        def append_next(self, event):
            super().append_next(event)
            if event.node == "right":
                right_finished.set()
    selected = bindings()
    def choose(s):
        assert right_finished.wait(2)
        return "short"
    selected["choose"] = choose
    candidate = generate_graph(spec(), state_type=State, bindings=selected, reducers=reducers()).candidate
    assert candidate is not None
    log = Log(tmp_path / "reverse.jsonl")
    result = candidate.run(State(), run_id="reverse", log=log)
    assert result.state.values == (10, 1, 10, 2)
    assert [e.node for e in log.read()].index("right") < [e.node for e in log.read()].index("choose")


@pytest.mark.parametrize("driver", [compile_reference, generate_graph])
def test_failed_decision_branch_keeps_entry_state_and_completes_sibling(tmp_path, driver):
    visited = []
    selected = bindings()
    selected["choose"] = lambda s: object()
    def right(s):
        visited.append("right")
        return TransformResult(s, "done")
    selected["right"] = right
    def forbidden(*args):
        pytest.fail("failed wave must not reduce")
    result, log = run(driver, tmp_path, bound=selected, reduced={"join": forbidden})
    assert (result.state, result.terminal, result.used_steps) == (
        State(values=(10,)), "FAILED_VALIDATION", 4)
    assert visited == ["right"]
    assert log.read()[-1].detail["branch_index"] == 0
    assert log.read()[-1].node == "join"


@pytest.mark.parametrize("change", ["route", "order"])
def test_changed_decision_route_or_branch_order_fails_structure(tmp_path, change):
    original = spec()
    if change == "route":
        edges = tuple(edge.model_copy(update={"target": "extra"})
                      if isinstance(edge, Route) and edge.source == "choose" and edge.outcome == "short"
                      else edge for edge in original.edges)
    else:
        edges = (original.edges[0].model_copy(update={"branches": ("right", "choose")}),
                 *original.edges[1:])
    altered = original.model_copy(update={"edges": edges})
    candidate = generate_graph(altered, state_type=State, bindings=bindings(), reducers=reducers()).candidate
    assert candidate is not None
    report = check_conformance(original, candidate, state_type=State, bindings=bindings(),
                               reducers=reducers(), cases={"case": State()}, evidence_dir=tmp_path)
    assert not report.attempted
    assert any(f.code == "structural_mismatch" for f in report.findings)


@pytest.mark.parametrize("driver", [compile_reference, generate_graph])
@pytest.mark.parametrize("change", ["terminal", "loop", "gate", "outside", "cycle"])
def test_unsupported_branch_shapes_rejected_before_work(driver, change):
    original = spec()
    nodes, edges = list(original.nodes), list(original.edges)
    if change == "terminal":
        edges[2] = Route(source="choose", outcome="long", target="DONE")
    elif change == "loop":
        from agent_lab.spec import LoopNode
        nodes[2] = LoopNode(id="extra", exit_predicate="extra", max_iterations=1)
        edges = [edge for edge in edges if edge.source != "extra"]
        edges.extend(Route(source="extra", outcome=label, target="finish")
                     for label in ("repeat", "exit", "exhausted"))
    elif change == "gate":
        from agent_lab.spec import GateNode
        nodes[2] = GateNode(id="extra")
        edges = [edge for edge in edges if edge.source != "extra"]
        edges.extend(Route(source="extra", outcome=label, target="finish")
                     for label in nodes[2].route_labels)
    elif change == "outside":
        nodes.append(TransformNode(id="outside", operation="outside"))
        edges.append(Route(source="outside", outcome="done", target="finish"))
    else:
        edges[3] = Route(source="extra", outcome="done", target="choose")
    changed = original.model_copy(update={"nodes": tuple(nodes), "edges": tuple(edges)})
    calls = []
    def forbidden(*args):
        calls.append(True)
        return "short"
    bound = {key: forbidden for key in (*bindings(), "outside")}
    built = driver(changed, state_type=State, bindings=bound, reducers={"join": forbidden})
    assert (built.plan if driver is compile_reference else built.candidate) is None
    assert built.findings and not calls


def exclusive_spec(budget):
    """Both arms have two visits, while their union has three nodes."""
    original = spec(budget)
    edges = tuple(edge.model_copy(update={"target": "extra"})
                  if isinstance(edge, Route) and edge.source == "choose" and edge.outcome == "short"
                  else edge.model_copy(update={"target": "finish"})
                  if isinstance(edge, Route) and edge.source == "choose" and edge.outcome == "long"
                  else edge.model_copy(update={"target": "join"})
                  if isinstance(edge, Route) and edge.source == "extra"
                  else edge for edge in original.edges)
    return original.model_copy(update={"edges": edges})


@pytest.mark.parametrize("driver", [compile_reference, generate_graph])
@pytest.mark.parametrize("budget,terminal,steps", [(4, "FAILED_BUDGET", 1), (5, "DONE", 5)])
def test_exclusive_paths_admit_longest_not_region_size(tmp_path, driver, budget, terminal, steps):
    chosen = []
    selected = bindings("short")
    selected["extra"] = lambda s: (chosen.append("extra") or
                                   TransformResult(State(values=s.values + (3,)), "done"))
    built = driver(exclusive_spec(budget), state_type=State, bindings=selected, reducers=reducers())
    plan = built.plan if driver is compile_reference else built.candidate
    assert plan is not None, built.findings
    log = RunLog(tmp_path / f"exclusive-{driver.__name__}-{budget}.jsonl")
    result = plan.run(State(), run_id="exclusive", log=log)
    assert (result.terminal, result.used_steps) == (terminal, steps)
    assert chosen == ([] if budget == 4 else ["extra"])
    if budget == 4:
        assert log.read()[-1].detail["branch_worst"] == [2, 1]
        assert log.read()[-1].detail["required"] == 4
        assert log.read()[-1].detail["remaining_steps"] == 3


@pytest.mark.parametrize("driver", [compile_reference, generate_graph])
def test_deep_acyclic_branch_admits_without_recursion_limit(tmp_path, driver):
    original = spec(budget=620)
    nodes = list(original.nodes)
    edges = [edge for edge in original.edges if edge.source != "extra"]
    for index in range(600):
        nodes.append(TransformNode(id=f"deep{index}", operation="deep"))
    edges.extend(Route(source=f"deep{index}", outcome="done",
                       target=f"deep{index + 1}" if index < 599 else "join")
                 for index in range(600))
    edges.append(Route(source="extra", outcome="done", target="deep0"))
    deep = original.model_copy(update={"nodes": tuple(nodes), "edges": tuple(edges)})
    built = driver(deep, state_type=State,
                   bindings={**bindings("short"), "deep": lambda s: TransformResult(s, "done")},
                   reducers=reducers())
    plan = built.plan if driver is compile_reference else built.candidate
    assert plan is not None, built.findings
    result = plan.run(State(), run_id="deep", log=RunLog(tmp_path / "deep.jsonl"))
    assert result.terminal == "DONE"
    assert result.used_steps == 5


def test_multiple_decision_wave_failures_checked_in_declared_order(tmp_path):
    selected = {**bindings(), "choose": lambda s: object(), "right": lambda s: object()}
    def forbidden(*args):
        pytest.fail("failed wave must not invoke reducer")
    candidate = generate_graph(spec(), state_type=State, bindings=selected,
                               reducers={"join": forbidden}).candidate
    assert candidate is not None
    report = check_conformance(spec(), candidate, state_type=State, bindings=selected,
                               reducers={"join": forbidden}, cases={"failure": State()},
                               evidence_dir=tmp_path)
    assert report.passed, report.findings
    assert (report.outputs[0].state, report.outputs[0].terminal, report.outputs[0].used_steps) == (
        State(values=(10,)), "FAILED_VALIDATION", 4)
    for evidence_path in (report.evidence[0].reference_log, report.evidence[0].candidate_log):
        events = RunLog(evidence_path).read()
        assert events[-1].detail["branch_index"] == 0
        assert {e.node for e in events} == {"dispatch", "choose", "right", "join"}


def test_decision_wave_conformance_without_network(tmp_path, monkeypatch):
    original = socket.socket
    def deny_network(family=socket.AF_INET, *args, **kwargs):
        if family in (socket.AF_INET, socket.AF_INET6):
            raise OSError("network socket denied")
        return original(family, *args, **kwargs)
    monkeypatch.setattr(socket, "socket", deny_network)
    with pytest.raises(OSError, match="network socket denied"):
        socket.socket()
    candidate = generate_graph(spec(), state_type=State, bindings=bindings(), reducers=reducers()).candidate
    assert candidate is not None
    report = check_conformance(spec(), candidate, state_type=State, bindings=bindings(),
                               reducers=reducers(), cases={"decision": State()}, evidence_dir=tmp_path)
    assert report.passed, report.findings


def test_decision_wave_audit_failure_is_incomplete(tmp_path, monkeypatch):
    original = RunLog.append_next
    def append(log, event):
        if event.node == "choose":
            raise OSError("synthetic append failure")
        original(log, event)
    monkeypatch.setattr(RunLog, "append_next", append)
    candidate = generate_graph(spec(), state_type=State, bindings=bindings(), reducers=reducers()).candidate
    assert candidate is not None
    report = check_conformance(spec(), candidate, state_type=State, bindings=bindings(),
                               reducers=reducers(), cases={"decision": State()}, evidence_dir=tmp_path)
    assert not report.passed and not report.completed
    assert report.findings[0].code == "incomplete"


def test_decision_wave_detaches_mutable_branch_and_reducer_inputs(tmp_path):
    class MutableState(BaseModel):
        model_config = ConfigDict(frozen=True)
        values: list[int]
    original = MutableState(values=[7])
    seen = []
    def dispatch(s):
        s.values.append(10)
        return TransformResult(s, "done")
    def choose(s):
        s.values.append(99)
        return "short"
    def finish(s):
        assert s.values == [7, 10]
        return TransformResult(s, "done")
    def right(s):
        assert s.values == [7, 10]
        return TransformResult(s, "done")
    def reduce(entry, branches):
        seen.append((list(entry.values), [list(branch.values) for branch in branches]))
        entry.values.append(77)
        branches[0].values.append(88)
        return TransformResult(MutableState(values=[42]), "done")
    selected = {"dispatch": dispatch, "choose": choose, "extra": finish,
                "finish": finish, "right": right}
    candidate = generate_graph(spec(), state_type=MutableState, bindings=selected,
                               reducers={"join": reduce}).candidate
    assert candidate is not None
    report = check_conformance(spec(), candidate, state_type=MutableState,
                               bindings=selected, reducers={"join": reduce},
                               cases={"detached": original}, evidence_dir=tmp_path)
    assert report.passed, report.findings
    assert original.values == [7]
    assert isinstance(report.outputs[0].state, MutableState)
    assert report.outputs[0].state.values == [42]
    assert seen == [([7, 10], [[7, 10], [7, 10]])] * 2


def test_reversed_decision_completion_conforms_with_raw_order_retained(tmp_path, monkeypatch):
    right_recorded = Event()
    original = RunLog.append_next
    def append(log, event):
        original(log, event)
        if log.path.name.endswith("candidate.jsonl") and event.node == "right":
            right_recorded.set()
    monkeypatch.setattr(RunLog, "append_next", append)
    def late_choice(s):
        assert right_recorded.wait(2)
        return "short"
    candidate = generate_graph(spec(), state_type=State,
                               bindings={**bindings(), "choose": late_choice},
                               reducers=reducers()).candidate
    assert candidate is not None
    report = check_conformance(spec(), candidate, state_type=State, bindings=bindings(),
                               reducers=reducers(), cases={"reversed": State()}, evidence_dir=tmp_path)
    assert report.passed, report.findings
    evidence = report.evidence[0]
    plain = [event.node for event in RunLog(evidence.reference_log).read()]
    graph = [event.node for event in RunLog(evidence.candidate_log).read()]
    assert plain.index("choose") < plain.index("right")
    assert graph.index("right") < graph.index("choose")
    assert evidence.reference_projection_digest == evidence.candidate_projection_digest
    assert evidence.reference_digest != evidence.candidate_digest


def test_decision_wave_refusal_conforms_with_exact_evidence(tmp_path):
    candidate = generate_graph(spec(5), state_type=State,
                               bindings=bindings(), reducers=reducers()).candidate
    assert candidate is not None
    report = check_conformance(spec(5), candidate, state_type=State, bindings=bindings(),
                               reducers=reducers(), cases={"refused": State()}, evidence_dir=tmp_path)
    assert report.passed, report.findings
    assert (report.outputs[0].terminal, report.outputs[0].used_steps) == ("FAILED_BUDGET", 1)
    for path in (report.evidence[0].reference_log, report.evidence[0].candidate_log):
        events = RunLog(path).read()
        assert [event.node for event in events] == ["dispatch", "dispatch"]
        assert events[-1].detail == {"target": "FAILED_BUDGET", "failure": "wave_budget_refused",
                                     "required": 5, "remaining_steps": 4, "branch_worst": [3, 1],
                                     "used_steps": 1, "max_steps": 5}
