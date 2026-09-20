from pathlib import Path

import pytest

from agent_lab.designer import author_design, check_design
from agent_lab.generation import generate_graph
from agent_lab.reference import compile_reference
from agent_lab.runlog import RunLog


ANSWERS = {"threshold": 50, "below": "ACCEPTED", "at_or_above": "REVIEW"}


def test_questionnaire_authors_and_executes_threshold_routes(tmp_path):
    design = author_design(ANSWERS)
    assert design.spec == author_design(ANSWERS).spec
    plan = compile_reference(design.spec, state_type=design.state_type, bindings=design.bindings).plan
    assert plan is not None
    results = [plan.run(state, run_id=name, log=RunLog(tmp_path / f"{name}.jsonl"))
               for name, state in design.cases.items()]
    assert [r.terminal for r in results] == ["ACCEPTED", "REVIEW", "REVIEW"]
    assert [r.state.score for r in results] == [49, 50, 51]
    assert [r.used_steps for r in results] == [2, 2, 2]
    view = design.view()
    assert view["cases"] == [
        {"name": "below", "score": 49, "expected_terminal": "ACCEPTED"},
        {"name": "at", "score": 50, "expected_terminal": "REVIEW"},
        {"name": "above", "score": 51, "expected_terminal": "REVIEW"},
    ]
    changed = author_design({**ANSWERS, "threshold": 100})
    assert changed.spec != design.spec
    assert changed.view() != view


def test_real_generation_check_exposes_complete_evidence(tmp_path):
    result = check_design(ANSWERS, evidence_dir=tmp_path)
    assert result["passed"]
    assert result["cases"] == result["completed_cases"] == ["below", "at", "above"]
    assert not result["findings"]
    assert len(result["evidence"]) == 3
    for case in result["evidence"]:
        reference = Path(case["reference_log"]).read_bytes()
        assert reference and reference == Path(case["candidate_log"]).read_bytes()


def test_nonconforming_candidate_cannot_pass(tmp_path):
    def altered(design):
        bindings = dict(design.bindings)
        bindings["score_at_least_50"] = lambda state: "below"
        return generate_graph(design.spec, state_type=design.state_type, bindings=bindings).candidate
    result = check_design(ANSWERS, evidence_dir=tmp_path, candidate_factory=altered)
    assert not result["passed"]
    assert "behavioral_mismatch" in {f["code"] for f in result["findings"]}


@pytest.mark.parametrize("patch", [
    {"threshold": True}, {"threshold": "50"}, {"threshold": 51},
    {"below": "exec"}, {"operation": "os.system"}, {"evidence_dir": "/tmp/override"},
    {"nodes": []},
])
def test_answers_fail_closed(tmp_path, patch):
    with pytest.raises(ValueError):
        check_design({**ANSWERS, **patch}, evidence_dir=tmp_path)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("threshold", [10, 50, 100])
@pytest.mark.parametrize("below,upper,expected", [
    ("ACCEPTED", "REVIEW", ["ACCEPTED", "REVIEW", "REVIEW"]),
    ("REVIEW", "ACCEPTED", ["REVIEW", "ACCEPTED", "ACCEPTED"]),
    ("ACCEPTED", "ACCEPTED", ["ACCEPTED"] * 3),
    ("REVIEW", "REVIEW", ["REVIEW"] * 3),
])
def test_catalog_choices_have_independent_expected_routes(tmp_path, threshold, below, upper, expected):
    raw = {"threshold": threshold, "below": below, "at_or_above": upper}
    result = check_design(raw, evidence_dir=tmp_path)
    assert result["passed"]
    terminals = [RunLog(Path(item["candidate_log"])).read()[-1].terminal
                 for item in result["evidence"]]
    assert terminals == expected


def test_audit_write_failure_never_passes(tmp_path, monkeypatch):
    def fail_write(self, event):
        raise OSError("audit disk unavailable")
    monkeypatch.setattr(RunLog, "append_next", fail_write)
    result = check_design(ANSWERS, evidence_dir=tmp_path)
    assert not result["passed"]
    assert result["completed_cases"] == []
    assert result["findings"][0]["code"] == "incomplete"


def test_configured_hermes_root_is_protected_before_generation(tmp_path, monkeypatch):
    home = tmp_path / "hermes"
    monkeypatch.setenv("HERMES_HOME", str(home))
    with pytest.raises(ValueError, match="outside Hermes"):
        check_design(ANSWERS, evidence_dir=home / "evidence")
    assert not home.exists()
