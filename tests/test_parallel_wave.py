"""Ticket 28: hand-authored wave oracles at the accepted public seams."""
import pytest
import socket
import json
from threading import Barrier, BrokenBarrierError, Event, Lock
from pydantic import BaseModel, ConfigDict

from agent_lab.generation import generate_graph
from agent_lab.conformance import check_conformance
from agent_lab.reference import AuditError, TransformResult, compile_reference
from agent_lab.runlog import RunLog
from agent_lab.spec import DecisionNode, Fork, GateNode, JudgmentNode, LoopNode, Route, TransformNode, WorkflowSpec


class State(BaseModel):
    model_config = ConfigDict(frozen=True)
    values: tuple[int, ...] = ()


def wave_spec():
    return WorkflowSpec(
        entry="dispatch", budget=4,
        terminals=("DONE", "FAILED_VALIDATION", "FAILED_BUDGET"),
        nodes=tuple(TransformNode(id=name, operation=name)
                    for name in ("dispatch", "left", "right", "join")),
        edges=(Fork(source="dispatch", outcome="done", branches=("left", "right"), join="join"),
               Route(source="left", outcome="done", target="join"),
               Route(source="right", outcome="done", target="join"),
               Route(source="join", outcome="done", target="DONE")),
    )


@pytest.mark.parametrize("driver", [compile_reference, generate_graph])
def test_two_branch_hand_authored_state_reducer_and_spend(tmp_path, driver):
    observed = []

    def reduce(entry, branches):
        observed.append((entry, branches))
        return TransformResult(State(values=branches[0].values + branches[1].values), "done")

    bindings = {
        "dispatch": lambda s: TransformResult(State(values=(10,)), "done"),
        "left": lambda s: TransformResult(State(values=s.values + (1,)), "done"),
        "right": lambda s: TransformResult(State(values=s.values + (2,)), "done"),
    }
    built = driver(wave_spec(), state_type=State, bindings=bindings, reducers={"join": reduce})
    runnable = built.plan if driver is compile_reference else built.candidate
    assert runnable is not None, built.findings
    log = RunLog(tmp_path / "wave.jsonl")
    result = runnable.run(State(), run_id="two-branch", log=log)
    assert observed == [(State(values=(10,)), (State(values=(10, 1)), State(values=(10, 2))))]
    assert result.state == State(values=(10, 1, 10, 2))
    assert result.terminal == "DONE"
    assert result.used_steps == 4
    assert len(log.read()) == 4
    assert {event.node for event in log.read()} == {"dispatch", "left", "right", "join"}
    assert sorted(event.detail["used_steps"] for event in log.read()) == [1, 2, 3, 4]


def bound():
    return {"dispatch": lambda s: TransformResult(s, "done"),
            "left": lambda s: TransformResult(State(values=(1,)), "done"),
            "right": lambda s: TransformResult(State(values=(2,)), "done")}


def reducers():
    return {"join": lambda entry, branches: TransformResult(
        State(values=tuple(value for branch in branches for value in branch.values)), "done")}


def runnable(driver, spec=None, bindings=None, reduced=None, **kwargs):
    built = driver(spec or wave_spec(), state_type=State,
                   bindings=bound() if bindings is None else bindings,
                   reducers=reducers() if reduced is None else reduced, **kwargs)
    result = built.plan if driver is compile_reference else built.candidate
    assert result is not None, built.findings
    return result


@pytest.mark.parametrize("driver", [compile_reference, generate_graph])
@pytest.mark.parametrize("budget,terminal,steps", [(3, "FAILED_BUDGET", 1), (4, "DONE", 4)])
def test_exact_and_short_budget(tmp_path, driver, budget, terminal, steps):
    called = []
    bindings = bound()
    def work(s):
        called.append(True)
        return TransformResult(s, "done")
    bindings.update(left=work, right=work)
    spec = wave_spec().model_copy(update={"budget": budget})
    log = RunLog(tmp_path / "budget.jsonl")
    result = runnable(driver, spec, bindings).run(State(), run_id="budget", log=log)
    assert (result.terminal, result.used_steps) == (terminal, steps)
    assert len(called) == (0 if budget == 3 else 2)
    if budget == 3:
        assert log.read()[-1].detail == {
            "target": "FAILED_BUDGET", "failure": "wave_budget_refused", "required": 3,
            "remaining_steps": 2, "branch_worst": [1, 1], "used_steps": 1, "max_steps": 3}


@pytest.mark.parametrize("driver", [compile_reference, generate_graph])
@pytest.mark.parametrize("both", [False, True])
def test_branch_failure_completes_siblings_and_charges_join(tmp_path, driver, both):
    visited = []
    def fail(s):
        visited.append("left")
        raise ValueError("synthetic")
    def right(s):
        visited.append("right")
        if both:
            raise ValueError("synthetic right")
        return TransformResult(State(values=(99,)), "done")
    def forbidden(*args):
        pytest.fail("failed wave must not reduce")
    bindings = {**bound(), "left": fail, "right": right}
    initial = State(values=(7,))
    log = RunLog(tmp_path / "failure.jsonl")
    result = runnable(driver, bindings=bindings, reduced={"join": forbidden}).run(initial, run_id="f", log=log)
    assert sorted(visited) == ["left", "right"]
    assert (result.state, result.terminal, result.used_steps) == (initial, "FAILED_VALIDATION", 4)
    assert log.read()[-1].detail["failure"] == "wave_branch_failure"
    assert log.read()[-1].detail["branch_index"] == 0
    assert log.read()[-1].node == "join"


@pytest.mark.parametrize("driver", [compile_reference, generate_graph])
@pytest.mark.parametrize("output", [object(), TransformResult(State(), "undeclared"), TransformResult({}, "done")])
def test_invalid_reducer_fails_closed(tmp_path, driver, output):
    result = runnable(driver, reduced={"join": lambda entry, branches: output}).run(
        State(), run_id="invalid", log=RunLog(tmp_path / "invalid.jsonl"))
    assert (result.terminal, result.used_steps) == ("FAILED_VALIDATION", 4)


@pytest.mark.parametrize("limit", [1, 2, 16])
def test_barrier_overlap_not_elapsed_time(tmp_path, limit):
    barrier = Barrier(2, timeout=0.5)
    observations = []
    def branch(s):
        try:
            barrier.wait()
        except BrokenBarrierError:
            observations.append("timeout")
        else:
            observations.append("overlap")
        return TransformResult(s, "done")
    bindings = {**bound(), "left": branch, "right": branch}
    result = runnable(generate_graph, bindings=bindings, wave_concurrency=limit).run(
        State(), run_id="overlap", log=RunLog(tmp_path / "overlap.jsonl"))
    assert result.terminal == "DONE"
    assert observations == (["timeout"] * 2 if limit == 1 else ["overlap"] * 2)
    (tmp_path / "overlap-observations.json").write_text(json.dumps({"limit": limit, "observations": observations}))


@pytest.mark.parametrize("driver", [compile_reference, generate_graph])
@pytest.mark.parametrize("limit", [0, 17, True, 1.5])
def test_invalid_concurrency_before_work(driver, limit):
    built = driver(wave_spec(), state_type=State, bindings=bound(), reducers=reducers(), wave_concurrency=limit)
    assert any(f.code == "invalid_wave_concurrency" for f in built.findings)


def test_out_of_order_raw_evidence_and_declared_reducer(tmp_path):
    right_recorded = Event()
    class Log(RunLog):
        def append_next(self, event):
            super().append_next(event)
            if event.node == "right":
                right_recorded.set()
    def left(s):
        assert right_recorded.wait(2)
        return TransformResult(State(values=(1,)), "done")
    log = Log(tmp_path / "ordered.jsonl")
    result = runnable(generate_graph, bindings={**bound(), "left": left}).run(State(), run_id="order", log=log)
    assert [event.node for event in log.read()] == ["dispatch", "right", "left", "join"]
    assert result.state == State(values=(1, 2))


@pytest.mark.parametrize("driver", [compile_reference, generate_graph])
def test_audit_failure_produces_no_result(tmp_path, driver):
    class BrokenLog(RunLog):
        def append_next(self, event):
            if event.node == "left":
                raise OSError("synthetic audit refusal")
            super().append_next(event)
    with pytest.raises(AuditError):
        runnable(driver).run(State(), run_id="audit", log=BrokenLog(tmp_path / "audit.jsonl"))


def test_conformance_without_network_sockets(tmp_path, monkeypatch):
    original = socket.socket
    def deny_network(family=socket.AF_INET, *args, **kwargs):
        if family in (socket.AF_INET, socket.AF_INET6):
            raise OSError("network socket denied")
        return original(family, *args, **kwargs)
    monkeypatch.setattr(socket, "socket", deny_network)
    with pytest.raises(OSError, match="network socket denied"):
        socket.socket()
    report = check_conformance(wave_spec(), runnable(generate_graph), state_type=State, bindings=bound(),
                               reducers=reducers(), cases={"wave": State()}, evidence_dir=tmp_path)
    assert report.passed, report.findings
    evidence = report.evidence[0]
    assert evidence.reference_projection_digest == evidence.candidate_projection_digest
    assert evidence.reference_digest == RunLog(evidence.reference_log).digest()
    assert evidence.candidate_digest == RunLog(evidence.candidate_log).digest()


def test_altered_reducer_is_behavioral_mismatch(tmp_path):
    candidate = runnable(generate_graph, reduced={"join": lambda e, b: TransformResult(State(values=(99,)), "done")})
    report = check_conformance(wave_spec(), candidate, state_type=State, bindings=bound(), reducers=reducers(),
                               cases={"wave": State()}, evidence_dir=tmp_path)
    assert not report.passed
    assert any(f.code == "behavioral_mismatch" for f in report.findings)


def test_altered_reducer_output_masked_by_downstream_transform_fails(tmp_path):
    spec = wave_spec()
    spec = spec.model_copy(update={
        "budget": 5,
        "nodes": spec.nodes + (TransformNode(id="after", operation="after"),),
        "edges": (*spec.edges[:-1], Route(source="join", outcome="done", target="after"),
                  Route(source="after", outcome="done", target="DONE")),
    })
    bindings = {**bound(), "after": lambda s: TransformResult(State(values=(99,)), "done")}
    reference = {"join": lambda e, b: TransformResult(State(values=(1,)), "done")}
    candidate = {"join": lambda e, b: TransformResult(State(values=(2,)), "done")}
    report = check_conformance(
        spec, runnable(generate_graph, spec=spec, bindings=bindings, reduced=candidate),
        state_type=State, bindings=bindings, reducers=reference,
        cases={"wave": State()}, evidence_dir=tmp_path)
    assert report.completed == ("wave",)
    assert report.outputs[0].state == State(values=(99,))
    assert not report.passed
    assert any(f.code == "behavioral_mismatch" and f.path == ("cases", "wave", "reducers", "join")
               for f in report.findings)


@pytest.mark.parametrize("masked", [False, True])
def test_identical_reducer_inputs_diverging_across_cases_fail_conformance(tmp_path, masked):
    def counter():
        calls = []
        def reduce(entry, branches):
            calls.append((entry, branches))
            return TransformResult(State(values=(len(calls),)), "done")
        return reduce, calls

    reference, reference_calls = counter()
    candidate, candidate_calls = counter()
    spec = wave_spec()
    bindings = bound()
    if masked:
        spec = spec.model_copy(update={
            "budget": 5,
            "nodes": spec.nodes + (TransformNode(id="after", operation="after"),),
            "edges": (*spec.edges[:-1], Route(source="join", outcome="done", target="after"),
                      Route(source="after", outcome="done", target="DONE")),
        })
        bindings.update(dispatch=lambda s: TransformResult(State(), "done"),
                        after=lambda s: TransformResult(State(values=(99,)), "done"))
    report = check_conformance(
        spec, runnable(generate_graph, spec=spec, bindings=bindings, reduced={"join": candidate}),
        state_type=State, bindings=bindings, reducers={"join": reference},
        cases={"first": State(), "second": State(values=(7,)) if masked else State()}, evidence_dir=tmp_path)
    assert reference_calls == candidate_calls
    assert reference_calls[0] == reference_calls[1]
    assert [output.state.model_dump()["values"] for output in report.outputs] == (
        [(99,), (99,)] if masked else [(1,), (2,)])
    assert report.completed == ("first", "second")
    assert not report.passed
    assert {f.path for f in report.findings if f.code == "behavioral_mismatch"} == {
        ("cases", "second", "reducers", "join", "reference"),
        ("cases", "second", "reducers", "join", "candidate"),
    }


def test_deterministic_reducer_repeated_and_different_inputs_pass(tmp_path):
    def reduce(entry, branches):
        return TransformResult(State(values=entry.values + branches[0].values + branches[1].values), "done")
    report = check_conformance(
        wave_spec(), runnable(generate_graph, reduced={"join": reduce}),
        state_type=State, bindings=bound(), reducers={"join": reduce},
        cases={"first": State(), "different": State(values=(7,)), "repeat": State()}, evidence_dir=tmp_path)
    assert report.passed, report.findings
    assert [output.state.model_dump()["values"] for output in report.outputs] == [(1, 2), (7, 1, 2), (1, 2)]


@pytest.mark.parametrize("driver", [compile_reference, generate_graph])
def test_linear_extraneous_reducers_are_unused(tmp_path, driver):
    spec = WorkflowSpec(entry="dispatch", budget=1, terminals=wave_spec().terminals,
                        nodes=(TransformNode(id="dispatch", operation="dispatch"),),
                        edges=(Route(source="dispatch", outcome="done", target="DONE"),))
    def forbidden(*args):
        pytest.fail("linear workflow must not invoke an unused reducer")
    baseline = driver(spec, state_type=State, bindings=bound())
    extra = driver(spec, state_type=State, bindings=bound(),
                   reducers={"unused": forbidden, "also_unused": None})
    assert extra.findings == baseline.findings == ()
    results, logs = [], []
    for name, built in (("baseline", baseline), ("extra", extra)):
        run = built.plan if driver is compile_reference else built.candidate
        assert run is not None
        log = RunLog(tmp_path / f"{name}.jsonl")
        results.append(run.run(State(values=(7,)), run_id="linear", log=log))
        logs.append(log.read_bytes())
    assert results[0] == results[1]
    assert results[1].state == State(values=(7,))
    assert results[1].terminal == "DONE"
    assert logs[0] == logs[1]
    assert driver(spec, state_type=State, bindings={}, reducers={"unused": forbidden}).findings == (
        driver(spec, state_type=State, bindings={}).findings)


@pytest.mark.parametrize("driver", [compile_reference, generate_graph])
def test_three_uneven_branches_expected_states_and_spend(tmp_path, driver):
    spec = wave_spec()
    spec = spec.model_copy(update={
        "budget": 6,
        "nodes": spec.nodes + (TransformNode(id="left2", operation="left2"),
                               TransformNode(id="third", operation="third")),
        "edges": (Fork(source="dispatch", outcome="done", branches=("left", "right", "third"), join="join"),
                  Route(source="left", outcome="done", target="left2"),
                  *spec.edges[2:], Route(source="left2", outcome="done", target="join"),
                  Route(source="third", outcome="done", target="join")),
    })
    bindings = {**bound(), "left2": lambda s: TransformResult(State(values=s.values + (3,)), "done"),
                "third": lambda s: TransformResult(State(values=(4,)), "done")}
    seen = []
    def reduce(entry, branches):
        seen.append(branches)
        return reducers()["join"](entry, branches)
    result = runnable(driver, spec, bindings, {"join": reduce}).run(
        State(), run_id="three", log=RunLog(tmp_path / "three.jsonl"))
    assert seen == [(State(values=(1, 3)), State(values=(2,)), State(values=(4,)))]
    assert result.state == State(values=(1, 3, 2, 4))
    assert (result.used_steps, result.terminal) == (6, "DONE")


@pytest.mark.parametrize("driver", [compile_reference, generate_graph])
def test_mutable_state_detached_at_branch_and_reducer_boundaries(tmp_path, driver):
    class MutableState(BaseModel):
        model_config = ConfigDict(frozen=True)
        values: list[int]
    leaked = []
    def branch(s):
        assert s.values == [10]
        s.values.append(1)
        leaked.append(s)
        return TransformResult(s, "done")
    def reduce(entry, branches):
        assert entry.values == [10]
        assert [b.values for b in branches] == [[10, 1], [10, 1]]
        entry.values.append(99)
        branches[0].values.append(98)
        return TransformResult(MutableState(values=[42]), "done")
    initial = MutableState(values=[10])
    built = driver(wave_spec(), state_type=MutableState,
                   bindings={"dispatch": lambda s: TransformResult(s, "done"), "left": branch, "right": branch},
                   reducers={"join": reduce})
    run = built.plan if driver is compile_reference else built.candidate
    assert run is not None, built.findings
    result = run.run(initial, run_id="detached", log=RunLog(tmp_path / "detached.jsonl"))
    assert initial.values == [10]
    assert [s.values for s in leaked] == [[10, 1], [10, 1]]
    assert result.state.values == [42]
    assert result.terminal == "DONE"


@pytest.mark.parametrize("driver", [compile_reference, generate_graph])
def test_join_binding_is_authoritative_and_stray_binding_ignored(tmp_path, driver):
    def forbidden(s):
        pytest.fail("join operation binding must never run")
    result = runnable(driver, bindings={**bound(), "join": forbidden}).run(
        State(), run_id="authoritative", log=RunLog(tmp_path / "join.jsonl"))
    assert (result.state.values, result.used_steps) == ((1, 2), 4)
    linear = WorkflowSpec(entry="only", budget=1, terminals=wave_spec().terminals,
                          nodes=(TransformNode(id="only", operation="missing"),),
                          edges=(Route(source="only", outcome="done", target="DONE"),))
    built = driver(linear, state_type=State, bindings={})
    assert any(f.code == "unbound_reference" for f in built.findings)


def invalid_wave(case):
    spec = wave_spec()
    nodes, edges = list(spec.nodes), list(spec.edges)
    reduced = reducers()
    if case == "missing_reducer":
        reduced = {}
    elif case == "extra_reducer":
        reduced["left"] = reduced["join"]
    elif case == "join_kind":
        nodes[-1] = DecisionNode(id="join", value="join", cases=("done",))
    elif case in ("gate", "judgment", "loop"):
        nodes[1] = {"gate": GateNode(id="left"),
                    "judgment": JudgmentNode(id="left", options=("done",)),
                    "loop": LoopNode(id="left", exit_predicate="left", max_iterations=1)}[case]
        edges = [edge for edge in edges if edge.source != "left"]
        edges.extend(Route(source="left", outcome=label, target="join") for label in nodes[1].route_labels)
    elif case == "under_loop":
        nodes.append(LoopNode(id="outer", exit_predicate="outer", max_iterations=1))
        edges[-1] = Route(source="join", outcome="done", target="outer")
        edges.extend((Route(source="outer", outcome="repeat", target="dispatch"),
                      Route(source="outer", outcome="exit", target="DONE"),
                      Route(source="outer", outcome="exhausted", target="DONE")))
        spec = spec.model_copy(update={"entry": "outer"})
    elif case in ("branch_kind", "branch_model", "join_model"):
        index = 3 if case == "join_model" else 1
        node = nodes[index]
        nodes[index] = (DecisionNode(id=node.id, value=node.operation, cases=("done",))
                        if case == "branch_kind" else node.model_copy(update={"model_operation": True}))
    elif case == "overlap":
        edges[1] = Route(source="left", outcome="done", target="right")
    elif case == "prejoin_terminal":
        edges[1] = Route(source="left", outcome="done", target="DONE")
    elif case == "unreachable":
        nodes.append(TransformNode(id="entry", operation="entry"))
        edges.append(Route(source="entry", outcome="done", target="DONE"))
        spec = spec.model_copy(update={"entry": "entry"})
    elif case in ("nested", "shared_join", "sequential"):
        nodes.extend(TransformNode(id=name, operation=name) for name in ("b2", "c2"))
        join = "join" if case != "sequential" else "join2"
        source = {"nested": "left", "shared_join": "other", "sequential": "join"}[case]
        if case == "shared_join":
            nodes.append(TransformNode(id="other", operation="other"))
        else:
            edges = [edge for edge in edges if edge.source != source]
        edges.extend((Fork(source=source, outcome="done", branches=("b2", "c2"), join=join),
                      Route(source="b2", outcome="done", target=join),
                      Route(source="c2", outcome="done", target=join)))
        if case == "sequential":
            nodes.append(TransformNode(id="join2", operation="join2"))
            edges.append(Route(source="join2", outcome="done", target="DONE"))
            reduced["join2"] = reduced["join"]
    return spec.model_copy(update={"nodes": tuple(nodes), "edges": tuple(edges)}), reduced


@pytest.mark.parametrize("driver", [compile_reference, generate_graph])
@pytest.mark.parametrize("case", ["missing_reducer", "extra_reducer", "join_kind", "branch_model",
                                 "join_model", "overlap", "prejoin_terminal", "unreachable", "nested",
                                 "shared_join", "sequential", "gate", "judgment", "loop", "under_loop"])
def test_negative_admission_before_any_binding(driver, case):
    spec, reduced = invalid_wave(case)
    calls = []
    def forbidden(*args):
        calls.append(True)
        pytest.fail("admission invoked user code")
    bindings = {getattr(node, "operation", getattr(node, "value", "")): forbidden for node in spec.nodes}
    reduced = {key: forbidden for key in reduced}
    built = driver(spec, state_type=State, bindings=bindings, reducers=reduced)
    assert built.findings
    assert (built.plan if driver is compile_reference else built.candidate) is None
    assert not calls


@pytest.mark.parametrize("change", ["order", "extra", "join"])
def test_structural_wave_adversaries(tmp_path, change):
    spec = wave_spec()
    altered = spec
    bindings, reduced = bound(), reducers()
    if change == "order":
        altered = spec.model_copy(update={"edges": (spec.edges[0].model_copy(update={
            "branches": ("right", "left")}), *spec.edges[1:])})
    elif change == "extra":
        altered = spec.model_copy(update={
            "nodes": spec.nodes + (TransformNode(id="third", operation="third"),),
            "edges": (spec.edges[0].model_copy(update={"branches": ("left", "right", "third")}),
                      *spec.edges[1:], Route(source="third", outcome="done", target="join"))})
        bindings["third"] = bindings["left"]
    else:
        altered = spec.model_copy(update={
            "nodes": tuple(node.model_copy(update={"id": "other_join"}) if node.id == "join" else node
                           for node in spec.nodes),
            "edges": (spec.edges[0].model_copy(update={"join": "other_join"}),
                      Route(source="left", outcome="done", target="other_join"),
                      Route(source="right", outcome="done", target="other_join"),
                      Route(source="other_join", outcome="done", target="DONE"))})
        reduced = {"other_join": reduced["join"]}
    candidate = runnable(generate_graph, altered, bindings, reduced)
    report = check_conformance(spec, candidate, state_type=State, bindings=bound(), reducers=reducers(),
                               cases={"wave": State()}, evidence_dir=tmp_path)
    assert not report.passed
    assert all(f.code == "structural_mismatch" for f in report.findings)
    assert not report.attempted


def test_canonical_projection_keeps_raw_adversarial_order(tmp_path, monkeypatch):
    right_recorded, left_started = Event(), Event()
    original = RunLog.append_next
    def append(log, event):
        original(log, event)
        if log.path.name.endswith("candidate.jsonl") and event.node == "right":
            right_recorded.set()
    monkeypatch.setattr(RunLog, "append_next", append)
    def left(s):
        left_started.set()
        assert right_recorded.wait(2)
        return bound()["left"](s)
    def right(s):
        assert left_started.wait(2)
        return bound()["right"](s)
    candidate = runnable(generate_graph, bindings={**bound(), "left": left, "right": right}, wave_concurrency=16)
    report = check_conformance(wave_spec(), candidate, state_type=State, bindings=bound(), reducers=reducers(),
                               cases={"wave": State()}, evidence_dir=tmp_path, wave_concurrency=1)
    assert report.passed, report.findings
    evidence = report.evidence[0]
    assert evidence.reference_digest != evidence.candidate_digest
    assert evidence.reference_projection_digest == evidence.candidate_projection_digest
    assert [event.node for event in RunLog(evidence.candidate_log).read()] == ["dispatch", "right", "left", "join"]


@pytest.mark.parametrize("configured,expected", [(None, 4), (2, 2), (1, 1)])
def test_worker_bound_and_default_observed(tmp_path, configured, expected):
    branches = tuple(f"branch{i}" for i in range(6))
    spec = WorkflowSpec(entry="dispatch", budget=8, terminals=wave_spec().terminals,
                        nodes=tuple(TransformNode(id=name, operation=name) for name in ("dispatch", *branches, "join")),
                        edges=(Fork(source="dispatch", outcome="done", branches=branches, join="join"),
                               *(Route(source=name, outcome="done", target="join") for name in branches),
                               Route(source="join", outcome="done", target="DONE")))
    barrier = Barrier(expected, timeout=0.5)
    lock = Lock()
    active = peak = 0
    def branch(s):
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        try:
            barrier.wait()
        except BrokenBarrierError:
            pass
        finally:
            with lock:
                active -= 1
        return TransformResult(s, "done")
    bindings = {"dispatch": bound()["dispatch"], **{name: branch for name in branches}}
    log = RunLog(tmp_path / "bounded.jsonl")
    result = runnable(generate_graph, spec, bindings, wave_concurrency=configured).run(State(), run_id="bound", log=log)
    assert (peak, active, result.used_steps, result.terminal) == (expected, 0, 8, "DONE")
    assert log.read()[0].detail["wave_concurrency"] == expected
    (tmp_path / "bound-observations.json").write_text(json.dumps({"configured": configured, "peak": peak}))


def test_reference_is_sequential_even_with_concurrency_parameter(tmp_path):
    barrier = Barrier(2, timeout=0.1)
    observations = []
    def branch(s):
        try:
            barrier.wait()
        except BrokenBarrierError:
            observations.append("timeout")
        return TransformResult(s, "done")
    result = runnable(compile_reference, bindings={**bound(), "left": branch, "right": branch}, wave_concurrency=16).run(
        State(), run_id="sequential", log=RunLog(tmp_path / "sequential.jsonl"))
    assert result.terminal == "DONE"
    assert observations == ["timeout", "timeout"]


@pytest.mark.parametrize("mode", ["failure", "refusal", "audit"])
def test_failed_wave_conformance_retains_evidence(tmp_path, monkeypatch, mode):
    bindings = bound()
    spec = wave_spec()
    if mode == "failure":
        bindings["left"] = lambda s: object()
    elif mode == "refusal":
        spec = spec.model_copy(update={"budget": 3})
    else:
        original = RunLog.append_next
        def append(log, event):
            if event.node == "left":
                raise OSError("synthetic append failure")
            original(log, event)
        monkeypatch.setattr(RunLog, "append_next", append)
    candidate = runnable(generate_graph, spec, bindings)
    report = check_conformance(spec, candidate, state_type=State, bindings=bindings, reducers=reducers(),
                               cases={"wave": State()}, evidence_dir=tmp_path)
    assert report.passed is (mode != "audit")
    if mode == "audit":
        assert report.findings[0].code == "incomplete"
    else:
        assert report.outputs[0].terminal == ("FAILED_BUDGET" if mode == "refusal" else "FAILED_VALIDATION")
        assert report.evidence[0].reference_projection_digest == report.evidence[0].candidate_projection_digest
