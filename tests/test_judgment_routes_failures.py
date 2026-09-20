"""Ticket 11 failure contracts at the approved execution/conformance seam."""
import hashlib
import json

import pytest
from pydantic import BaseModel, ConfigDict

from agent_lab.conformance import check_conformance
from agent_lab.generation import generate_graph
from agent_lab.judgment import RecordedSource, StubSource
from agent_lab.reference import AuditError, JudgmentBinding, TransformResult, compile_reference
from agent_lab.runlog import RunLog
from agent_lab.spec import JudgmentNode, Route, TransformNode
from agent_lab.state import Intervention
from test_judgment_routes import State, judgments, spec


class SuppliedSource:
    """Explicit offline boundary fixture; each execution gets its own instance."""

    def __init__(self, result=None, error=None, effect=None):
        self.result = result
        self.error = error
        self.effect = effect
        self.inputs = []

    def judge(self, assessment):
        self.inputs.append(assessment)
        if self.effect is not None:
            self.effect()
        if self.error is not None:
            raise self.error
        return self.result


def with_later_work(authored):
    """Only the payment route reaches later work; review stops immediately."""
    return authored.model_copy(update={
        "nodes": authored.nodes + (TransformNode(id="later", operation="later"),),
        "edges": tuple(edge.model_copy(update={"target": "later"})
                       if edge.outcome == "payment_follow_up" else edge
                       for edge in authored.edges) +
                 (Route(source="later", outcome="done", target="PAYMENT"),),
    })


def valid_judgment():
    return StubSource(Intervention.REVIEW_FOLLOW_UP).judge("fixture")


def checked(tmp_path, authored, reference, candidate, *, bindings=None, initial=None):
    bindings = {} if bindings is None else bindings
    generated = generate_graph(authored, state_type=State, bindings=bindings, judgments=candidate)
    assert generated.candidate is not None, generated.findings
    return check_conformance(
        authored, generated.candidate, state_type=State, bindings=bindings,
        judgments=reference, cases={"first": initial or State()}, evidence_dir=tmp_path,
    )


def paired_events(report):
    assert report.passed, report.findings
    assert report.attempted == report.completed == ("first",)
    evidence = report.evidence[0]
    plain, graph = RunLog(evidence.reference_log), RunLog(evidence.candidate_log)
    assert plain.read_bytes() == graph.read_bytes()
    assert plain.digest() == graph.digest()
    return plain.read()


@pytest.mark.parametrize("bad", [
    None, {}, "review_follow_up",
    valid_judgment().model_dump(),
    valid_judgment().model_copy(update={"intervention": "invented"}),
    valid_judgment().model_copy(update={"confidence": -0.1}),
    valid_judgment().model_copy(update={"review_gap_evidenced": 1.1}),
    valid_judgment().model_copy(update={"confidence": float("nan")}),
    valid_judgment().model_copy(update={"source": "invented"}),
    valid_judgment().model_copy(update={"intervention": "review_follow_up"}),
    valid_judgment().model_copy(update={"confidence": "0.99"}),
    valid_judgment().model_copy(update={"review_gap_evidenced": "0.97"}),
    valid_judgment().model_copy(update={"confidence": True}),
], ids=["missing", "empty", "string", "dict", "choice", "confidence", "probability", "nan", "provenance",
        "unchecked-string-choice", "unchecked-string-confidence", "unchecked-string-probability", "bool-confidence"])
def test_malformed_and_unchecked_judgments_record_validation_failure(tmp_path, bad):
    sources = [SuppliedSource(bad), SuppliedSource(bad)]
    events = paired_events(checked(tmp_path, spec(), *(judgments(s) for s in sources)))
    assert len(events) == 1
    assert events[0].terminal == "FAILED_VALIDATION"
    assert events[0].transition is None
    assert events[0].detail["judgment"] is None
    assert events[0].detail["used_steps"] == 1
    assert [s.inputs for s in sources] == [[State().assessment], [State().assessment]]


@pytest.mark.parametrize("failure", ["adapter", "source", "nontext", "bytes"])
def test_adapter_and_source_failures_are_recorded_without_fallback(tmp_path, failure):
    sources = [SuppliedSource(valid_judgment(), error=RuntimeError("offline failure")
                              if failure == "source" else None) for _ in range(2)]
    adapter_inputs = []

    def assessment(state):
        adapter_inputs.append(state.assessment)
        if failure == "adapter":
            raise ValueError("cannot assess")
        if failure == "nontext":
            return 42
        if failure == "bytes":
            return b"assessment"
        return state.assessment

    events = paired_events(checked(tmp_path, spec(), *(
        {"judge": JudgmentBinding(source, assessment)} for source in sources)))
    assert len(events) == 1
    assert events[0].terminal == "FAILED_VALIDATION"
    assert events[0].detail["used_steps"] == 1
    assert events[0].detail["judgment"] is None
    assert adapter_inputs == [State().assessment, State().assessment]
    assert [source.inputs for source in sources] == (
        [[State().assessment], [State().assessment]] if failure == "source" else [[], []])


def test_valid_but_undeclared_choice_is_not_routed(tmp_path):
    authored = spec().model_copy(update={
        "nodes": (JudgmentNode(id="judge", options=("payment_follow_up", "not_a_fit")),),
        "edges": spec().edges[1:],
    })
    events = paired_events(checked(tmp_path, authored, judgments(StubSource()), judgments(StubSource())))
    assert len(events) == 1
    assert events[0].terminal == "FAILED_VALIDATION"
    assert events[0].transition is None
    assert events[0].detail["judgment"]["intervention"] == "review_follow_up"


@pytest.mark.parametrize("budget", [1, 2, 3])
def test_short_and_exact_budget_reserve_before_judgment_and_stop_at_terminal(tmp_path, budget):
    authored = with_later_work(spec(budget)).model_copy(update={"entry": "prepare"})
    authored = authored.model_copy(update={
        "nodes": (TransformNode(id="prepare", operation="prepare"),) + authored.nodes,
        "edges": (Route(source="prepare", outcome="done", target="judge"),) + authored.edges,
    })
    sources = [SuppliedSource(valid_judgment()), SuppliedSource(valid_judgment())]
    adapter_inputs, prepared = [], []

    def assessment(state):
        adapter_inputs.append(state.assessment)
        return state.assessment

    def prepare(state):
        prepared.append(state)
        return TransformResult(state, "done")

    def forbidden(state):
        pytest.fail("terminal routing must stop later work")

    events = paired_events(checked(tmp_path, authored, *(
        {"judge": JudgmentBinding(source, assessment)} for source in sources),
        bindings={"prepare": prepare, "later": forbidden}))
    assert len(prepared) == 2
    assert [event.node for event in events] == ["prepare", "judge"]
    assert [event.seq for event in events] == [0, 1]
    assert [event.detail["used_steps"] for event in events] == ([1, 1] if budget == 1 else [1, 2])
    assert events[-1].terminal == ("FAILED_BUDGET" if budget == 1 else "REVIEW")
    assert adapter_inputs == ([] if budget == 1 else [State().assessment] * 2)
    assert [source.inputs for source in sources] == ([[], []] if budget == 1 else [[State().assessment]] * 2)


class NestedState(BaseModel):
    model_config = ConfigDict(frozen=True)
    assessment: str = "business assessment"
    notes: dict[str, list[str]]


@pytest.mark.parametrize("driver", ["reference", "graph"])
def test_judgment_adapter_cannot_mutate_retained_nested_state(tmp_path, driver):
    initial = NestedState(notes={"items": ["original"]})
    retained = []

    def assessment(state):
        retained.append(state)
        state.notes["items"].append("adapter mutation")
        return state.assessment

    bound = {"judge": JudgmentBinding(StubSource(), assessment)}
    if driver == "reference":
        executable = compile_reference(spec(), state_type=NestedState, bindings={}, judgments=bound).plan
    else:
        executable = generate_graph(spec(), state_type=NestedState, bindings={}, judgments=bound).candidate
    assert executable is not None
    log = RunLog(tmp_path / "run.jsonl")
    result = executable.run(initial, run_id="nested", log=log)
    assert result.terminal == "REVIEW"
    assert result.state.notes == initial.notes == {"items": ["original"]}
    retained[0].notes["items"].append("after run")
    assert result.state.notes == initial.notes == {"items": ["original"]}
    result.state.notes["items"].append("caller result mutation")
    assert initial.notes == {"items": ["original"]}
    assert log.read()[-1].detail["judgment"]["intervention"] == "review_follow_up"


@pytest.mark.parametrize("driver", ["reference", "graph"])
def test_real_audit_write_failure_stops_before_later_work(tmp_path, driver):
    authored = with_later_work(spec(2))
    log = RunLog(tmp_path / "run.jsonl")
    source = SuppliedSource(
        StubSource(Intervention.PAYMENT_FOLLOW_UP).judge("fixture"),
        effect=lambda: log.path.mkdir(),
    )

    def forbidden(state):
        pytest.fail("work ran after judgment evidence failed to persist")

    kwargs = dict(state_type=State, bindings={"later": forbidden}, judgments=judgments(source))
    executable = (compile_reference(authored, **kwargs).plan if driver == "reference"
                  else generate_graph(authored, **kwargs).candidate)
    assert executable is not None
    with pytest.raises(AuditError):
        executable.run(State(), run_id="audit", log=log)
    assert source.inputs == [State().assessment]
    assert log.path.is_dir()
    assert log.read() == []


@pytest.mark.parametrize("phase", ["reference", "candidate"])
def test_check_reports_incomplete_and_stops_after_real_audit_failure(tmp_path, phase):
    authored = with_later_work(spec(2))
    destination = tmp_path / "evidence"
    calls = []

    def break_evidence_directory():
        # Replace the actual fresh evidence directory with a file, rather than
        # mocking persistence or relying on permissions (which root can bypass).
        root, = destination.iterdir()
        root.rename(tmp_path / "preserved-evidence")
        root.write_text("not a directory")

    choice = StubSource(Intervention.PAYMENT_FOLLOW_UP).judge("fixture")
    reference = SuppliedSource(choice, effect=break_evidence_directory if phase == "reference" else None)
    candidate = SuppliedSource(choice, effect=break_evidence_directory if phase == "candidate" else None)

    def later(state):
        calls.append(state.assessment)
        return TransformResult(state, "done")

    generated = generate_graph(authored, state_type=State, bindings={"later": later},
                               judgments=judgments(candidate))
    assert generated.candidate is not None
    report = check_conformance(
        authored, generated.candidate, state_type=State, bindings={"later": later},
        judgments=judgments(reference), cases={"first": State(), "never": State()},
        evidence_dir=destination,
    )
    assert not report.passed
    assert report.attempted == ("first",)
    assert report.completed == ()
    assert [(finding.code, finding.path) for finding in report.findings] == [
        ("incomplete", ("cases", "first", phase))]
    assert len(report.evidence) == 1
    assert reference.inputs == [State().assessment]
    assert candidate.inputs == ([] if phase == "reference" else [State().assessment])
    assert calls == ([] if phase == "reference" else [State().assessment])


def test_real_recorded_source_rejects_assessment_mismatch(tmp_path):
    recording = tmp_path / "recording.json"
    recording.write_text(json.dumps({
        "assessment_sha": hashlib.sha256(b"different assessment").hexdigest(),
        "intervention": "review_follow_up", "confidence": 0.99, "review_gap": 0.97,
    }))
    assert RecordedSource(recording).judge("different assessment").intervention == Intervention.REVIEW_FOLLOW_UP
    sources = [RecordedSource(recording), RecordedSource(recording)]
    events = paired_events(checked(tmp_path / "evidence", spec(), *(judgments(s) for s in sources)))
    assert len(events) == 1
    assert events[0].terminal == "FAILED_VALIDATION"
    assert events[0].detail["used_steps"] == 1
    assert events[0].detail["judgment"] is None
