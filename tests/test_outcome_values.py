"""Ticket 35: exact declared values using the existing LinkedIn review vocabulary."""
import hashlib
import json
import os
from pathlib import Path

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError

from agent_lab.outcome import run_checked
from agent_lab.reference import TransformResult
from agent_lab.spec import JsonOutputExpectation, Route, StringFieldExpectation, TransformNode, WorkflowSpec


class State(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)


def workflow(expectation=None):
    return WorkflowSpec(entry="review", budget=1,
        nodes=(TransformNode(id="review", operation="save_review", expected_output=expectation or
            JsonOutputExpectation(file="review.json", required_fields=("verdict", "scope"),
                string_fields=(StringFieldExpectation(field="verdict",
                    allowed_values=("Approved", "Changes requested", "Blocked")),
                    StringFieldExpectation(field="scope", allowed_values=("copy-only",))))),),
        edges=(Route(source="review", outcome="done", target="COMPLETED"),),
        terminals=("COMPLETED", "FAILED_VALIDATION", "FAILED_BUDGET"))


@pytest.mark.parametrize("driver", ["reference", "graph"])
@pytest.mark.parametrize("payload, expected", [
    ({"verdict": "Approved", "scope": "copy-only"}, []),
    ({"verdict": "Changes requested", "scope": "copy-only"}, []),
    ({"verdict": "Blocked", "scope": "copy-only"}, []),
    ({"verdict": "approved", "scope": "copy-only"}, [("unexpected_value", "verdict")]),
    ({"verdict": "Approved ", "scope": "copy-only"}, [("unexpected_value", "verdict")]),
    ({"verdict": None, "scope": "copy-only"}, [("unexpected_value", "verdict")]),
    ({"verdict": True, "scope": "copy-only"}, [("unexpected_value", "verdict")]),
    ({"verdict": 1, "scope": "copy-only"}, [("unexpected_value", "verdict")]),
    ({"verdict": ["Approved"], "scope": "copy-only"}, [("unexpected_value", "verdict")]),
    ({"verdict": {"value": "Approved"}, "scope": "copy-only"}, [("unexpected_value", "verdict")]),
    ({"scope": "copy-only"}, [("missing_field", "verdict")]),
    ({"verdict": "PRIVATE unexpected text", "scope": "full"},
        [("unexpected_value", "verdict"), ("unexpected_value", "scope")]),
])
def test_saved_verdict_checks_exact_values_through_both_drivers(driver, payload, expected):
    def bindings(output):
        def save(state):
            (output / "review.json").write_text(json.dumps(payload), encoding="utf-8")
            return TransformResult(state, "done")
        return {"save_review": save}
    result = run_checked(workflow(), State(), bindings_factory=bindings,
        evidence_dir=Path(os.environ["WORKFLOW_VALIDATION_DIR"]), driver=driver)
    assert result.execution.terminal == "COMPLETED"
    assert result.verdict.passed == (not expected)
    assert [(f.code, f.requirement) for f in result.verdict.findings] == expected
    saved = json.loads(result.verdict_path.read_text())
    assert "PRIVATE" not in result.verdict_path.read_text()
    assert saved["run_id"] == result.run_id
    assert saved["declaration"]["string_fields"][0]["allowed_values"] == ["Approved", "Changes requested", "Blocked"]
    assert saved["spec_digest"] == hashlib.sha256((result.root / "declaration.json").read_bytes()).hexdigest()
    assert saved["output_digest"] == hashlib.sha256((result.root / "output/review.json").read_bytes()).hexdigest()
    declared = json.loads((result.root / "declaration.json").read_text())
    assert declared["nodes"][0]["expected_output"] == saved["declaration"]


@pytest.mark.parametrize("body", [
    '{"verdict":"unapproved","verdict":"Approved","scope":"copy-only"}',
    '{"verdict":"Approved","scope":"copy-only","extra":{"x":1,"x":2}}',
])
def test_duplicate_json_keys_fail_visible(body):
    def bindings(output):
        def save(state):
            (output / "review.json").write_text(body, encoding="utf-8")
            return TransformResult(state, "done")
        return {"save_review": save}
    result = run_checked(workflow(), State(), bindings_factory=bindings,
        evidence_dir=Path(os.environ["WORKFLOW_VALIDATION_DIR"]))
    assert [(f.code, f.requirement) for f in result.verdict.findings] == [("invalid_json", "review.json")]


@pytest.mark.parametrize("values", [(), ("Approved", "Approved"), (1,), (True,), ["Approved"]])
def test_invalid_allowed_values_rejected(values):
    with pytest.raises(ValidationError):
        StringFieldExpectation(field="verdict", allowed_values=values)


@pytest.mark.parametrize("fields", [
    (StringFieldExpectation(field="absent", allowed_values=("x",)),),
    (StringFieldExpectation(field="verdict", allowed_values=("x",)),) * 2,
])
def test_constraints_must_name_distinct_required_fields(fields):
    with pytest.raises(ValidationError):
        JsonOutputExpectation(file="review.json", required_fields=("verdict",), string_fields=fields)


def test_copied_invalid_nested_constraint_rejected_before_work():
    constraint = StringFieldExpectation(field="verdict", allowed_values=("Approved",))
    malformed = constraint.model_copy(update={"allowed_values": ()})
    expectation = JsonOutputExpectation(file="review.json", required_fields=("verdict",))
    malformed_expectation = expectation.model_copy(update={"string_fields": (malformed,)})
    spec = workflow()
    malformed_spec = spec.model_copy(update={"nodes": (spec.nodes[0].model_copy(
        update={"expected_output": malformed_expectation}),)})
    with pytest.raises(ValueError, match="Invalid declaration"):
        run_checked(malformed_spec, State(),
            bindings_factory=lambda _: pytest.fail("Bindings must not execute"),
            evidence_dir=Path(os.environ["WORKFLOW_VALIDATION_DIR"]))
