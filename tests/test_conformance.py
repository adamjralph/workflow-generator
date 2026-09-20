"""Approved seam: independent candidate + spec + typed cases -> report and logs."""
from pathlib import Path

import pytest

from pydantic import BaseModel, ConfigDict

from agent_lab.conformance import check_conformance
from agent_lab.generation import generate_graph
from agent_lab.reference import TransformResult
from agent_lab.runlog import RunLog
from agent_lab.spec import DecisionNode, Route, TransformNode, WorkflowSpec


class State(BaseModel):
    model_config = ConfigDict(frozen=True)
    value: int


def example(budget=2):
    return WorkflowSpec(
        entry="prepare / arbitrary", budget=budget,
        terminals=("YES", "NO", "FAILED_VALIDATION", "FAILED_BUDGET"),
        nodes=(TransformNode(id="prepare / arbitrary", operation="increment"),
               DecisionNode(id="choose", value="sign", cases=("positive", "negative"))),
        edges=(Route(source="prepare / arbitrary", outcome="done", target="choose"),
               Route(source="choose", outcome="positive", target="YES"),
               Route(source="choose", outcome="negative", target="NO")),
    )


def bindings():
    return {"increment": lambda s: TransformResult(State(value=s.value + 1), "done"),
            "sign": lambda s: "positive" if s.value > 0 else "negative"}


def candidate(spec=None, bound=None):
    result = generate_graph(spec or example(), state_type=State, bindings=bound or bindings())
    assert result.candidate is not None
    return result.candidate


def test_branching_check_retains_same_id_separate_exact_evidence(tmp_path):
    report = check_conformance(example(), candidate(), state_type=State,
                               bindings=bindings(), cases={"../positive": State(value=0),
                                                          "negative": State(value=-2)},
                               evidence_dir=tmp_path)
    assert report.passed
    assert report.attempted == report.completed == ("../positive", "negative")
    assert not report.findings
    for evidence, terminal in zip(report.evidence, ("YES", "NO")):
        plain, graph = RunLog(evidence.reference_log), RunLog(evidence.candidate_log)
        assert evidence.reference_log != evidence.candidate_log
        assert evidence.reference_log.is_relative_to(tmp_path)
        assert plain.read_bytes() == graph.read_bytes()
        assert plain.digest() == graph.digest()
        assert plain.read()[-1].terminal == terminal
        assert [event.seq for event in plain.read()] == [0, 1]
        assert {event.run_id for event in plain.read() + graph.read()} == {evidence.run_id}


def test_independently_altered_binding_cannot_pass(tmp_path):
    altered = bindings() | {"increment": lambda s: TransformResult(State(value=-10), "done")}
    report = check_conformance(example(), candidate(bound=altered), state_type=State,
                               bindings=bindings(), cases={"case": State(value=0)},
                               evidence_dir=tmp_path)
    assert not report.passed
    assert report.completed == ("case",)
    assert {finding.path for finding in report.findings} >= {
        ("cases", "case", "state"), ("cases", "case", "terminal"),
        ("cases", "case", "trace"), ("cases", "case", "bytes"),
        ("cases", "case", "digest")}


@pytest.mark.parametrize("change, location", [
    ({"entry": "choose"}, ("entry",)),
    ({"budget": 3}, ("budget",)),
    ({"terminals": (*example().terminals, "UNUSED")}, ("terminals",)),
    ({"nodes": (TransformNode(id="prepare / arbitrary", operation="other"),
                 example().nodes[1])}, ("nodes", "prepare / arbitrary")),
    ({"nodes": (DecisionNode(id="prepare / arbitrary", value="sign", cases=("done",)),
                 example().nodes[1])}, ("nodes", "prepare / arbitrary")),
    ({"nodes": (example().nodes[0], DecisionNode(id="choose", value="other", cases=("positive", "negative")))},
     ("nodes", "choose")),
    ({"nodes": (example().nodes[0], DecisionNode(id="choose", value="sign", cases=("positive", "negative", "third"))),
      "edges": (*example().edges, Route(source="choose", outcome="third", target="YES"))},
     ("nodes", "choose")),
    ({"edges": (example().edges[0],
                 Route(source="choose", outcome="positive", target="NO"),
                 example().edges[2])}, ("edges", "choose", "positive")),
    ({"nodes": (*example().nodes, TransformNode(id="unreachable", operation="other")),
      "edges": (*example().edges, Route(source="unreachable", outcome="done", target="YES"))},
     ("nodes", "unreachable")),
])
def test_structural_changes_prevent_all_bindings(tmp_path, change, location):
    calls = []
    bound = {key: lambda s: calls.append(s) for key in ("increment", "sign", "other")}
    altered = example().model_copy(update=change)
    report = check_conformance(example(), candidate(altered, bound), state_type=State,
                               bindings=bound, cases={"case": State(value=0)}, evidence_dir=tmp_path)
    assert not report.passed
    assert report.attempted == ()
    assert calls == []
    assert any(f.code == "structural_mismatch" and f.path == location for f in report.findings)


def test_declaration_order_has_no_execution_meaning(tmp_path):
    spec = example()
    reordered_nodes = (spec.nodes[0], spec.nodes[1].model_copy(update={"cases": ("negative", "positive")}))
    reordered = spec.model_copy(update={"nodes": tuple(reversed(reordered_nodes)),
        "edges": tuple(reversed(spec.edges)), "terminals": tuple(reversed(spec.terminals))})
    report = check_conformance(spec, candidate(reordered), state_type=State, bindings=bindings(),
                               cases={"case": State(value=0)}, evidence_dir=tmp_path)
    assert report.passed


@pytest.mark.parametrize("mode", ["object", "subclass", "mutation"])
def test_unsupported_or_mutated_candidate_is_a_located_finding(tmp_path, mode):
    from agent_lab.generation import GraphCandidate
    class Subclass(GraphCandidate):
        pass
    supplied = candidate()
    if mode == "object":
        supplied = object()
    elif mode == "subclass":
        supplied = object.__new__(Subclass)
    else:
        object.__setattr__(supplied, "_budget", 99)
    report = check_conformance(example(), supplied, state_type=State, bindings=bindings(),
                               cases={"case": State(value=0)}, evidence_dir=tmp_path)
    assert report.attempted == ()
    assert report.findings[0].code == "unsupported_candidate"
    assert report.findings[0].path == ("candidate",)


@pytest.mark.parametrize("driver", ["reference", "candidate"])
def test_real_audit_write_failure_stops_all_later_work(tmp_path, driver):
    calls = []
    def break_audit(state):
        calls.append("break")
        root, = tmp_path.glob("check-*")
        (root / f"0-{driver}.jsonl").mkdir()
        return TransformResult(state, "done")
    def later(state):
        calls.append("later")
        return "positive"
    broken = {"increment": break_audit, "sign": later}
    report = check_conformance(example(), candidate(bound=broken if driver == "candidate" else bindings()),
        state_type=State, bindings=broken if driver == "reference" else bindings(),
        cases={"first": State(value=0), "never": State(value=1)}, evidence_dir=tmp_path)
    assert not report.passed
    assert calls == ["break"]
    assert report.attempted == ("first",)
    assert report.completed == ()
    assert len(report.evidence) == 1
    assert report.findings[-1].code == "incomplete"
    assert report.findings[-1].path == ("cases", "first", driver)


def test_evidence_creation_failure_is_incomplete_without_execution(tmp_path):
    file = tmp_path / "not-a-directory"
    file.write_text("occupied")
    report = check_conformance(example(), candidate(), state_type=State, bindings=bindings(),
        cases={"first": State(value=0)}, evidence_dir=file)
    assert not report.passed
    assert report.attempted == report.completed == ()
    assert report.findings[0].code == "incomplete"
    assert report.findings[0].path == ("evidence_dir",)


@pytest.mark.parametrize("root_kind", ["default", "configured", "source", "explicit", "symlink"])
def test_evidence_must_be_outside_protected_roots(tmp_path, monkeypatch, root_kind):
    import sys
    from types import SimpleNamespace
    protected = tmp_path / "protected"
    protected.mkdir()
    extra = {}
    if root_kind == "default":
        monkeypatch.setenv("HOME", str(tmp_path))
        destination = tmp_path / ".hermes" / "evidence"
    elif root_kind == "source":
        monkeypatch.setitem(sys.modules, "hermes_cli", SimpleNamespace(__file__=str(protected / "hermes_cli" / "__init__.py")))
        destination = protected / "evidence"
    elif root_kind == "explicit":
        extra = {"protected_roots": (protected,)}
        destination = protected / "evidence"
    else:
        monkeypatch.setenv("HERMES_HOME", str(protected))
        destination = protected / "evidence"
        if root_kind == "symlink":
            destination = tmp_path / "link"
            destination.symlink_to(protected, target_is_directory=True)
    with pytest.raises(ValueError, match="outside Hermes"):
        check_conformance(example(), candidate(), state_type=State, bindings=bindings(),
            cases={"first": State(value=0)}, evidence_dir=destination, **extra)
    assert list(protected.iterdir()) == []


@pytest.mark.parametrize("mode, terminal, steps", [
    ("exception", "FAILED_VALIDATION", 1), ("state", "FAILED_VALIDATION", 1),
    ("label", "FAILED_VALIDATION", 2), ("short", "FAILED_BUDGET", 1),
    ("exact", "YES", 2), ("terminal", "YES", 1),
])
def test_recorded_failure_and_budget_outcomes_are_comparable(tmp_path, mode, terminal, steps):
    spec, bound = example(1 if mode == "short" else 2), bindings()
    def fail(state):
        raise RuntimeError("trusted binding failed")
    if mode == "exception":
        bound["increment"] = fail
    elif mode == "state":
        bound["increment"] = lambda s: TransformResult(State.model_construct(value="bad"), "done")
    elif mode == "label":
        bound["sign"] = lambda s: "undeclared"
    elif mode == "terminal":
        spec = spec.model_copy(update={"edges": (Route(source=spec.entry, outcome="done", target="YES"), *spec.edges[1:])})
        bound["sign"] = fail
    report = check_conformance(spec, candidate(spec, bound), state_type=State, bindings=bound,
        cases={"case": State(value=0)}, evidence_dir=tmp_path)
    assert report.passed
    events = RunLog(report.evidence[0].candidate_log).read()
    assert events[-1].terminal == terminal
    assert events[-1].detail["used_steps"] == steps


def test_repeated_checks_use_fresh_subdirectories_but_identical_bytes(tmp_path):
    supplied = candidate()
    reports = [check_conformance(example(), supplied, state_type=State, bindings=bindings(),
        cases={"same": State(value=0)}, evidence_dir=tmp_path / "new") for _ in range(2)]
    assert all(r.passed for r in reports)
    first, second = (r.evidence[0].candidate_log for r in reports)
    assert first != second
    assert RunLog(first).read_bytes() == RunLog(second).read_bytes()


@pytest.mark.parametrize("mode, code", [("invalid", "invalid_declaration"),
    ("unbound", "unbound_reference"), ("safety", "missing_safety_terminal"),
    ("state", "invalid_state_type"), ("unreachable", "unsupported_node")])
def test_reference_compilation_failure_cannot_pass_or_invoke(tmp_path, mode, code):
    from agent_lab.spec import JudgmentNode
    spec, state_type, bound = example(), State, bindings()
    if mode == "invalid":
        spec = spec.model_copy(update={"budget": True})
    elif mode == "unbound":
        bound = {}
    elif mode == "safety":
        spec = spec.model_copy(update={"terminals": ("YES", "NO")})
    elif mode == "state":
        state_type = BaseModel
    else:
        spec = spec.model_copy(update={"nodes": (*spec.nodes, JudgmentNode(id="unused", options=("yes",))),
            "edges": (*spec.edges, Route(source="unused", outcome="yes", target="YES"))})
    calls = []
    bound = {key: lambda s: calls.append(s) for key in bound}
    report = check_conformance(spec, candidate(), state_type=state_type, bindings=bound,
        cases={"case": State(value=0)}, evidence_dir=tmp_path)
    assert not report.passed
    assert report.attempted == report.evidence == ()
    assert any(f.code == code and f.path for f in report.findings)
    assert not calls


def test_invalid_initial_state_retains_value_error_policy(tmp_path):
    with pytest.raises(ValueError, match="Invalid initial state"):
        check_conformance(example(), candidate(), state_type=State, bindings=bindings(),
            cases={"bad": State.model_construct(value="bad")}, evidence_dir=tmp_path)


def test_missing_persisted_reference_is_incomplete_and_stops_cases(tmp_path):
    def remove_reference(state):
        for path in tmp_path.glob("check-*/0-reference.jsonl"):
            path.unlink()
        return "positive"
    report = check_conformance(example(), candidate(bound=bindings() | {"sign": remove_reference}),
        state_type=State, bindings=bindings(), cases={"first": State(value=0), "never": State(value=1)},
        evidence_dir=tmp_path)
    assert report.attempted == ("first",)
    assert report.completed == ()
    assert report.findings[-1].path == ("cases", "first", "comparison")
    assert report.findings[-1].code == "incomplete"


def test_final_state_comparison_does_not_coerce_equal_python_values(tmp_path):
    class UnionState(BaseModel):
        model_config = ConfigDict(frozen=True)
        value: int | bool
    reference = {"increment": lambda s: TransformResult(UnionState(value=1), "done"),
                 "sign": lambda s: "positive"}
    altered = reference | {"increment": lambda s: TransformResult(UnionState(value=True), "done")}
    generated = generate_graph(example(), state_type=UnionState, bindings=altered)
    report = check_conformance(example(), generated.candidate, state_type=UnionState, bindings=reference,
        cases={"case": UnionState(value=0)}, evidence_dir=tmp_path)
    assert not report.passed
    assert any(f.path == ("cases", "case", "state") for f in report.findings)


@pytest.mark.parametrize("name", ["", "  ", 1])
def test_invalid_case_names_raise_value_error(tmp_path, name):
    with pytest.raises(ValueError, match="Case names"):
        check_conformance(example(), candidate(), state_type=State, bindings=bindings(),
            cases={name: State(value=0)}, evidence_dir=tmp_path)


def test_replaced_public_inspection_method_cannot_claim_structure(tmp_path):
    from agent_lab.generation import GraphCandidate
    supplied = candidate()
    original = GraphCandidate.inspect_structure
    try:
        GraphCandidate.inspect_structure = lambda self: example()
        report = check_conformance(example(), supplied, state_type=State, bindings=bindings(),
            cases={"case": State(value=0)}, evidence_dir=tmp_path)
    finally:
        GraphCandidate.inspect_structure = original
    assert report.findings[0].code == "unsupported_candidate"
    assert not report.attempted


def test_freshness_violation_is_not_disguised_as_a_mismatch(tmp_path):
    def occupy_candidate_log(state):
        root, = tmp_path.glob("check-*")
        candidate().run(state, run_id="case-0", log=RunLog(root / "0-candidate.jsonl"))
        return TransformResult(state, "done")
    with pytest.raises(ValueError, match="already recorded"):
        check_conformance(example(), candidate(), state_type=State,
            bindings=bindings() | {"increment": occupy_candidate_log},
            cases={"case": State(value=0)}, evidence_dir=tmp_path)


def test_unexpected_programming_error_is_not_an_incomplete_report(tmp_path):
    class BrokenCases(dict):
        def items(self):
            raise RuntimeError("programming error")
    with pytest.raises(RuntimeError, match="programming error"):
        check_conformance(example(), candidate(), state_type=State, bindings=bindings(),
            cases=BrokenCases(), evidence_dir=tmp_path)


def test_empty_cases_never_pass(tmp_path):
    report = check_conformance(example(), candidate(), state_type=State,
                               bindings=bindings(), cases={}, evidence_dir=tmp_path)
    assert not report.passed
    assert report.findings[0].code == "empty_cases"
