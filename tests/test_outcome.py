"""Ticket 34: agreed declaration and run/file/verdict boundaries."""
import hashlib
import json
import os
from pathlib import Path

import pytest
from pydantic import BaseModel, ConfigDict

from agent_lab.reference import TransformResult

from agent_lab.reference import compile_reference
from agent_lab.spec import JsonOutputExpectation, Route, TransformNode, WorkflowSpec


class State(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)
    value: int = 0


def workflow():
    return WorkflowSpec(
        entry="produce", budget=1,
        nodes=(TransformNode(id="produce", operation="write_fixture",
            expected_output=JsonOutputExpectation(file="result.json", required_fields=("title", "body"))),),
        edges=(Route(source="produce", outcome="done", target="COMPLETED"),),
        terminals=("COMPLETED", "FAILED_VALIDATION", "FAILED_BUDGET"),
    )


def test_unsafe_declaration_is_rejected_before_execution():
    spec = workflow()
    node = spec.nodes[0]
    invalid = node.expected_output.model_copy(update={"file": "../private.json"})
    malformed = spec.model_copy(update={"nodes": (node.model_copy(update={"expected_output": invalid}),)})
    compiled = compile_reference(malformed, state_type=State,
        bindings={"write_fixture": lambda state: (_ for _ in ()).throw(AssertionError("binding invoked"))})
    assert compiled.plan is None
    assert compiled.findings[0].code == "invalid_declaration"


@pytest.mark.parametrize("driver", ["reference", "graph"])
def test_run_checks_actual_file_and_saves_attributed_verdict(driver):
    from agent_lab.outcome import run_checked

    def bindings(output):
        def produce(state):
            (output / "result.json").write_text('{"title":"Fixture", "body":"Actual output"}')
            return TransformResult(state, "done")
        return {"write_fixture": produce}

    result = run_checked(workflow(), State(), bindings_factory=bindings,
        evidence_dir=Path(os.environ["WORKFLOW_VALIDATION_DIR"]), driver=driver)
    assert result.execution.terminal == "COMPLETED"
    assert result.verdict.passed is True
    assert result.verdict.step == "produce"
    assert result.verdict.declaration == workflow().nodes[0].expected_output
    assert result.verdict.findings == ()
    saved = json.loads(result.verdict_path.read_text())
    assert saved["run_id"] == result.run_id
    assert saved["step"] == "produce"
    assert saved["passed"] is True
    assert saved["declaration"]["required_fields"] == ["title", "body"]
    assert (result.root / "output/result.json").is_file()
    assert saved["output_digest"] == hashlib.sha256((result.root / "output/result.json").read_bytes()).hexdigest()
    assert saved["spec_digest"] == hashlib.sha256((result.root / "declaration.json").read_bytes()).hexdigest()


@pytest.mark.parametrize("driver", ["reference", "graph"])
@pytest.mark.parametrize("body,code,requirement", [
    (None, "missing_file", "result.json"),
    ("not JSON", "invalid_json", "result.json"),
    ('{"title":"Fixture"}', "missing_field", "body"),
    ("[]", "invalid_object", "result.json"),
])
def test_completed_workflow_can_fail_output_check(driver, body, code, requirement):
    from agent_lab.outcome import run_checked

    def bindings(output):
        def produce(state):
            if body is not None:
                (output / "result.json").write_text(body)
            return TransformResult(state, "done")
        return {"write_fixture": produce}

    result = run_checked(workflow(), State(), bindings_factory=bindings,
        evidence_dir=Path(os.environ["WORKFLOW_VALIDATION_DIR"]), driver=driver)
    assert result.execution.terminal == "COMPLETED"
    assert result.verdict.passed is False
    assert [(f.code, f.requirement) for f in result.verdict.findings] == [(code, requirement)]
    saved = json.loads(result.verdict_path.read_text())
    assert saved["passed"] is False
    assert saved["findings"] == [{"code": code, "requirement": requirement}]


@pytest.mark.parametrize("escape", ["symlink", "parent_symlink", "root_symlink", "hardlink", "directory"])
def test_unsafe_files_fail_without_reading_outside_output(escape):
    from agent_lab.outcome import run_checked

    def bindings(output):
        # A real valid external file: following a link would incorrectly pass.
        outside = output.parent / "outside"
        outside.mkdir()
        target = outside / "result.json"
        target.write_text('{"title":"private", "body":"must not be read"}')
        def produce(state):
            if escape == "symlink":
                (output / "result.json").symlink_to(target)
            elif escape == "parent_symlink":
                (output / "nested").symlink_to(outside, target_is_directory=True)
            elif escape == "root_symlink":
                output.rmdir()
                output.symlink_to(outside, target_is_directory=True)
            elif escape == "hardlink":
                os.link(target, output / "result.json")
            else:
                (output / "result.json").mkdir()
            return TransformResult(state, "done")
        return {"write_fixture": produce}

    spec = workflow()
    if escape == "parent_symlink":
        node = spec.nodes[0]
        spec = spec.model_copy(update={"nodes": (node.model_copy(update={"expected_output":
            JsonOutputExpectation(file="nested/result.json", required_fields=("title", "body"))}),)})
    result = run_checked(spec, State(), bindings_factory=bindings,
        evidence_dir=Path(os.environ["WORKFLOW_VALIDATION_DIR"]))
    assert result.verdict.passed is False
    assert result.verdict.findings[0].code == "unsafe_file"
    assert result.verdict.output_digest is None


@pytest.mark.parametrize("driver", ["reference", "graph"])
def test_unexecuted_checked_step_cannot_pass_using_another_steps_file(driver):
    from agent_lab.outcome import run_checked

    spec = workflow()
    spec = spec.model_copy(update={"entry": "other", "nodes": spec.nodes +
        (TransformNode(id="other", operation="write_fixture"),), "edges": spec.edges +
        (Route(source="other", outcome="done", target="COMPLETED"),)})
    def bindings(output):
        def produce(state):
            (output / "result.json").write_text('{"title":"other step", "body":"not checked step"}')
            return TransformResult(state, "done")
        return {"write_fixture": produce}
    result = run_checked(spec, State(), bindings_factory=bindings,
        evidence_dir=Path(os.environ["WORKFLOW_VALIDATION_DIR"]), driver=driver)
    assert result.execution.terminal == "COMPLETED"
    assert result.verdict.passed is False
    assert result.verdict.findings[0].code == "step_not_completed"


@pytest.mark.parametrize("body", [b'{"title":NaN,"body":"bad"}', b'{"title":1,"body":Infinity}', b'\xff'])
def test_non_json_values_are_rejected(body):
    from agent_lab.outcome import run_checked
    def bindings(output):
        def produce(state):
            (output / "result.json").write_bytes(body)
            return TransformResult(state, "done")
        return {"write_fixture": produce}
    result = run_checked(workflow(), State(), bindings_factory=bindings,
        evidence_dir=Path(os.environ["WORKFLOW_VALIDATION_DIR"]))
    assert result.verdict.passed is False
    assert result.verdict.findings[0].code == "invalid_json"


def test_declaration_is_saved_before_fixture_executes():
    from agent_lab.outcome import run_checked
    def bindings(output):
        def produce(state):
            snapshot = json.loads((output.parent / "declaration.json").read_text())
            assert snapshot["nodes"][0]["expected_output"]["file"] == "result.json"
            (output / "result.json").write_text('{"title":null,"body":"fixture"}')
            return TransformResult(state, "done")
        return {"write_fixture": produce}
    result = run_checked(workflow(), State(), bindings_factory=bindings,
        evidence_dir=Path(os.environ["WORKFLOW_VALIDATION_DIR"]))
    assert result.verdict.passed is True


@pytest.mark.parametrize("file", ["../private.json", "/private.json", "nested/../result.json",
    "nested//result.json", "./result.json", "nested\\result.json", "bad\x00.json"])
def test_bad_path_cannot_reach_binding_factory(file):
    from agent_lab.outcome import run_checked
    node = workflow().nodes[0]
    bad = node.expected_output.model_copy(update={"file": file})
    spec = workflow().model_copy(update={"nodes": (node.model_copy(update={"expected_output": bad}),)})
    with pytest.raises(ValueError, match="Invalid declaration"):
        run_checked(spec, State(), bindings_factory=lambda output: pytest.fail("factory ran"),
            evidence_dir=Path(os.environ["WORKFLOW_VALIDATION_DIR"]))


def test_oversized_output_fails_with_bounded_read():
    from agent_lab.outcome import run_checked
    def bindings(output):
        def produce(state):
            (output / "result.json").write_text('{"title":"' + 'x' * (1024 * 1024) + '","body":"large"}')
            return TransformResult(state, "done")
        return {"write_fixture": produce}
    result = run_checked(workflow(), State(), bindings_factory=bindings,
        evidence_dir=Path(os.environ["WORKFLOW_VALIDATION_DIR"]))
    assert result.verdict.passed is False
    assert result.verdict.findings[0].code == "file_too_large"


@pytest.mark.parametrize("limit,passed", [(20, False), (200, True)])
def test_declared_size_limit_is_used(limit, passed):
    from agent_lab.outcome import run_checked
    node = workflow().nodes[0]
    expectation = JsonOutputExpectation(file="result.json", required_fields=("title", "body"), max_bytes=limit)
    spec = workflow().model_copy(update={"nodes": (node.model_copy(update={"expected_output": expectation}),)})
    def bindings(output):
        def produce(state):
            (output / "result.json").write_text('{"title":"Fixture", "body":"Actual output"}')
            return TransformResult(state, "done")
        return {"write_fixture": produce}
    result = run_checked(spec, State(), bindings_factory=bindings,
        evidence_dir=Path(os.environ["WORKFLOW_VALIDATION_DIR"]))
    assert result.verdict.passed is passed
    assert result.verdict.declaration.max_bytes == limit


@pytest.mark.parametrize("limit", [0, -1, True, "100"])
def test_invalid_size_limit_is_rejected_before_execution(limit):
    from agent_lab.outcome import run_checked
    node = workflow().nodes[0]
    bad = node.expected_output.model_copy(update={"max_bytes": limit})
    spec = workflow().model_copy(update={"nodes": (node.model_copy(update={"expected_output": bad}),)})
    with pytest.raises(ValueError, match="Invalid declaration"):
        run_checked(spec, State(), bindings_factory=lambda output: pytest.fail("factory ran"),
            evidence_dir=Path(os.environ["WORKFLOW_VALIDATION_DIR"]))


def test_safe_nested_file_passes_and_names_all_missing_fields():
    from agent_lab.outcome import run_checked
    node = workflow().nodes[0]
    expectation = JsonOutputExpectation(file="nested/result.json", required_fields=("title", "body"))
    spec = workflow().model_copy(update={"nodes": (node.model_copy(update={"expected_output": expectation}),)})
    for payload, missing in [('{"title":null,"body":false}', []), ('{}', ["title", "body"])]:
        def bindings(output):
            def produce(state):
                (output / "nested").mkdir()
                (output / "nested/result.json").write_text(payload)
                return TransformResult(state, "done")
            return {"write_fixture": produce}
        result = run_checked(spec, State(), bindings_factory=bindings,
            evidence_dir=Path(os.environ["WORKFLOW_VALIDATION_DIR"]))
        assert result.verdict.passed is (not missing)
        assert [finding.requirement for finding in result.verdict.findings] == missing
