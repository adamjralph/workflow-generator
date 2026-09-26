"""Ticket 32: bounded branch loops through the authored-spec public seam."""
import socket
from threading import Event

import pytest
from pydantic import BaseModel, ConfigDict

from agent_lab.conformance import check_conformance
from agent_lab.generation import generate_graph
from agent_lab.reference import TransformResult, compile_reference
from agent_lab.runlog import RunLog
from agent_lab.spec import DecisionNode, Fork, LoopNode, Route, TransformNode, WorkflowSpec


class State(BaseModel):
    model_config = ConfigDict(frozen=True)
    values: tuple[int, ...] = ()


def spec(budget=13, iterations=2):
    return WorkflowSpec(
        entry="dispatch", budget=budget,
        terminals=("DONE", "FAILED_VALIDATION", "FAILED_BUDGET"),
        nodes=(TransformNode(id="dispatch", operation="dispatch"),
               LoopNode(id="loop", exit_predicate="stop", max_iterations=iterations),
               DecisionNode(id="choose", value="choose", cases=("short", "long")),
               TransformNode(id="extra", operation="extra"),
               TransformNode(id="body", operation="body"),
               TransformNode(id="after", operation="after"),
               TransformNode(id="right", operation="right"),
               TransformNode(id="join", operation="join")),
        edges=(Fork(source="dispatch", outcome="done", branches=("loop", "right"), join="join"),
               Route(source="loop", outcome="repeat", target="choose"),
               Route(source="loop", outcome="exit", target="after"),
               Route(source="loop", outcome="exhausted", target="after"),
               Route(source="choose", outcome="short", target="body"),
               Route(source="choose", outcome="long", target="extra"),
               Route(source="extra", outcome="done", target="body"),
               Route(source="body", outcome="done", target="loop"),
               Route(source="after", outcome="done", target="join"),
               Route(source="right", outcome="done", target="join"),
               Route(source="join", outcome="done", target="DONE")),
    )


def bindings(stop_after=0, choice="long"):
    return {"dispatch": lambda s: TransformResult(State(values=(10,)), "done"),
            "stop": lambda s: len(s.values) >= stop_after + 1,
            "choose": lambda s: choice,
            "extra": lambda s: TransformResult(State(values=s.values + (3,)), "done"),
            "body": lambda s: TransformResult(State(values=s.values + (1,)), "done"),
            "after": lambda s: TransformResult(State(values=s.values + (4,)), "done"),
            "right": lambda s: TransformResult(State(values=s.values + (2,)), "done")}


def reducers():
    return {"join": lambda entry, branches: TransformResult(
        State(values=branches[0].values + branches[1].values), "done")}


def run(driver, tmp_path, *, budget=13, iterations=2, stop_after=0, choice="long", selected=None, reducer=None):
    built = driver(spec(budget, iterations), state_type=State, bindings=selected or bindings(stop_after, choice),
                   reducers=reducer or reducers())
    plan = built.plan if driver is compile_reference else built.candidate
    assert plan is not None, built.findings
    log = RunLog(tmp_path / f"{driver.__name__}-{budget}-{stop_after}-{choice}.jsonl")
    return plan.run(State(), run_id="loop", log=log), log


@pytest.mark.parametrize("driver", [compile_reference, generate_graph])
@pytest.mark.parametrize("stop_after,choice,expected,steps,labels,counts", [
    (0, "long", (10, 4, 10, 2), 5, ["exit"], [0]),
    (1, "short", (10, 1, 4, 10, 2), 8, ["repeat", "exit"], [1, 1]),
    (10, "long", (10, 3, 1, 3, 1, 4, 10, 2), 13, ["repeat", "repeat", "exhausted"], [1, 2, 2]),
])
def test_repeat_exit_exhaustion_state_spend_and_events(tmp_path, driver, stop_after, choice, expected, steps, labels, counts):
    result, log = run(driver, tmp_path, stop_after=stop_after, choice=choice)
    assert (result.state.values, result.terminal, result.used_steps) == (expected, "DONE", steps)
    visits = [event for event in log.read() if event.node == "loop"]
    assert [event.transition for event in visits] == labels
    assert [event.detail["repeat_count"] for event in visits] == counts
    assert [event.node for event in log.read() if event.node in {"choose", "extra", "body"}].count("body") == len(labels) - 1


@pytest.mark.parametrize("driver", [compile_reference, generate_graph])
def test_just_short_refused_before_branch_and_exact_admitted(tmp_path, driver):
    result, log = run(driver, tmp_path, budget=12, stop_after=0)
    assert (result.terminal, result.used_steps) == ("FAILED_BUDGET", 1)
    assert [e.node for e in log.read()] == ["dispatch", "dispatch"]
    assert log.read()[-1].detail["branch_worst"] == [10, 1]
    assert log.read()[-1].detail["required"] == 12
    assert log.read()[-1].detail["remaining_steps"] == 11
    result, log = run(driver, tmp_path, budget=13, stop_after=10)
    assert (result.terminal, result.used_steps) == ("DONE", 13)
    assert all(e.detail.get("failure") != "budget_exhausted" for e in log.read())


@pytest.mark.parametrize("driver", [compile_reference, generate_graph])
@pytest.mark.parametrize("budget,iterations,left,required", [
    (13, 14, 58, 60), (2, 100_000, 400_002, 400_004),
])
def test_refusal_reports_true_whole_branch_cost_above_budget(tmp_path, driver, budget, iterations, left, required):
    result, log = run(driver, tmp_path, budget=budget, iterations=iterations)
    assert (result.terminal, result.used_steps) == ("FAILED_BUDGET", 1)
    assert [event.node for event in log.read()] == ["dispatch", "dispatch"]
    assert log.read()[-1].detail["branch_worst"] == [left, 1]
    assert log.read()[-1].detail["required"] == required


@pytest.mark.parametrize("driver", [compile_reference, generate_graph])
def test_failure_finishes_sibling_and_keeps_entry_state(tmp_path, driver):
    seen = []
    selected = bindings(10)
    selected["stop"] = lambda s: object()
    selected["right"] = lambda s: (seen.append("right") or TransformResult(s, "done"))
    def no_reduce(*args):
        pytest.fail("failed branch cannot reduce")
    result, log = run(driver, tmp_path, selected=selected, reducer={"join": no_reduce})
    assert (result.state, result.terminal, result.used_steps) == (State(values=(10,)), "FAILED_VALIDATION", 4)
    assert seen == ["right"]
    assert log.read()[-1].detail["branch_index"] == 0


@pytest.mark.parametrize("change", ["second_loop", "repeat_bypass", "outside_entry", "non_loop_cycle", "nested_fork"])
@pytest.mark.parametrize("driver", [compile_reference, generate_graph])
def test_unsupported_shapes_rejected_before_binding(driver, change):
    original = spec()
    nodes, edges = list(original.nodes), list(original.edges)
    if change == "second_loop":
        nodes[6] = LoopNode(id="right", exit_predicate="stop", max_iterations=1)
        edges = [e for e in edges if e.source != "right"]
        edges.extend(Route(source="right", outcome=label, target="join") for label in ("repeat", "exit", "exhausted"))
    elif change == "repeat_bypass":
        edges[1] = Route(source="loop", outcome="repeat", target="join")
    elif change == "outside_entry":
        nodes.append(TransformNode(id="outside", operation="outside"))
        edges.append(Route(source="outside", outcome="done", target="body"))
    elif change == "nested_fork":
        edges[1] = Fork(source="loop", outcome="repeat", branches=("choose", "extra"), join="body")
    else:
        edges[7] = Route(source="body", outcome="done", target="choose")
    changed = original.model_copy(update={"nodes": tuple(nodes), "edges": tuple(edges)})
    calls = []
    def forbidden(*args):
        calls.append(True)
        return True
    built = driver(changed, state_type=State, bindings={k: forbidden for k in (*bindings(), "outside")},
                   reducers={"join": forbidden})
    assert (built.plan if driver is compile_reference else built.candidate) is None
    assert built.findings and not calls


def test_conformance_repeat_visits_mutations_and_no_network(tmp_path, monkeypatch):
    def denied(*args, **kwargs):
        pytest.fail("offline case attempted network")
    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(socket.socket, "connect", denied)
    selected = bindings(10)
    candidate = generate_graph(spec(), state_type=State, bindings=selected, reducers=reducers()).candidate
    assert candidate is not None
    report = check_conformance(spec(), candidate, state_type=State, bindings=selected, reducers=reducers(),
                               cases={"repeat": State()}, evidence_dir=tmp_path)
    assert report.passed, report.findings
    assert report.evidence[0].reference_projection_digest == report.evidence[0].candidate_projection_digest
    assert [e.node for e in RunLog(report.evidence[0].candidate_log).read()].count("loop") == 3
    changed = spec().model_copy(update={"nodes": tuple(
        node.model_copy(update={"max_iterations": 1}) if isinstance(node, LoopNode) else node
        for node in spec().nodes)})
    altered = generate_graph(changed, state_type=State, bindings=selected, reducers=reducers()).candidate
    assert altered is not None
    mismatch = check_conformance(spec(), altered, state_type=State, bindings=selected,
                                 reducers=reducers(), cases={"case": State()}, evidence_dir=tmp_path)
    assert any(f.code == "structural_mismatch" for f in mismatch.findings)
    rerouted = spec().model_copy(update={"edges": tuple(
        edge.model_copy(update={"target": "join"})
        if isinstance(edge, Route) and edge.source == "loop" and edge.outcome == "exit" else edge
        for edge in spec().edges)})
    altered = generate_graph(rerouted, state_type=State, bindings=selected, reducers=reducers()).candidate
    assert altered is not None
    mismatch = check_conformance(spec(), altered, state_type=State, bindings=selected,
                                 reducers=reducers(), cases={"case": State()}, evidence_dir=tmp_path)
    assert not mismatch.attempted
    assert any(f.code == "structural_mismatch" for f in mismatch.findings)
    divergent = generate_graph(spec(), state_type=State, bindings=bindings(0), reducers=reducers()).candidate
    assert divergent is not None
    mismatch = check_conformance(spec(), divergent, state_type=State, bindings=selected,
                                 reducers=reducers(), cases={"case": State()}, evidence_dir=tmp_path)
    assert any(f.code == "behavioral_mismatch" for f in mismatch.findings)


def test_canonical_evidence_detects_changed_repeated_visit(tmp_path):
    from dataclasses import replace
    from agent_lab.conformance import wave_projection
    result, log = run(compile_reference, tmp_path, stop_after=10)
    assert result.terminal == "DONE"
    events = log.read()
    loop_index = next(i for i, event in enumerate(events)
                      if event.node == "loop" and event.transition == "repeat")
    corrupted = list(events)
    corrupted[loop_index] = replace(events[loop_index], detail={
        **events[loop_index].detail, "repeat_count": 0})
    assert wave_projection(spec(), events) != wave_projection(spec(), corrupted)


def test_two_branch_loops_fail_by_declared_order_after_both_complete(tmp_path):
    original = spec(budget=15, iterations=1)
    nodes = (*[node for node in original.nodes if node.id != "right"],
             LoopNode(id="other_loop", exit_predicate="other_stop", max_iterations=1))
    edges = tuple(edge.model_copy(update={"branches": ("loop", "other_loop")})
                  if isinstance(edge, Fork) else edge for edge in original.edges if edge.source != "right")
    edges += (Route(source="other_loop", outcome="repeat", target="other_loop"),
              Route(source="other_loop", outcome="exit", target="join"),
              Route(source="other_loop", outcome="exhausted", target="join"))
    both = original.model_copy(update={"nodes": nodes, "edges": edges})
    visited = []
    selected = {**bindings(10), "stop": lambda s: object(),
                "other_stop": lambda s: (visited.append("other") or object())}
    def no_reduce(*args):
        pytest.fail("failed branches cannot reduce")
    for driver in (compile_reference, generate_graph):
        built = driver(both, state_type=State, bindings=selected, reducers={"join": no_reduce})
        plan = built.plan if driver is compile_reference else built.candidate
        assert plan is not None, built.findings
        log = RunLog(tmp_path / f"two-{driver.__name__}.jsonl")
        result = plan.run(State(), run_id="two", log=log)
        assert (result.state, result.terminal, result.used_steps) == (State(values=(10,)), "FAILED_VALIDATION", 4)
        assert log.read()[-1].detail["branch_index"] == 0
    assert visited == ["other", "other"]


@pytest.mark.parametrize("driver", [compile_reference, generate_graph])
def test_two_loops_keep_separate_repeat_counts_and_branch_state(tmp_path, driver):
    original = spec(budget=14)
    nodes = (*[node for node in original.nodes if node.id != "right"],
             LoopNode(id="other_loop", exit_predicate="other_stop", max_iterations=1))
    edges = tuple(edge.model_copy(update={"branches": ("loop", "other_loop")})
                  if isinstance(edge, Fork) else edge for edge in original.edges if edge.source != "right")
    edges += (Route(source="other_loop", outcome="repeat", target="other_loop"),
              Route(source="other_loop", outcome="exit", target="join"),
              Route(source="other_loop", outcome="exhausted", target="join"))
    both = original.model_copy(update={"nodes": nodes, "edges": edges})
    built = driver(both, state_type=State,
                   bindings={**bindings(10), "other_stop": lambda s: False}, reducers=reducers())
    plan = built.plan if driver is compile_reference else built.candidate
    assert plan is not None, built.findings
    log = RunLog(tmp_path / f"two-success-{driver.__name__}.jsonl")
    result = plan.run(State(), run_id="two-success", log=log)
    assert (result.state.values, result.terminal, result.used_steps) == (
        (10, 3, 1, 3, 1, 4, 10), "DONE", 14)
    assert [e.detail["repeat_count"] for e in log.read() if e.node == "loop"] == [1, 2, 2]
    assert [e.detail["repeat_count"] for e in log.read() if e.node == "other_loop"] == [1, 1]


def test_reversed_completion_keeps_per_branch_repeat_order(tmp_path):
    sibling_done = Event()
    class Log(RunLog):
        def append_next(self, event):
            super().append_next(event)
            if event.node == "right":
                sibling_done.set()
    selected = bindings(10)
    predicate = selected["stop"]
    def wait_predicate(s):
        assert sibling_done.wait(2)
        return predicate(s)
    selected["stop"] = wait_predicate
    candidate = generate_graph(spec(), state_type=State, bindings=selected, reducers=reducers()).candidate
    assert candidate is not None
    log = Log(tmp_path / "reverse-loop.jsonl")
    result = candidate.run(State(), run_id="reverse", log=log)
    assert (result.terminal, result.used_steps) == ("DONE", 13)
    nodes = [event.node for event in log.read()]
    assert nodes.index("right") < nodes.index("loop")
    assert [event.transition for event in log.read() if event.node == "loop"] == [
        "repeat", "repeat", "exhausted"]


def test_conformance_early_exit_exhaustion_refusal_and_failure(tmp_path):
    selected = bindings(10)
    selected["stop"] = lambda s: s.values == (10, 0)
    selected["dispatch"] = lambda s: TransformResult(State(values=(10, *s.values)), "done")
    candidate = generate_graph(spec(), state_type=State, bindings=selected, reducers=reducers()).candidate
    assert candidate is not None
    report = check_conformance(spec(), candidate, state_type=State, bindings=selected, reducers=reducers(),
                               cases={"early": State(values=(0,)), "exhausted": State(values=(1,))},
                               evidence_dir=tmp_path)
    assert report.passed, report.findings
    assert [case.terminal for case in report.outputs] == ["DONE", "DONE"]
    assert [[event.transition for event in RunLog(record.reference_log).read() if event.node == "loop"]
            for record in report.evidence] == [["exit"], ["repeat", "repeat", "exhausted"]]
    short = spec(budget=12)
    short_candidate = generate_graph(short, state_type=State, bindings=selected, reducers=reducers()).candidate
    assert short_candidate is not None
    refused = check_conformance(short, short_candidate, state_type=State, bindings=selected,
                                reducers=reducers(), cases={"short": State()}, evidence_dir=tmp_path)
    assert refused.passed, refused.findings
    assert refused.outputs[0].terminal == "FAILED_BUDGET"
    failed_bindings = {**bindings(), "stop": lambda s: "not a bool"}
    failed = generate_graph(spec(), state_type=State, bindings=failed_bindings, reducers=reducers()).candidate
    assert failed is not None
    report = check_conformance(spec(), failed, state_type=State, bindings=failed_bindings,
                               reducers=reducers(), cases={"invalid": State()}, evidence_dir=tmp_path)
    assert report.passed, report.findings
    assert report.outputs[0].terminal == "FAILED_VALIDATION"


def test_audit_write_failure_fails_closed(tmp_path):
    class BrokenLog(RunLog):
        def append_next(self, event):
            if event.node == "loop":
                raise OSError("disk unavailable")
            super().append_next(event)
    for driver in (compile_reference, generate_graph):
        built = driver(spec(), state_type=State, bindings=bindings(), reducers=reducers())
        plan = built.plan if driver is compile_reference else built.candidate
        assert plan is not None
        with pytest.raises(Exception, match="audit I/O failed"):
            plan.run(State(), run_id="broken", log=BrokenLog(tmp_path / f"broken-{driver.__name__}.jsonl"))
