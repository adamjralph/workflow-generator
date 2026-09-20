"""Role composition through public authoring, run and checking seams."""
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import replace

import pytest

from pathlib import Path

from agent_lab.designer import author_design, check_design, generate_candidate
from agent_lab.designer.custom import run_request
from agent_lab.runlog import RunLog
from agent_lab.generation import generate_graph
from agent_lab.reference import TransformResult, compile_reference
from agent_lab.spec import Route

DEFAULT = {"mode": "roles", "producer": "signal_generator",
           "output": "evidence_handoff", "consumer": "signal_guardian"}


def test_two_role_workflow_executes_both_independently_expected_cases(tmp_path):
    design = author_design(DEFAULT)
    assert design.spec.budget == 2
    assert [(n.id, n.kind) for n in design.spec.nodes] == [
        ("generator", "transform"), ("guardian", "transform")]
    result = check_design(DEFAULT, evidence_dir=tmp_path)
    assert result["passed"] is True
    assert result["cases"] == ["with_evidence", "without_evidence"]
    assert [item["state"] for item in result["outputs"]] == [
        {"brief": {"request_id": "fixture-with", "text": "Write a synthetic update.",
                   "evidence_labels": ["synthetic-note"]},
         "handoff": {"request_id": "fixture-with", "text": "Write a synthetic update.",
                     "evidence_labels": ["synthetic-note"]},
         "verdict": {"request_id": "fixture-with", "evidence_count": 1,
                     "result": "evidence_present"}},
        {"brief": {"request_id": "fixture-without", "text": "Write a synthetic update.",
                   "evidence_labels": []},
         "handoff": {"request_id": "fixture-without", "text": "Write a synthetic update.",
                     "evidence_labels": []},
         "verdict": {"request_id": "fixture-without", "evidence_count": 0,
                     "result": "evidence_missing"}},
    ]
    for item in result["outputs"]:
        assert item["terminal"] == "COMPLETED"
        assert item["used_steps"] == 2
        assert item["route"] == [["generator", "done", "guardian"],
                                 ["guardian", "done", "COMPLETED"]]


def test_check_evidence_is_fresh_and_independent_with_identical_recorded_traces(tmp_path):
    first = check_design(DEFAULT, evidence_dir=tmp_path)
    second = check_design(DEFAULT, evidence_dir=tmp_path)
    paths = set()
    for result in (first, second):
        assert result["passed"] is True
        for record in result["evidence"]:
            reference = RunLog(Path(record["reference_log"]))
            candidate = RunLog(Path(record["candidate_log"]))
            assert reference.path != candidate.path
            assert reference.read_bytes() == candidate.read_bytes()
            assert reference.digest() == candidate.digest()
            assert len(reference.read()) == 2
            paths.update((reference.path, candidate.path))
    assert len(paths) == 8


def test_selected_fixture_runs_generated_graph_alone_with_fresh_state_and_evidence(tmp_path):
    present = run_request(DEFAULT, {"fixture": "with_evidence"}, evidence_dir=tmp_path)
    missing = run_request(DEFAULT, {"fixture": "without_evidence"}, evidence_dir=tmp_path)
    again = run_request(DEFAULT, {"fixture": "with_evidence"}, evidence_dir=tmp_path)
    assert present["succeeded"] is missing["succeeded"] is again["succeeded"] is True
    assert present["output"]["state"]["verdict"] == {
        "request_id": "fixture-with", "evidence_count": 1, "result": "evidence_present"}
    assert missing["output"]["state"]["verdict"] == {
        "request_id": "fixture-without", "evidence_count": 0, "result": "evidence_missing"}
    assert again["output"] == present["output"]
    assert "passed" not in present
    assert present["input"] == {"request_id": "fixture-with", "text": "Write a synthetic update.",
                                "evidence_labels": ["synthetic-note"]}
    assert len({item["evidence"] for item in (present, missing, again)}) == 3
    for item in (present, missing, again):
        log = RunLog(Path(item["evidence"]))
        assert log.path.is_relative_to(tmp_path)
        assert [event.seq for event in log.read()] == [0, 1]
        assert [event.detail["used_steps"] for event in log.read()] == [1, 2]
        assert list(log.path.parent.glob("*.jsonl")) == [log.path]


@pytest.mark.parametrize("field,value", [
    ("request_id", ""), ("request_id", " \n"), ("request_id", "😀" * 65),
    ("request_id", 42), ("request_id", True), ("request_id", None),
    ("text", ""), ("text", "\t"), ("text", "😀" * 241), ("text", False),
    ("evidence_labels", ("same", "same")), ("evidence_labels", ("",)),
    ("evidence_labels", (" \n",)), ("evidence_labels", ("a", "b", "c", "d")),
    ("evidence_labels", ("😀" * 65,)), ("evidence_labels", (False,)),
    ("evidence_labels", "abc"), ("evidence_labels", None),
])
def test_invalid_briefs_rejected_at_core_run_boundary_before_evidence(tmp_path, field, value):
    design = author_design(DEFAULT)
    state = design.cases["with_evidence"]
    invalid = state.model_copy(update={"brief": state.brief.model_copy(update={field: value})})
    candidate = generate_candidate(design)
    log = RunLog(tmp_path / "invalid.jsonl")
    with pytest.raises(ValueError):
        candidate.run(invalid, run_id="invalid", log=log)
    assert not log.path.exists()


def test_unicode_bounds_and_inert_labels_preserved_without_truncation(tmp_path):
    design = author_design(DEFAULT)
    state = design.state_type.model_validate({"brief": {
        "request_id": "😀" * 64, "text": "😀" * 240,
        "evidence_labels": ("😀" * 64, "https://example.invalid", "/not/a/source")}})
    result = generate_candidate(design).run(state, run_id="unicode", log=RunLog(tmp_path / "unicode.jsonl"))
    assert result.terminal == "COMPLETED"
    assert result.state.handoff.model_dump() == {
        "request_id": "😀" * 64, "text": "😀" * 240,
        "evidence_labels": ("😀" * 64, "https://example.invalid", "/not/a/source")}
    assert result.state.verdict.evidence_count == 3


def test_catalog_shows_registry_types_and_separate_fixture_contracts():
    view = author_design(DEFAULT).view()
    catalog = view["catalog"]
    assert catalog["provenance"]["source"] == "specialist-agent-role-registry.yaml"
    roles = {role["id"]: role for role in catalog["roles"]}
    assert roles["signal_generator"]["accepts"] == [
        "bounded_writing_brief", "approved_source_material", "adam_dictation", "revision_request"]
    assert roles["signal_generator"]["produces"] == [
        "prose_artifact", "caption", "creative_brief", "evidence_handoff"]
    assert roles["signal_guardian"]["reviews"] == ["signal_generator"]
    assert roles["signal_guardian"]["produces"] == ["review_verdict", "revision_request"]
    assert roles["studio_producer"]["accepts"] == [
        "approved_copy", "caption", "creative_brief", "approved_visual_references", "revision_request"]
    assert set(catalog) == {"provenance", "roles"}
    assert all(set(role) == {"id", "display_name", "status", "accepts", "produces", "reviews", "reviewed_by"}
               for role in roles.values())
    assert "historical" in view["policy"]
    assert view["operations"] == [
        {"role": "signal_generator", "requires": ["bounded_writing_brief"], "produces": "evidence_handoff"},
        {"role": "signal_guardian", "requires": ["evidence_handoff"], "produces": "review_verdict",
         "reviews": "signal_generator"}]


@pytest.mark.parametrize("change,message", [
    ({"consumer": "studio_producer"}, "Incompatible"),
    ({"output": "caption", "consumer": "studio_producer"}, "Unsupported fixture operation"),
    ({"output": "creative_brief", "consumer": "studio_producer"}, "Unsupported fixture operation"),
    ({"producer": "unknown"}, "Unknown role"),
    ({"output": "Evidence_Handoff"}, "Incompatible"),
    ({"catalog": {}}, "Extra inputs"),
])
def test_connection_admission_precedes_generation(tmp_path, change, message):
    def forbidden(design):
        pytest.fail("inadmissible composition reached generation")
    with pytest.raises(ValueError, match=message):
        check_design({**DEFAULT, **change}, evidence_dir=tmp_path, candidate_factory=forbidden)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("change,message", [
    (lambda c: c["roles"][2].update(reviews=[]), "review relationship"),
    (lambda c: c["roles"][0].update(accepts=["revision_request"]), "fixture operation"),
    (lambda c: c["roles"][2].update(produces=["revision_request"]), "fixture operation"),
    (lambda c: c["roles"][0].update(produces="evidence_handoff"), "tuple"),
    (lambda c: c["roles"][0].update(code="exec"), "Extra inputs"),
    (lambda c: c["roles"][0].update(accepts=[""]), "blank"),
    (lambda c: c["roles"].append(c["roles"][0]), "three distinct"),
    (lambda c: c["roles"][0].update(id="unknown"), "Input should be"),
    (lambda c: c["roles"][0].update(produces=["evidence_handoff", "evidence_handoff"]), "distinct"),
    (lambda c: c["roles"][2].update(reviews=["unknown"]), "Unknown role"),
    (lambda c: c["roles"][1].update(accepts=[False]), "valid string"),
    (lambda c: c["roles"][1].update(produces=[]), "at least 1"),
    (lambda c: c["provenance"].update(source_sha256="bad"), "pattern"),
])
def test_malformed_or_insufficient_catalog_contracts_are_not_executable(change, message):
    from agent_lab.designer.roles import author_roles
    catalog = deepcopy(author_design(DEFAULT).view()["catalog"])
    change(catalog)
    with pytest.raises(ValueError, match=message):
        author_roles(DEFAULT, catalog=catalog)


def altered_candidate(kind):
    def factory(design):
        if kind == "generation":
            raise RuntimeError("deliberate generation failure")
        if kind == "unsupported":
            return object()
        if kind == "budget":
            return generate_candidate(replace(design, spec=design.spec.model_copy(update={"budget": 1})))
        if kind == "route":
            spec = design.spec.model_copy(update={"edges": (
                Route(source="generator", outcome="done", target="COMPLETED"),
                Route(source="guardian", outcome="done", target="COMPLETED"))})
            return generate_candidate(replace(design, spec=spec))
        def different(state):
            if kind == "execution":
                raise ValueError("fixture operation failed")
            outcome = design.bindings["review_handoff"](state)
            verdict = outcome.state.verdict.model_copy(update={"result": "evidence_missing"})
            return TransformResult(outcome.state.model_copy(update={"verdict": verdict}), "done")
        return generate_candidate(replace(design, bindings={**design.bindings, "review_handoff": different}))
    return factory


@pytest.mark.parametrize("kind,code", [("budget", "structural_mismatch"),
    ("route", "structural_mismatch"), ("behavior", "behavioral_mismatch"),
    ("unsupported", "unsupported_candidate"), ("execution", "behavioral_mismatch")])
def test_check_inspects_and_executes_the_supplied_candidate(tmp_path, kind, code):
    result = check_design(DEFAULT, evidence_dir=tmp_path, candidate_factory=altered_candidate(kind))
    assert result["passed"] is False
    assert code in {finding["code"] for finding in result["findings"]}
    if code != "behavioral_mismatch":
        assert result["evidence"] == []
    else:
        assert result["outputs"][0]["state"]["verdict"] != {
            "request_id": "fixture-with", "evidence_count": 1, "result": "evidence_present"}


def test_run_displays_actual_candidate_output_not_predicted_fixture(tmp_path):
    result = run_request(DEFAULT, {"fixture": "with_evidence"}, evidence_dir=tmp_path,
                         candidate_factory=altered_candidate("behavior"))
    assert result["succeeded"] is True
    assert result["output"]["state"]["verdict"]["result"] == "evidence_missing"
    assert "passed" not in result


@pytest.mark.parametrize("kind", ["budget", "route", "unsupported", "generation"])
def test_run_rejects_generation_and_structural_failures_before_evidence(tmp_path, kind):
    with pytest.raises((ValueError, RuntimeError)):
        run_request(DEFAULT, {"fixture": "with_evidence"}, evidence_dir=tmp_path,
                    candidate_factory=altered_candidate(kind))
    assert list(tmp_path.iterdir()) == []


def test_fixture_runtime_failure_is_not_success(tmp_path):
    result = run_request(DEFAULT, {"fixture": "with_evidence"}, evidence_dir=tmp_path,
                         candidate_factory=altered_candidate("execution"))
    assert result["succeeded"] is False
    assert result["output"]["terminal"] == "FAILED_VALIDATION"
    assert result["output"]["state"]["verdict"] is None


@pytest.mark.parametrize("driver", ["plain", "graph"])
def test_short_budget_stops_before_guardian_and_run_ids_cannot_be_reused(tmp_path, driver):
    design = author_design(DEFAULT)
    spec = design.spec.model_copy(update={"budget": 1})
    if driver == "plain":
        runner = compile_reference(spec, state_type=design.state_type, bindings=design.bindings).plan
    else:
        runner = generate_graph(spec, state_type=design.state_type, bindings=design.bindings).candidate
    log = RunLog(tmp_path / "short.jsonl")
    initial = design.cases["with_evidence"]
    result = runner.run(initial, run_id="short", log=log)
    assert result.terminal == "FAILED_BUDGET"
    assert result.used_steps == 1
    assert result.state.handoff is not None
    assert result.state.verdict is None
    assert initial.handoff is initial.verdict is None
    assert [(event.node, event.detail["used_steps"]) for event in log.read()] == [
        ("generator", 1), ("guardian", 1)]
    with pytest.raises(ValueError, match="already recorded"):
        runner.run(initial, run_id="short", log=log)


@pytest.mark.parametrize("selection", [None, [], {}, "with_evidence", {"fixture": True},
    {"fixture": "unknown"}, {"fixture": "with_evidence", "brief": {}},
    {"fixture": "with_evidence", "handoff": {}}, {"fixture": "with_evidence", "path": "/tmp"}])
def test_run_accepts_only_fixed_fixture_selection_before_generation(tmp_path, selection):
    def forbidden(design):
        pytest.fail("invalid request reached generation")
    with pytest.raises(ValueError):
        run_request(DEFAULT, selection, evidence_dir=tmp_path, candidate_factory=forbidden)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("failure", ["append", "read", "lost-first", "lost-last"])
def test_role_run_audit_failure_or_lost_events_never_establish_success(tmp_path, monkeypatch, failure):
    original = Path.open
    writes = 0
    @contextmanager
    def unreliable(path, mode="r", *args, **kwargs):
        nonlocal writes
        if path.suffix == ".jsonl" and ((failure == "append" and mode == "a+")
                                        or (failure == "read" and mode == "r")):
            raise OSError("audit unavailable")
        with original(path, mode, *args, **kwargs) as handle:
            if path.suffix == ".jsonl" and mode == "a+":
                write = handle.write
                def discard(data):
                    nonlocal writes
                    writes += 1
                    if (failure == "lost-first" and writes == 1) or (failure == "lost-last" and writes == 2):
                        return len(data)
                    return write(data)
                handle.write = discard
            yield handle
    monkeypatch.setattr(Path, "open", unreliable)
    with pytest.raises((OSError, RuntimeError)):
        run_request(DEFAULT, {"fixture": "with_evidence"}, evidence_dir=tmp_path)


@pytest.mark.parametrize("phase", ["reference", "candidate"])
def test_check_audit_failure_is_incomplete_not_pass(tmp_path, monkeypatch, phase):
    original = Path.open
    def fail(path, mode="r", *args, **kwargs):
        if path.name.endswith(f"-{phase}.jsonl") and mode == "a+":
            raise OSError("audit unavailable")
        return original(path, mode, *args, **kwargs)
    monkeypatch.setattr(Path, "open", fail)
    result = check_design(DEFAULT, evidence_dir=tmp_path)
    assert result["passed"] is False
    assert result["completed_cases"] == []
    assert result["findings"][0]["code"] == "incomplete"


def test_role_run_and_check_reject_symlinked_protected_outputs_before_generation(tmp_path):
    protected = tmp_path / "protected"
    protected.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(protected, target_is_directory=True)
    def forbidden(design):
        pytest.fail("protected output reached generation")
    for seam, args in ((run_request, (DEFAULT, {"fixture": "with_evidence"})), (check_design, (DEFAULT,))):
        with pytest.raises(ValueError, match="outside"):
            seam(*args, evidence_dir=alias / "logs", protected_roots=(protected,), candidate_factory=forbidden)
    assert list(protected.iterdir()) == []
