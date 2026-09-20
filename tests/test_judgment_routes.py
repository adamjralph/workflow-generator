"""Ticket 11 public seam: authored spec, supplied candidate, persisted evidence."""
import json

import pytest
from pydantic import BaseModel, ConfigDict

from agent_lab.conformance import check_conformance
from agent_lab.generation import generate_graph
from agent_lab.judgment import StubSource
from agent_lab.reference import JudgmentBinding
from agent_lab.spec import JudgmentNode, Route, WorkflowSpec
from agent_lab.state import Intervention


class State(BaseModel):
    model_config = ConfigDict(frozen=True)
    assessment: str = "business assessment"
    notes: list[str] = []


def spec(budget=1):
    return WorkflowSpec(
        entry="judge", budget=budget,
        nodes=(JudgmentNode(id="judge", options=("review_follow_up", "payment_follow_up", "not_a_fit")),),
        edges=(Route(source="judge", outcome="review_follow_up", target="REVIEW"),
               Route(source="judge", outcome="payment_follow_up", target="PAYMENT"),
               Route(source="judge", outcome="not_a_fit", target="STOP")),
        terminals=("REVIEW", "PAYMENT", "STOP", "FAILED_VALIDATION", "FAILED_BUDGET"),
    )


def judgments(source):
    return {"judge": JudgmentBinding(source, lambda state: state.assessment)}


@pytest.mark.parametrize("choice, terminal", [(Intervention.REVIEW_FOLLOW_UP, "REVIEW"),
                                               (Intervention.PAYMENT_FOLLOW_UP, "PAYMENT"),
                                               (Intervention.NOT_A_FIT, "STOP")])
def test_explicit_judgment_routes_and_full_evidence(tmp_path, choice, terminal):
    initial = State()
    generated = generate_graph(spec(), state_type=State, bindings={},
                               judgments=judgments(StubSource(choice)))
    assert generated.candidate is not None
    report = check_conformance(spec(), generated.candidate, state_type=State, bindings={},
                               judgments=judgments(StubSource(choice)), cases={"business": initial},
                               evidence_dir=tmp_path)
    assert report.passed, report.findings
    evidence = report.evidence[0]
    assert evidence.reference_log.read_bytes() == evidence.candidate_log.read_bytes()
    event = json.loads(evidence.reference_log.read_text())
    assert event["terminal"] == terminal
    assert event["detail"]["judgment"] == {
        "intervention": choice.value, "confidence": 0.99,
        "review_gap_evidenced": 0.97, "source": "stub",
    }
    assert event["detail"]["used_steps"] == 1
    assert initial == State()


@pytest.mark.parametrize("side", ["shared", "reference_live", "candidate_live"])
def test_check_requires_independent_offline_sources_before_execution(tmp_path, side):
    from agent_lab.judgment import JevSource

    class NeverLive(JevSource):
        def judge(self, assessment):
            pytest.fail("conformance called a live source")

    source = StubSource()
    reference = NeverLive() if side == "reference_live" else source
    candidate = NeverLive() if side == "candidate_live" else source
    if side == "reference_live":
        candidate = StubSource()
    generated = generate_graph(spec(), state_type=State, bindings={}, judgments=judgments(candidate))
    assert generated.candidate is not None
    with pytest.raises(ValueError, match="independent|offline"):
        check_conformance(spec(), generated.candidate, state_type=State, bindings={},
                          judgments=judgments(reference), cases={"case": State()}, evidence_dir=tmp_path)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("field, value", [
    ("intervention", Intervention.PAYMENT_FOLLOW_UP), ("confidence", 0.5),
    ("review_gap_evidenced", 0.5), ("source", "recorded"),
    ("intervention", "review_follow_up"), ("confidence", "0.99"),
    ("review_gap_evidenced", "0.97"),
])
def test_changed_judgment_evidence_cannot_pass(tmp_path, field, value):
    class AlteredSource:
        name = "stub"

        def judge(self, assessment):
            return StubSource().judge(assessment).model_copy(update={field: value})

    generated = generate_graph(spec(), state_type=State, bindings={}, judgments=judgments(AlteredSource()))
    report = check_conformance(spec(), generated.candidate, state_type=State, bindings={},
                              judgments=judgments(StubSource()), cases={"case": State()}, evidence_dir=tmp_path)
    assert not report.passed
    assert {finding.path[-1] for finding in report.findings} >= {"trace", "bytes", "digest"}


@pytest.mark.parametrize("change", ["options", "routing", "unreachable"])
def test_actual_judgment_structure_is_checked_before_execution(tmp_path, change):
    authored = spec()
    if change == "options":
        altered = authored.model_copy(update={
            "nodes": (JudgmentNode(id="judge", options=("review_follow_up", "payment_follow_up")),),
            "edges": authored.edges[:2],
        })
        location = ("nodes", "judge")
    elif change == "routing":
        altered = authored.model_copy(update={"edges": (
            authored.edges[0].model_copy(update={"target": "STOP"}), *authored.edges[1:])})
        location = ("edges", "judge", "review_follow_up")
    else:
        altered = authored.model_copy(update={
            "nodes": (*authored.nodes, JudgmentNode(id="dead", options=("not_a_fit",))),
            "edges": (*authored.edges, Route(source="dead", outcome="not_a_fit", target="STOP")),
        })
        location = ("nodes", "dead")

    class Forbidden:
        name = "stub"

        def judge(self, assessment):
            pytest.fail("structural checking invoked source")

    def assessment(state):
        pytest.fail("compilation or structural checking invoked adapter")

    reference = {"judge": JudgmentBinding(Forbidden(), assessment)}
    candidate = {key: JudgmentBinding(Forbidden(), assessment) for key in ("judge", "dead")}
    generated = generate_graph(altered, state_type=State, bindings={}, judgments=candidate)
    assert generated.candidate is not None
    report = check_conformance(authored, generated.candidate, state_type=State, bindings={},
                              judgments=reference, cases={"case": State()}, evidence_dir=tmp_path)
    assert not report.passed and not report.attempted
    assert any(f.code == "structural_mismatch" and f.path == location for f in report.findings)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("failure", ["missing", "unsupported", "adapter", "source"])
@pytest.mark.parametrize("unreachable", [False, True])
def test_all_judgment_declarations_and_bindings_are_checked(tmp_path, failure, unreachable):
    from agent_lab.reference import compile_reference

    authored = spec()
    key = "dead" if unreachable else "judge"
    options = ("arbitrary",) if failure == "unsupported" else ("not_a_fit",)
    node = JudgmentNode(id=key, options=options)
    edges = tuple(Route(source=key, outcome=label, target="STOP") for label in options)
    authored = authored.model_copy(update={
        "nodes": (*authored.nodes, node) if unreachable else (node,),
        "edges": (*authored.edges, *edges) if unreachable else edges,
    })
    bound = judgments(StubSource())
    if failure == "missing":
        bound.pop(key, None)
    else:
        bound[key] = JudgmentBinding(object() if failure == "source" else StubSource(),
                                     None if failure == "adapter" else lambda state: state.assessment)
    compiled = compile_reference(authored, state_type=State, bindings={}, judgments=bound)
    generated = generate_graph(authored, state_type=State, bindings={}, judgments=bound)
    assert compiled.plan is generated.candidate is None
    expected = "unsupported_options" if failure == "unsupported" else "unbound_reference"
    assert any(f.code == expected for f in compiled.findings)
    report = check_conformance(authored, None, state_type=State, bindings={}, judgments=bound,
                              cases={"case": State()}, evidence_dir=tmp_path)
    assert not report.passed and not report.attempted


def test_independent_replay_progress_and_repeated_evidence(tmp_path):
    class Replay:
        name = "recorded"

        def __init__(self):
            self.inputs = []
            self.choices = iter([Intervention.REVIEW_FOLLOW_UP, Intervention.PAYMENT_FOLLOW_UP])

        def judge(self, assessment):
            self.inputs.append(assessment)
            return StubSource(next(self.choices)).judge(assessment).model_copy(update={"source": "recorded"})

    logs = []
    for _ in range(2):
        # Sources are explicit run inputs: fresh independent progress for each check.
        reference, candidate = Replay(), Replay()
        generated = generate_graph(spec(), state_type=State, bindings={}, judgments=judgments(candidate))
        report = check_conformance(spec(), generated.candidate, state_type=State, bindings={},
                                  judgments=judgments(reference), cases={"one": State(assessment="one"),
                                  "two": State(assessment="two")}, evidence_dir=tmp_path)
        assert report.passed, report.findings
        assert reference.inputs == candidate.inputs == ["one", "two"]
        run_logs = [item.reference_log.read_bytes() for item in report.evidence]
        assert [json.loads(raw)["terminal"] for raw in run_logs] == ["REVIEW", "PAYMENT"]
        logs.append(run_logs)
    assert logs[0] == logs[1]


def test_different_assessment_inputs_cannot_silently_pass_with_fixed_sources(tmp_path):
    generated = generate_graph(spec(), state_type=State, bindings={}, judgments={
        "judge": JudgmentBinding(StubSource(), lambda state: "different input")})
    report = check_conformance(spec(), generated.candidate, state_type=State, bindings={},
                              judgments=judgments(StubSource()), cases={"case": State()}, evidence_dir=tmp_path)
    assert not report.passed
    assert {f.path[-1] for f in report.findings} >= {"trace", "bytes", "digest"}


def test_compilation_copies_judgment_binding_maps_and_declarations(tmp_path):
    from agent_lab.reference import compile_reference
    from agent_lab.runlog import RunLog

    authored = spec()
    bound = judgments(StubSource())
    plan = compile_reference(authored, state_type=State, bindings={}, judgments=bound).plan
    graph = generate_graph(authored, state_type=State, bindings={}, judgments=bound).candidate
    assert plan is not None and graph is not None
    bound.clear()
    object.__setattr__(authored.nodes[0], "options", ("not_a_fit",))
    for index, executable in enumerate((plan, graph)):
        result = executable.run(State(), run_id="copied", log=RunLog(tmp_path / f"{index}.jsonl"))
        assert result.terminal == "REVIEW"
        assert result.state == State()
