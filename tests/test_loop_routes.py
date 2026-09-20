"""Ticket 12: authored retries through public execution and conformance APIs."""
import pytest
from pydantic import BaseModel, ConfigDict, Field

from agent_lab.conformance import check_conformance
from agent_lab.generation import generate_graph
from agent_lab.reference import AuditError, JudgmentBinding, compile_reference, TransformResult
from agent_lab.judgment import StubSource
from agent_lab.state import Intervention
from agent_lab.runlog import RunLog
from agent_lab.spec import JudgmentNode, LoopNode, Route, TransformNode, WorkflowSpec


class State(BaseModel):
    model_config = ConfigDict(frozen=True)
    count: int = 0
    goal: int = 1
    items: list[int] = Field(default_factory=list)


def retry(budget=10):
    return WorkflowSpec(
        entry="retry", budget=budget,
        nodes=(LoopNode(id="retry", max_iterations=2, exit_predicate="done?"),
               TransformNode(id="body", operation="increment", outcomes=("next",))),
        edges=(Route(source="retry", outcome="repeat", target="body"),
               Route(source="retry", outcome="exit", target="DONE"),
               Route(source="retry", outcome="exhausted", target="EXHAUSTED"),
               Route(source="body", outcome="next", target="retry")),
        terminals=("DONE", "EXHAUSTED", "FAILED_VALIDATION", "FAILED_BUDGET"),
    )


def bindings():
    return {"done?": lambda s: s.count >= s.goal,
            "increment": lambda s: TransformResult(State(count=s.count + 1, goal=s.goal), "next")}


@pytest.mark.parametrize("goal,routes,counts,terminal", [
    (0, ["exit"], [0], "DONE"),
    (1, ["repeat", "exit"], [1, 1], "DONE"),
    (2, ["repeat", "repeat", "exit"], [1, 2, 2], "DONE"),
    (3, ["repeat", "repeat", "exhausted"], [1, 2, 2], "EXHAUSTED"),
])
def test_bounded_retry_expected_routes_and_exact_evidence(tmp_path, goal, routes, counts, terminal):
    spec = retry()
    generated = generate_graph(spec, state_type=State, bindings=bindings())
    assert generated.candidate is not None, generated.findings
    report = check_conformance(spec, generated.candidate, state_type=State, bindings=bindings(),
                               cases={"retry": State(goal=goal)}, evidence_dir=tmp_path)
    assert report.passed, report.findings
    record = report.evidence[0]
    plain, graph = RunLog(record.reference_log), RunLog(record.candidate_log)
    loops = [event for event in plain.read() if event.node == "retry"]
    assert [event.transition for event in loops] == routes
    assert [event.detail["repeat_count"] for event in loops] == counts
    assert loops[-1].terminal == terminal
    assert plain.read_bytes() == graph.read_bytes()
    assert plain.digest() == graph.digest()


@pytest.mark.parametrize("budget,goal,terminal,steps,calls", [
    (1, 0, "DONE", 1, 1), (1, 3, "FAILED_BUDGET", 1, 1),
    (2, 3, "FAILED_BUDGET", 2, 1), (4, 3, "FAILED_BUDGET", 4, 2),
    (5, 3, "EXHAUSTED", 5, 3), (5, 2, "DONE", 5, 3),
])
def test_budget_reserved_before_every_loop_visit(tmp_path, budget, goal, terminal, steps, calls):
    observed = []
    bound = bindings()
    bound["done?"] = lambda s: observed.append(s.count) or s.count >= s.goal
    spec = retry(budget)
    candidate = generate_graph(spec, state_type=State, bindings=bound).candidate
    report = check_conformance(spec, candidate, state_type=State, bindings=bound,
                               cases={"budget": State(goal=goal)}, evidence_dir=tmp_path)
    assert report.passed
    assert len(observed) == 2 * calls
    events = RunLog(report.evidence[0].reference_log).read()
    assert events[-1].terminal == terminal
    assert events[-1].detail["used_steps"] == steps


@pytest.mark.parametrize("value", [1, 0, "yes", None, [], ValueError("bad predicate")])
def test_invalid_predicates_fail_without_body_or_coercion(tmp_path, value):
    def predicate(state):
        state.items.append(99)
        if isinstance(value, Exception):
            raise value
        return value

    bound = bindings() | {"done?": predicate}
    candidate = generate_graph(retry(), state_type=State, bindings=bound).candidate
    initial = State()
    report = check_conformance(retry(), candidate, state_type=State, bindings=bound,
                               cases={"invalid": initial}, evidence_dir=tmp_path)
    assert report.passed
    events = RunLog(report.evidence[0].reference_log).read()
    assert len(events) == 1
    assert events[0].terminal == "FAILED_VALIDATION"
    assert events[0].detail["repeat_count"] == 0
    assert events[0].detail["used_steps"] == 1
    assert initial.items == []


def test_snapshot_isolation_copied_bindings_and_fresh_counters(tmp_path):
    def predicate(state):
        state.items.append(99)
        return state.count >= state.goal

    spec = retry()
    bound = bindings() | {"done?": predicate}
    plan = compile_reference(spec, state_type=State, bindings=bound).plan
    candidate = generate_graph(spec, state_type=State, bindings=bound).candidate
    bound.clear()
    object.__setattr__(spec.nodes[0], "max_iterations", 100)
    initial = State(goal=3)
    for index, driver in enumerate((plan, candidate, plan, candidate)):
        result = driver.run(initial, run_id="same", log=RunLog(tmp_path / f"{index}.jsonl"))
        assert result.state == State(count=2, goal=3)
        assert result.terminal == "EXHAUSTED"
        assert result.used_steps == 5
        assert initial == State(goal=3)


@pytest.mark.parametrize("change", ["bound", "predicate", "route", "unreachable"])
def test_structural_loop_changes_prevent_all_execution(tmp_path, change):
    spec = retry()
    data = spec.model_dump()
    if change == "bound":
        data["nodes"][0]["max_iterations"] = 3
    elif change == "predicate":
        data["nodes"][0]["exit_predicate"] = "other"
    elif change == "route":
        data["edges"][1]["target"] = "EXHAUSTED"
    else:
        data["nodes"] += ({"id": "unused", "kind": "loop", "max_iterations": 1,
                           "exit_predicate": "other"},)
        data["edges"] += tuple({"kind": "route", "source": "unused", "outcome": label,
                                 "target": "DONE"} for label in ("exit", "repeat", "exhausted"))
    def forbidden(state):
        pytest.fail("Structural check invoked a binding")
    bound = {"done?": forbidden, "other": forbidden, "increment": forbidden}
    candidate = generate_graph(data, state_type=State, bindings=bound).candidate
    assert candidate is not None
    report = check_conformance(spec, candidate, state_type=State, bindings=bound,
                               cases={"structure": State()}, evidence_dir=tmp_path)
    assert not report.passed and not report.attempted
    assert all(f.code == "structural_mismatch" for f in report.findings)
    assert all(f.path[0] in ("nodes", "edges") for f in report.findings)


def test_changed_predicate_behavior_does_not_pass(tmp_path):
    candidate = generate_graph(retry(), state_type=State,
                               bindings=bindings() | {"done?": lambda s: True}).candidate
    report = check_conformance(retry(), candidate, state_type=State, bindings=bindings(),
                               cases={"different": State(goal=3)}, evidence_dir=tmp_path)
    assert not report.passed
    assert {f.path[-1] for f in report.findings} >= {"state", "terminal", "trace", "bytes", "digest"}


@pytest.mark.parametrize("binding", [None, 42])
@pytest.mark.parametrize("unreachable", [False, True])
def test_missing_and_invalid_predicate_bindings_are_located(tmp_path, binding, unreachable):
    data = retry().model_dump()
    if unreachable:
        data["entry"] = "body"
        data["edges"][3]["target"] = "DONE"
    bound = bindings()
    if binding is None:
        del bound["done?"]
    else:
        bound["done?"] = binding
    compiled = compile_reference(data, state_type=State, bindings=bound)
    generated = generate_graph(data, state_type=State, bindings=bound)
    report = check_conformance(data, generated.candidate, state_type=State, bindings=bound,
                               cases={"bad": State()}, evidence_dir=tmp_path)
    assert compiled.plan is None and generated.candidate is None and not report.passed
    assert any(f.path == ("nodes", 0, "exit_predicate") for f in report.findings)


def test_distinct_loop_counters_survive_reentry(tmp_path):
    spec = WorkflowSpec(
        entry="a", budget=10,
        nodes=(LoopNode(id="a", max_iterations=1, exit_predicate="false"),
               LoopNode(id="b", max_iterations=2, exit_predicate="false")),
        edges=tuple(Route(source=node, outcome=label, target=target)
                    for node, label, target in [
                        ("a", "repeat", "b"), ("a", "exit", "DONE"), ("a", "exhausted", "b"),
                        ("b", "repeat", "a"), ("b", "exit", "DONE"), ("b", "exhausted", "DONE")]),
        terminals=("DONE", "FAILED_VALIDATION", "FAILED_BUDGET"))
    bound = {"false": lambda s: False}
    candidate = generate_graph(spec, state_type=State, bindings=bound).candidate
    report = check_conformance(spec, candidate, state_type=State, bindings=bound,
                               cases={"first": State(), "fresh": State()}, evidence_dir=tmp_path)
    assert report.passed
    for record in report.evidence:
        assert [(e.node, e.transition, e.detail["repeat_count"]) for e in RunLog(record.reference_log).read()] == [
            ("a", "repeat", 1), ("b", "repeat", 1), ("a", "exhausted", 1),
            ("b", "repeat", 2), ("a", "exhausted", 1), ("b", "exhausted", 2)]


def test_offline_judgment_inside_retry_reproduces_full_evidence(tmp_path):
    class Replay:
        name = "recorded"

        def __init__(self):
            self.inputs = []
            self.choices = iter([Intervention.REVIEW_FOLLOW_UP, Intervention.PAYMENT_FOLLOW_UP])

        def judge(self, assessment):
            self.inputs.append(assessment)
            return StubSource(next(self.choices)).judge(assessment).model_copy(update={"source": "recorded"})

    data = retry().model_dump()
    data["nodes"] += (JudgmentNode(id="judge", options=("review_follow_up", "payment_follow_up")).model_dump(),)
    data["edges"][0]["target"] = "judge"
    data["edges"] += (Route(source="judge", outcome="review_follow_up", target="body").model_dump(),
                       Route(source="judge", outcome="payment_follow_up", target="body").model_dump())
    logs = []
    for _ in range(2):
        plain, graph = Replay(), Replay()
        def judgments(source):
            return {"judge": JudgmentBinding(source, lambda s: f"attempt {s.count}")}
        candidate = generate_graph(data, state_type=State, bindings=bindings(), judgments=judgments(graph)).candidate
        report = check_conformance(data, candidate, state_type=State, bindings=bindings(),
                                   judgments=judgments(plain), cases={"retry": State(goal=3)}, evidence_dir=tmp_path)
        assert report.passed
        assert plain.inputs == graph.inputs == ["attempt 0", "attempt 1"]
        log = RunLog(report.evidence[0].reference_log)
        events = [e for e in log.read() if e.node == "judge"]
        assert [e.transition for e in events] == ["review_follow_up", "payment_follow_up"]
        assert all(e.detail["judgment"]["source"] == "recorded" and e.detail["assessment_sha"] for e in events)
        logs.append(log.read_bytes())
    assert logs[0] == logs[1]


@pytest.mark.parametrize("driver", ["reference", "graph", "check", "check-candidate"])
def test_real_audit_failure_stops_before_body(tmp_path, driver):
    calls = []
    def predicate(state):
        calls.append("predicate")
        # Sabotage this run's actual audit destination, not a mocked writer.
        for lock in tmp_path.rglob("*.reference.lock"):
            if driver == "check-candidate" and "candidate" not in lock.name:
                continue
            path = lock.with_name(lock.name.removesuffix(".reference.lock"))
            path.mkdir()
        return False

    bound = bindings() | {"done?": predicate,
                          "increment": lambda s: calls.append("body")}
    candidate = generate_graph(retry(), state_type=State, bindings=bound).candidate
    if driver.startswith("check"):
        report = check_conformance(retry(), candidate, state_type=State,
                                   bindings=bindings() if driver == "check-candidate" else bound,
                                   cases={"audit": State()}, evidence_dir=tmp_path)
        assert not report.passed and not report.completed
        assert report.findings[0].code == "incomplete"
        assert report.findings[0].path[-1] == ("candidate" if driver == "check-candidate" else "reference")
    else:
        runnable = (compile_reference(retry(), state_type=State, bindings=bound).plan
                    if driver == "reference" else candidate)
        with pytest.raises(AuditError):
            runnable.run(State(), run_id="audit", log=RunLog(tmp_path / "audit.jsonl"))
    assert calls == ["predicate"]
