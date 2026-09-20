"""Public designer seams, with expectations authored independently of either driver."""
from copy import deepcopy
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from agent_lab.designer import author_design, check_design, generate_candidate
from agent_lab.generation import generate_graph
from agent_lab.reference import TransformResult
from agent_lab.runlog import RunLog


def receive(done="ACCEPTED", identity="start"):
    return {"id": identity, "operation": "receive", "done": done}


def adjust(identity, amount, done):
    return {"id": identity, "operation": "adjust", "adjustment": amount, "done": done}


def compare(identity="choose", threshold=50, below="ACCEPTED", upper="REVIEW"):
    return {"id": identity, "operation": "compare", "threshold": threshold,
            "below": below, "at_or_above": upper}


ANSWERS = {"nodes": [receive("choose"), compare()]}
LINEAR = {"nodes": [receive("up"), adjust("up", 10, "down"), adjust("down", -10, "REVIEW")]}
BRANCH = {"nodes": [receive("up"), adjust("up", 10, "choose"),
                     compare(below="down", upper="ACCEPTED"), adjust("down", -10, "REVIEW")]}
BOUNDED = {"nodes": [receive("first"), compare("first", 10, "REVIEW", "second"),
                      compare("second", 50, "ACCEPTED", "REVIEW")]}
RECONVERGENT = {"nodes": [receive("first"), compare("first", 50, "up", "down"),
                         adjust("up", 10, "second"), adjust("down", -10, "second"),
                         compare("second", 50, "REVIEW", "ACCEPTED")]}
INFEASIBLE = {"nodes": [receive("first"), compare("first", 50, "second", "ACCEPTED"),
                        compare("second", 100, "REVIEW", "ACCEPTED")]}


INFEASIBLE_LONG = {"nodes": [receive("first"), compare("first", 50, "second", "ACCEPTED"),
                             compare("second", 100, "REVIEW", "up"),
                             adjust("up", 10, "down"), adjust("down", -10, "ACCEPTED")]}


# Route fixtures are literal node/outcome/target triples, not walks over the spec.
START = ("start", "done", "first")
LOW = (START, ("first", "below", "REVIEW"))
MIDDLE = (START, ("first", "at_or_above", "second"), ("second", "below", "ACCEPTED"))
HIGH = (START, ("first", "at_or_above", "second"), ("second", "at_or_above", "REVIEW"))
UP_LOW = (START, ("first", "below", "up"), ("up", "done", "second"), ("second", "below", "REVIEW"))
UP_HIGH = (START, ("first", "below", "up"), ("up", "done", "second"), ("second", "at_or_above", "ACCEPTED"))
DOWN_LOW = (START, ("first", "at_or_above", "down"), ("down", "done", "second"), ("second", "below", "REVIEW"))
DOWN_HIGH = (START, ("first", "at_or_above", "down"), ("down", "done", "second"), ("second", "at_or_above", "ACCEPTED"))
BRANCH_LOW = (("start", "done", "up"), ("up", "done", "choose"), ("choose", "below", "down"), ("down", "done", "REVIEW"))
BRANCH_HIGH = (("start", "done", "up"), ("up", "done", "choose"), ("choose", "at_or_above", "ACCEPTED"))
IMPOSSIBLE_LOW = (START, ("first", "below", "second"), ("second", "below", "REVIEW"))
IMPOSSIBLE_HIGH = (START, ("first", "at_or_above", "ACCEPTED"))


@pytest.mark.parametrize("raw,budget,rows", [
    pytest.param({"nodes": [receive()]}, 1, [
        (0, "ACCEPTED", 0, (("start", "done", "ACCEPTED"),)),
    ], id="receive-only"),
    pytest.param(LINEAR, 3, [
        (0, "REVIEW", 0, (("start", "done", "up"), ("up", "done", "down"), ("down", "done", "REVIEW"))),
    ], id="linear-adjustments"),
    pytest.param(BRANCH, 4, [
        (38, "REVIEW", 38, BRANCH_LOW), (39, "REVIEW", 39, BRANCH_LOW),
        (40, "ACCEPTED", 50, BRANCH_HIGH), (41, "ACCEPTED", 51, BRANCH_HIGH),
    ], id="adjust-before-and-after-decision-equality"),
    pytest.param(BOUNDED, 3, [
        (8, "REVIEW", 8, LOW), (9, "REVIEW", 9, LOW),
        (10, "ACCEPTED", 10, MIDDLE), (29, "ACCEPTED", 29, MIDDLE), (49, "ACCEPTED", 49, MIDDLE),
        (50, "REVIEW", 50, HIGH), (51, "REVIEW", 51, HIGH),
    ], id="two-decisions-bounded-midpoint"),
    pytest.param(RECONVERGENT, 4, [
        (38, "REVIEW", 48, UP_LOW), (39, "REVIEW", 49, UP_LOW),
        (40, "ACCEPTED", 50, UP_HIGH), (44, "ACCEPTED", 54, UP_HIGH), (49, "ACCEPTED", 59, UP_HIGH),
        (50, "REVIEW", 40, DOWN_LOW), (54, "REVIEW", 44, DOWN_LOW), (59, "REVIEW", 49, DOWN_LOW),
        (60, "ACCEPTED", 50, DOWN_HIGH), (61, "ACCEPTED", 51, DOWN_HIGH),
    ], id="reconvergence-keeps-path-specific-offsets"),
    pytest.param(INFEASIBLE, 3, [
        (48, "REVIEW", 48, IMPOSSIBLE_LOW), (49, "REVIEW", 49, IMPOSSIBLE_LOW),
        (50, "ACCEPTED", 50, IMPOSSIBLE_HIGH), (51, "ACCEPTED", 51, IMPOSSIBLE_HIGH),
    ], id="infeasible-route-not-executed"),
    pytest.param(INFEASIBLE_LONG, 3, [
        (48, "REVIEW", 48, IMPOSSIBLE_LOW), (49, "REVIEW", 49, IMPOSSIBLE_LOW),
        (50, "ACCEPTED", 50, IMPOSSIBLE_HIGH), (51, "ACCEPTED", 51, IMPOSSIBLE_HIGH),
    ], id="infeasible-long-path-does-not-inflate-budget"),
])
def test_authored_cases_execute_independent_routes_and_scores(tmp_path, raw, budget, rows):
    design = author_design(raw)
    assert design.spec == author_design(deepcopy(raw)).spec
    assert design.spec.entry == "start"
    assert design.spec.budget == design.view()["budget"] == budget
    assert list(design.cases) == [f"score_{score}" for score, *_ in rows]
    candidate = generate_candidate(design)
    for score, terminal, final_score, routes in rows:
        log = RunLog(tmp_path / f"direct-{score}.jsonl")
        result = candidate.run(design.state_type(score=score), run_id=f"input-{score}", log=log)
        assert (result.terminal, result.state.score, result.used_steps) == (terminal, final_score, len(routes))
        assert_routes(log, routes, terminal, budget)
    report = check_design(raw, evidence_dir=tmp_path / "checks")
    assert report["passed"] is True
    assert report["findings"] == []
    assert report["cases"] == report["completed_cases"] == [f"score_{row[0]}" for row in rows]
    assert [item["name"] for item in report["evidence"]] == report["cases"]
    for item, (_, terminal, _, routes) in zip(report["evidence"], rows, strict=True):
        # Both real persisted logs must satisfy the independent fixture; equality
        # between two implementations alone would not prove the intended routes.
        for key in ("reference_log", "candidate_log"):
            assert Path(item[key]).is_relative_to(tmp_path / "checks")
            assert_routes(RunLog(Path(item[key])), routes, terminal, budget)
        assert Path(item["reference_log"]).read_bytes() == Path(item["candidate_log"]).read_bytes()


def assert_routes(log, routes, terminal, budget):
    events = log.read()
    assert tuple((event.node, event.transition, event.detail["target"]) for event in events) == routes
    assert [event.seq for event in events] == list(range(len(routes)))
    assert [event.detail["used_steps"] for event in events] == list(range(1, len(routes) + 1))
    assert all(event.detail["max_steps"] == budget and event.detail["failure"] is None for event in events)
    assert [event.terminal for event in events] == [None] * (len(routes) - 1) + [terminal]


@pytest.mark.parametrize("raw,scores", [
    ({"nodes": [receive()]}, [0]),
    (ANSWERS, [48, 49, 50, 51]),
    (BRANCH, [38, 39, 40, 41]),
    (BOUNDED, [8, 9, 10, 29, 49, 50, 51]),
    (RECONVERGENT, [38, 39, 40, 44, 49, 50, 54, 59, 60, 61]),
    (INFEASIBLE, [48, 49, 50, 51]),
    ({"nodes": [receive("up"), adjust("up", 10, "choose"), compare(threshold=10)]}, [-2, -1, 0, 1]),
    ({"nodes": [receive("first"), compare("first", 50, "second", "second"), compare("second", 50)]}, [48, 49, 50, 51]),
])
def test_case_interval_fixtures_are_deterministic_bounded_and_deduplicated(raw, scores):
    design = author_design(raw)
    expected = [{"name": f"score_{score}", "score": score} for score in scores]
    assert design.view()["cases"] == expected
    assert [(name, state.score) for name, state in design.cases.items()] == [(row["name"], row["score"]) for row in expected]
    assert len(design.cases) <= 12
    assert "not exhaustive" in design.view()["scope"]
    assert author_design(deepcopy(raw)).view() == design.view()


def test_infeasible_routes_are_reported_without_suppressing_valid_design():
    view = author_design(INFEASIBLE).view()
    assert view["infeasible_routes"] == [[START, ("first", "below", "second"), ("second", "at_or_above", "ACCEPTED")]]
    assert "2 feasible / 3 syntactic paths" in view["scope"]


@pytest.mark.parametrize("threshold", [10, 50, 100])
@pytest.mark.parametrize("below,upper", [("ACCEPTED", "REVIEW"), ("REVIEW", "ACCEPTED"),
                                         ("ACCEPTED", "ACCEPTED"), ("REVIEW", "REVIEW")])
def test_catalog_thresholds_and_terminal_choices(tmp_path, threshold, below, upper):
    raw = {"nodes": [receive("choose"), compare(threshold=threshold, below=below, upper=upper)]}
    result = check_design(raw, evidence_dir=tmp_path)
    assert result["passed"]
    assert result["cases"] == [f"score_{value}" for value in (threshold - 2, threshold - 1, threshold, threshold + 1)]
    for item, outcome, terminal in zip(result["evidence"], ["below", "below", "at_or_above", "at_or_above"], [below, below, upper, upper], strict=True):
        assert_routes(RunLog(Path(item["candidate_log"])),
                      (("start", "done", "choose"), ("choose", outcome, terminal)), terminal, 2)


def test_structural_edits_view_budget_and_route_repair(tmp_path):
    original = author_design({"nodes": [receive()]})
    raw = {"nodes": [receive("extra"), adjust("extra", 10, "ACCEPTED")]}
    expanded = author_design(raw)
    assert expanded.spec != original.spec
    assert expanded.view()["nodes"] == [
        {"id": "start", "kind": "transform", "label": "Receive request"},
        {"id": "extra", "kind": "transform", "label": "Score +10"},
    ]
    assert expanded.view()["edges"] == [
        {"source": "start", "outcome": "done", "target": "extra"},
        {"source": "extra", "outcome": "done", "target": "ACCEPTED"},
    ]
    assert expanded.spec.budget == 2
    raw["nodes"].pop()
    with pytest.raises(ValueError, match="destination"):
        check_design(raw, evidence_dir=tmp_path)
    assert raw["nodes"][0]["done"] == "extra"
    assert not list(tmp_path.iterdir())
    raw["nodes"][0]["done"] = "REVIEW"
    repaired = author_design(raw)
    assert repaired.spec.budget == repaired.view()["budget"] == 1
    assert repaired.spec != original.spec
    assert check_design(raw, evidence_dir=tmp_path)["passed"]


def test_six_nodes_are_allowed_and_entry_is_not_list_order(tmp_path):
    raw = {"nodes": [adjust("a", 10, "b"), adjust("b", 10, "c"), receive("a"),
                     adjust("c", 10, "d"), adjust("d", 10, "e"), adjust("e", 10, "ACCEPTED")]}
    design = author_design(raw)
    assert design.spec.entry == "start"
    assert design.spec.budget == 6
    result = generate_candidate(design).run(design.state_type(score=0), run_id="six", log=RunLog(tmp_path / "six.jsonl"))
    assert (result.terminal, result.state.score, result.used_steps) == ("ACCEPTED", 50, 6)


@pytest.mark.parametrize("score", [True, False, "10", 10.0, 1.5, None])
def test_score_type_is_strict(score):
    with pytest.raises(ValueError):
        author_design(ANSWERS).state_type(score=score)


def test_score_is_frozen_and_has_no_extra_fields():
    state_type = author_design(ANSWERS).state_type
    state = state_type(score=-10)
    with pytest.raises(ValueError):
        state.score = 0
    with pytest.raises(ValueError):
        state_type(score=0, code="exec")


def invalid_answers():
    for raw in (None, [], {}, {"nodes": []}, {"nodes": "start"},
                {"threshold": 50, "below": "ACCEPTED", "at_or_above": "REVIEW"}):
        yield pytest.param(raw, id=f"envelope-{raw}")
    for field in ("budget", "entry", "bindings", "code", "evidence_dir", "candidate_factory"):
        yield pytest.param({**ANSWERS, field: "injected"}, id=f"extra-{field}")
    for field, values in (("threshold", [True, False, "50", 50.0, 1.5, None, 0, 51, -10]),
                          ("operation", ["exec", "loop", "judgment", "gate", "fork", None, 1]),
                          ("id", ["", "1bad", "bad id", "a" * 65, True, "ACCEPTED", "FAILED_BUDGET"]),
                          ("below", [None, True, 1, "", "missing", "FAILED_VALIDATION", "FAILED_BUDGET"])):
        for value in values:
            raw = deepcopy(ANSWERS)
            raw["nodes"][1][field] = value
            yield pytest.param(raw, id=f"{field}-{value}")
    for value in (True, False, "10", 10.0, 1.5, None, 0, 20, -20):
        yield pytest.param({"nodes": [receive("a"), adjust("a", value, "ACCEPTED")]}, id=f"adjustment-{value}")
    for index, field in ((0, "done"), (0, "id"), (0, "operation"), (1, "below"), (1, "at_or_above"), (1, "threshold")):
        raw = deepcopy(ANSWERS)
        del raw["nodes"][index][field]
        yield pytest.param(raw, id=f"missing-{index}-{field}")
    for index, field in ((0, "threshold"), (0, "adjustment"), (1, "done"), (1, "code")):
        raw = deepcopy(ANSWERS)
        raw["nodes"][index][field] = 10
        yield pytest.param(raw, id=f"node-extra-{index}-{field}")
    graphs = {
        "no-receive": [adjust("a", 10, "ACCEPTED")],
        "two-receives": [receive("other"), receive(identity="other")],
        "duplicate-id": [receive("start"), adjust("start", 10, "ACCEPTED")],
        "self-cycle": [receive("start")],
        "cycle": [receive("a"), adjust("a", 10, "start")],
        "unreachable": [receive(), adjust("unused", 10, "REVIEW")],
        "infeasible-cycle": [receive("first"), compare("first", 50, "second", "ACCEPTED"), compare("second", 100, "REVIEW", "second")],
        "three-decisions": [receive("a"), compare("a", 10, "b", "ACCEPTED"), compare("b", 50, "c", "ACCEPTED"), compare("c")],
        "seven-nodes": [receive("a"), *[adjust(a, 10, b) for a, b in zip("abcdef", ["b", "c", "d", "e", "f", "ACCEPTED"], strict=True)]],
        "missing-transform-destination": [receive("gone")],
        "missing-adjustment": [receive("a"), {"id": "a", "operation": "adjust", "done": "ACCEPTED"}],
    }
    for name, nodes in graphs.items():
        yield pytest.param({"nodes": nodes}, id=name)


@pytest.mark.parametrize("raw", list(invalid_answers()))
def test_invalid_answers_fail_before_generation_or_evidence(tmp_path, raw):
    def forbidden(design):
        pytest.fail("Invalid answers reached generation")
    with pytest.raises(ValueError):
        author_design(raw)
    with pytest.raises(ValueError):
        check_design(raw, evidence_dir=tmp_path, candidate_factory=forbidden)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("alteration", ["routes", "budget", "decision", "score"])
def test_altered_structure_or_behavior_cannot_pass(tmp_path, alteration):
    def altered(design):
        spec, bindings = design.spec, dict(design.bindings)
        if alteration == "routes":
            edges = tuple(edge.model_copy(update={"target": "REVIEW"}) if edge.source == "choose" else edge for edge in spec.edges)
            spec = spec.model_copy(update={"edges": edges})
        elif alteration == "budget":
            spec = spec.model_copy(update={"budget": spec.budget + 1})
        elif alteration == "decision":
            bindings["score_at_least_50"] = lambda state: "below"
        else:
            bindings["receive_request"] = lambda state: TransformResult(design.state_type(score=state.score + 1), "done")
        result = generate_graph(spec, state_type=design.state_type, bindings=bindings)
        assert result.candidate is not None  # Generation is not the verdict.
        return result.candidate
    result = check_design(ANSWERS, evidence_dir=tmp_path, candidate_factory=altered)
    assert result["passed"] is False
    code = "structural_mismatch" if alteration in ("routes", "budget") else "behavioral_mismatch"
    assert code in {finding["code"] for finding in result["findings"]}
    if code == "structural_mismatch":
        assert result["completed_cases"] == result["evidence"] == []
        assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("phase", ["reference", "candidate"])
def test_audit_write_failure_never_passes(tmp_path, monkeypatch, phase):
    append = RunLog.append_next
    def fail_write(self, event):
        if phase in self.path.name:
            raise OSError("audit disk unavailable")
        return append(self, event)
    monkeypatch.setattr(RunLog, "append_next", fail_write)
    result = check_design(ANSWERS, evidence_dir=tmp_path)
    assert not result["passed"]
    assert result["completed_cases"] == []
    assert result["findings"][0]["code"] == "incomplete"


def test_unwritable_evidence_location_never_passes(tmp_path):
    root = tmp_path / "file-not-directory"
    root.write_text("preserve")
    result = check_design(ANSWERS, evidence_dir=root)
    assert not result["passed"]
    assert result["completed_cases"] == result["evidence"] == []
    assert result["findings"][0]["code"] == "incomplete"
    assert root.read_text() == "preserve"


@pytest.mark.parametrize("kind", ["configured", "default", "source", "additional", "host", "symlink"])
def test_protected_roots_are_rejected_before_generation(tmp_path, monkeypatch, kind):
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("HERMES_HOME", raising=False)
    root = tmp_path / "installation"
    protected = ()
    if kind == "configured":
        monkeypatch.setenv("HERMES_HOME", str(root))
    elif kind == "default":
        root = home / ".hermes"
    elif kind == "source":
        root = Path(__file__).resolve().parents[1]
    elif kind == "additional":
        protected = (root,)
    elif kind == "host":
        monkeypatch.setitem(sys.modules, "hermes_cli", SimpleNamespace(__file__=str(root / "hermes_cli" / "__init__.py")))
    else:
        link = tmp_path / "link"
        link.symlink_to(root, target_is_directory=True)
        protected = (root,)
        root = link
    def forbidden(design):
        pytest.fail("Protected output reached generation")
    destination = root / "forbidden-test-evidence"
    with pytest.raises(ValueError, match="outside Hermes"):
        check_design(ANSWERS, evidence_dir=destination, candidate_factory=forbidden, protected_roots=protected)
    assert not destination.exists()
