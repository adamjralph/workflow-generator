"""Ticket 08: callers validate declarations, never execute a workflow here."""

import pytest

from agent_lab.spec import TransformNode, validate_spec


def linear():
    return {
        "entry": "start",
        "nodes": ({"id": "start", "kind": "transform", "operation": "example.copy"},),
        "edges": ({"kind": "route", "source": "start", "outcome": "done", "target": "SUCCESS"},),
        "budget": 5,
        "terminals": ("SUCCESS",),
    }


def test_caller_can_validate_a_linear_spec_without_executing_its_operation():
    result = validate_spec(linear())
    assert result.valid
    assert result.findings == ()
    assert result.spec is not None
    assert result.spec.entry == "start"
    assert result.spec.budget == 5
    assert result.spec.nodes[0].kind == "transform"


@pytest.mark.parametrize("change, code, path", [
    ({"entry": "absent"}, "missing_entry", ("entry",)),
    ({"nodes": linear()["nodes"] * 2}, "duplicate_identity", ("nodes", 1, "id")),
    ({"terminals": ("SUCCESS", "SUCCESS")}, "duplicate_identity", ("terminals", 1)),
    ({"terminals": ("SUCCESS", "start")}, "duplicate_identity", ("terminals", 1)),
    ({"edges": ({"kind": "route", "source": "absent", "outcome": "done", "target": "SUCCESS"},)},
     "unknown_reference", ("edges", 0, "source")),
    ({"edges": ({"kind": "route", "source": "start", "outcome": "done", "target": "absent"},)},
     "unknown_reference", ("edges", 0, "target")),
])
def test_invalid_graph_references_return_located_findings(change, code, path):
    result = validate_spec(linear() | change)
    assert not result.valid
    assert result.spec is None
    assert (code, path) in {(f.code, f.path) for f in result.findings}
    assert result == validate_spec(linear() | change)


def branching():
    return {
        "entry": "judge",
        "nodes": (
            {"id": "judge", "kind": "judgment", "options": ("yes", "no")},
            {"id": "route", "kind": "decision", "value": "judgment.confidence",
             "cases": ("high", "low")},
            {"id": "approve", "kind": "gate"},
        ),
        "edges": (
            {"kind": "route", "source": "judge", "outcome": "yes", "target": "route"},
            {"kind": "route", "source": "judge", "outcome": "no", "target": "REJECTED"},
            {"kind": "route", "source": "route", "outcome": "high", "target": "approve"},
            {"kind": "route", "source": "route", "outcome": "low", "target": "PAUSED"},
            {"kind": "route", "source": "approve", "outcome": "approved", "target": "SUCCESS"},
            {"kind": "route", "source": "approve", "outcome": "rejected", "target": "REJECTED"},
            {"kind": "route", "source": "approve", "outcome": "pending", "target": "PAUSED"},
            {"kind": "route", "source": "approve", "outcome": "invalid", "target": "FAILED"},
        ),
        "budget": 8,
        "terminals": ("SUCCESS", "REJECTED", "PAUSED", "FAILED"),
    }


def test_judgment_decision_and_gate_declare_distinct_complete_routes():
    result = validate_spec(branching())
    assert result.valid, result.findings
    assert [n.kind for n in result.spec.nodes] == ["judgment", "decision", "gate"]


@pytest.mark.parametrize("edges, code", [
    (branching()["edges"][1:], "missing_route"),
    (branching()["edges"] + (branching()["edges"][0],), "conflicting_route"),
    (branching()["edges"] + ({"kind": "route", "source": "judge", "outcome": "maybe",
                              "target": "SUCCESS"},), "unknown_outcome"),
])
def test_routing_must_cover_exactly_the_declared_outcomes(edges, code):
    result = validate_spec(branching() | {"edges": edges})
    assert result.spec is None
    assert code in {f.code for f in result.findings}


@pytest.mark.parametrize("options", [(), ("yes", "yes")])
def test_judgment_choices_are_nonempty_and_distinct(options):
    candidate = branching()
    candidate["nodes"] = (candidate["nodes"][0] | {"options": options}, *candidate["nodes"][1:])
    result = validate_spec(candidate)
    assert not result.valid
    assert any(f.path[:2] == ("nodes", 0) for f in result.findings)


def retrying():
    return linear() | {
        "entry": "retry",
        "nodes": (
            {"id": "retry", "kind": "loop", "max_iterations": 3, "exit_predicate": "example.ready"},
            {"id": "start", "kind": "transform", "operation": "example.retry"},
        ),
        "edges": (
            {"kind": "route", "source": "retry", "outcome": "repeat", "target": "start"},
            {"kind": "route", "source": "retry", "outcome": "exit", "target": "SUCCESS"},
            {"kind": "route", "source": "retry", "outcome": "exhausted", "target": "FAILED"},
            {"kind": "route", "source": "start", "outcome": "done", "target": "retry"},
        ),
        "terminals": ("SUCCESS", "FAILED"),
    }


def test_retry_cycle_is_explicit_and_bounded_without_evaluating_predicate():
    result = validate_spec(retrying())
    assert result.valid, result.findings
    assert result.spec.nodes[0].max_iterations == 3


@pytest.mark.parametrize("bound", [0, -1, True, 1.5, "3", None])
def test_loop_requires_a_positive_integer_bound(bound):
    candidate = retrying()
    candidate["nodes"] = (candidate["nodes"][0] | {"max_iterations": bound}, candidate["nodes"][1])
    result = validate_spec(candidate)
    assert not result.valid
    assert any(f.path[-1] == "max_iterations" for f in result.findings)


@pytest.mark.parametrize("outcome", ["exit", "exhausted"])
def test_loop_exit_cannot_bypass_its_repeat_bound(outcome):
    candidate = retrying()
    candidate["edges"] = tuple(e | {"target": "start"} if e["outcome"] == outcome else e
                               for e in candidate["edges"])
    result = validate_spec(candidate)
    assert not result.valid
    assert "unbounded_cycle" in {f.code for f in result.findings}


def parallel_waves():
    return {
        "entry": "start",
        "nodes": tuple({"id": name, "kind": "transform", "operation": f"example.{name}"}
                       for name in ("start", "a", "b", "join1", "c", "d", "join2")),
        "edges": (
            {"kind": "fork", "source": "start", "outcome": "done", "branches": ("a", "b"), "join": "join1"},
            {"kind": "route", "source": "a", "outcome": "done", "target": "join1"},
            {"kind": "route", "source": "b", "outcome": "done", "target": "join1"},
            {"kind": "fork", "source": "join1", "outcome": "done", "branches": ("c", "d"), "join": "join2"},
            {"kind": "route", "source": "c", "outcome": "done", "target": "join2"},
            {"kind": "route", "source": "d", "outcome": "done", "target": "join2"},
            {"kind": "route", "source": "join2", "outcome": "done", "target": "SUCCESS"},
        ),
        "budget": 20,
        "terminals": ("SUCCESS",),
    }


def test_two_parallel_waves_have_explicit_existing_node_joins():
    result = validate_spec(parallel_waves())
    assert result.valid, result.findings
    assert result.spec.edges[0].join == "join1"
    assert result.spec.edges[3].join == "join2"
    assert {n.kind for n in result.spec.nodes} == {"transform"}


@pytest.mark.parametrize("change, code", [
    ({"branches": ("a",)}, "invalid_declaration"),
    ({"branches": ("a", "a")}, "invalid_fork"),
    ({"branches": ("a", "missing")}, "unknown_reference"),
    ({"branches": ("a", "SUCCESS")}, "unknown_reference"),
    ({"branches": ("a", "join1")}, "invalid_fork"),
    ({"join": "missing"}, "unknown_reference"),
    ({"join": "SUCCESS"}, "unknown_reference"),
    ({"join": "start"}, "invalid_fork"),
])
def test_forks_require_distinct_branches_and_a_real_convergence(change, code):
    candidate = parallel_waves()
    candidate["edges"] = (candidate["edges"][0] | change, *candidate["edges"][1:])
    result = validate_spec(candidate)
    assert not result.valid
    assert code in {f.code for f in result.findings}
    assert any(f.path[:2] == ("edges", 0) for f in result.findings)


def test_a_branch_cannot_silently_skip_its_join():
    candidate = parallel_waves()
    candidate["edges"] = tuple(e | {"target": "SUCCESS"} if e["source"] == "b" else e
                               for e in candidate["edges"])
    result = validate_spec(candidate)
    assert not result.valid
    assert "invalid_join" in {f.code for f in result.findings}


def test_multiple_routes_are_not_silently_treated_as_parallel_fanout():
    candidate = linear()
    candidate["edges"] = candidate["edges"] * 2
    result = validate_spec(candidate)
    assert not result.valid
    assert "conflicting_route" in {f.code for f in result.findings}


@pytest.mark.parametrize("change", [
    {"budget": 0}, {"budget": -1}, {"budget": True}, {"budget": "5"}, {"budget": 1.5},
    {"terminals": ()}, {"terminals": ("",)}, {"entry": "   "}, {"extra": "ignored?"},
    {"nodes": ({"id": "start", "kind": "invented"},)},
    {"nodes": ({"id": "start", "operation": "example.copy"},)},
    {"nodes": ({"id": "start", "kind": "transform", "operation": lambda: None},)},
    {"nodes": ({"id": "start", "kind": "transform", "operation": "   "},)},
    {"nodes": ({"id": "start", "kind": "transform", "operation": "copy", "outcomes": ()},)},
    {"nodes": ({"id": "start", "kind": "decision", "value": "x", "cases": ()},)},
    {"nodes": ({"id": "start", "kind": "judgment", "options": (True, "no")},)},
    {"nodes": ({"id": "start", "kind": "gate", "outcomes": ("approved",)},)},
    {"nodes": ({"id": "start", "kind": "loop", "max_iterations": 3},)},
    {"edges": ({"kind": "invented", "source": "start", "target": "SUCCESS"},)},
    {"edges": ({"source": "start", "outcome": "done", "target": "SUCCESS"},)},
])
def test_malformed_declarations_fail_without_coercion_or_execution(change):
    result = validate_spec(linear() | change)
    assert not result.valid
    assert result.spec is None
    assert {f.code for f in result.findings} == {"invalid_declaration"}
    assert all(f.path for f in result.findings)


@pytest.mark.parametrize("candidate", [None, "not a spec", 1, (), []])
def test_bad_top_level_candidates_are_findings_not_exceptions(candidate):
    result = validate_spec(candidate)
    assert not result.valid
    assert result.findings[0].code == "invalid_declaration"


def test_validated_declarations_are_immutable_and_revalidated_at_admission():
    spec = validate_spec(linear()).spec
    assert spec is not None
    assert validate_spec(spec).valid
    with pytest.raises(ValueError):
        spec.budget = 10
    with pytest.raises(ValueError):
        spec.nodes[0].id = "changed"
    invalid = spec.model_copy(update={"budget": True})
    assert not validate_spec(invalid).valid
    forged_node = TransformNode.model_construct(id="start", operation=lambda: None)
    forged = spec.model_copy(update={"nodes": (forged_node,)})
    assert not validate_spec(forged).valid
    dangling = spec.model_copy(update={"entry": "missing"})
    assert validate_spec(dangling).findings[0].code == "missing_entry"
    assert spec.nodes[0].id == "start"


def foundation_route():
    """Hand-authored from workflow.py and ADR 0007, not derived from the validator.

    Generic runtime failure/budget handling is not executed or compiled here.
    """
    return {
        "entry": "intake",
        "nodes": (
            {"id": "intake", "kind": "transform", "operation": "foundation.intake"},
            {"id": "classify", "kind": "judgment",
             "options": ("review_follow_up", "payment_follow_up", "not_a_fit")},
            {"id": "route", "kind": "decision", "value": "foundation.judgment_route",
             "cases": ("reject", "low_confidence", "prepare")},
            {"id": "prepare", "kind": "transform", "operation": "foundation.prepare"},
            {"id": "verify", "kind": "transform", "operation": "foundation.verify",
             "outcomes": ("valid", "invalid")},
            {"id": "await_approval", "kind": "gate"},
        ),
        "edges": (
            {"kind": "route", "source": "intake", "outcome": "done", "target": "classify"},
            {"kind": "route", "source": "classify", "outcome": "review_follow_up", "target": "route"},
            {"kind": "route", "source": "classify", "outcome": "payment_follow_up", "target": "route"},
            {"kind": "route", "source": "classify", "outcome": "not_a_fit", "target": "route"},
            {"kind": "route", "source": "route", "outcome": "reject", "target": "REJECTED"},
            {"kind": "route", "source": "route", "outcome": "low_confidence", "target": "NEEDS_REVIEW"},
            {"kind": "route", "source": "route", "outcome": "prepare", "target": "prepare"},
            {"kind": "route", "source": "prepare", "outcome": "done", "target": "verify"},
            {"kind": "route", "source": "verify", "outcome": "valid", "target": "await_approval"},
            {"kind": "route", "source": "verify", "outcome": "invalid", "target": "FAILED_VALIDATION"},
            {"kind": "route", "source": "await_approval", "outcome": "approved", "target": "SUCCESS"},
            {"kind": "route", "source": "await_approval", "outcome": "rejected", "target": "REJECTED"},
            {"kind": "route", "source": "await_approval", "outcome": "pending", "target": "NEEDS_REVIEW"},
            {"kind": "route", "source": "await_approval", "outcome": "invalid", "target": "FAILED_VALIDATION"},
        ),
        "budget": 8,
        "terminals": ("SUCCESS", "NEEDS_REVIEW", "FAILED_VALIDATION", "FAILED_BUDGET", "REJECTED"),
    }


def test_foundation_business_route_is_one_instance_not_the_spec_type_system():
    result = validate_spec(foundation_route())
    assert result.valid, result.findings
    assert [(n.id, n.kind) for n in result.spec.nodes] == [
        ("intake", "transform"), ("classify", "judgment"), ("route", "decision"),
        ("prepare", "transform"), ("verify", "transform"), ("await_approval", "gate"),
    ]
    assert result.spec.terminals == (
        "SUCCESS", "NEEDS_REVIEW", "FAILED_VALIDATION", "FAILED_BUDGET", "REJECTED",
    )


def test_a_cycle_without_any_loop_is_rejected():
    candidate = linear()
    candidate["edges"] = (candidate["edges"][0] | {"target": "start"},)
    result = validate_spec(candidate)
    assert not result.valid
    assert result.findings[0].code == "unbounded_cycle"
    assert result.findings[0].path == ("edges", 0)


@pytest.mark.parametrize("kind, fields", [
    ("transform", {"operation": "copy", "outcomes": ("done", "done")}),
    ("decision", {"value": "x", "cases": ("done", "done")}),
])
def test_other_node_outcome_vocabularies_also_require_distinct_labels(kind, fields):
    candidate = linear() | {"nodes": ({"id": "start", "kind": kind, **fields},)}
    result = validate_spec(candidate)
    assert not result.valid
    assert "duplicate_outcome" in {f.code for f in result.findings}


def test_each_outcome_needs_a_single_destination_even_when_destinations_differ():
    candidate = branching()
    candidate["edges"] += (candidate["edges"][0] | {"target": "REJECTED"},)
    result = validate_spec(candidate)
    assert not result.valid
    assert "conflicting_route" in {f.code for f in result.findings}


def test_join_validation_checks_all_branch_routes_not_just_one_reachable_path():
    candidate = parallel_waves()
    candidate["nodes"] = tuple(
        {"kind": "decision", "id": "b", "value": "x", "cases": ("done", "escape")}
        if n["id"] == "b" else n for n in candidate["nodes"])
    candidate["edges"] += ({"kind": "route", "source": "b", "outcome": "escape", "target": "SUCCESS"},)
    result = validate_spec(candidate)
    assert not result.valid
    assert "invalid_join" in {f.code for f in result.findings}


def test_a_terminal_cannot_be_an_entry_or_an_edge_source():
    candidate = linear() | {"entry": "SUCCESS"}
    candidate["edges"] = (candidate["edges"][0] | {"source": "SUCCESS"},)
    result = validate_spec(candidate)
    assert {f.code for f in result.findings} == {"missing_entry", "unknown_reference"}


def test_an_unrelated_loop_does_not_legalize_an_unbounded_cycle():
    candidate = retrying()
    candidate["edges"] = (*candidate["edges"][:-1],
                          {"kind": "route", "source": "start", "outcome": "done", "target": "start"})
    result = validate_spec(candidate)
    assert not result.valid
    assert "unbounded_cycle" in {f.code for f in result.findings}
