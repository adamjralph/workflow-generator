"""Independent role inputs and review application through both actual drivers."""
import hashlib
import json

import pytest

from agent_lab.designer.linkedin import canonical
from agent_lab.designer.linkedin_review import ReviewState, SPEC, operations
from agent_lab.generation import generate_graph
from agent_lab.reference import compile_reference
from agent_lab.runlog import RunLog
from tests.test_designer_drafts import operator  # noqa: F401
from tests.test_designer_draft_runs import setup
from tests.test_designer_review_server import GuardianSource
from tests.test_designer_draft_run_server import FixtureSource, POST


@pytest.mark.parametrize("driver", ["reference", "generated"])
@pytest.mark.parametrize("verdict", ["Approved", "Changes requested", "Blocked"])
def test_independent_guardian_receives_exact_original_evidence_and_draft(operator, driver, verdict):
    runs, snapshot, _ = setup(operator)
    captured = runs.source.load(snapshot)
    generator, guardian = FixtureSource(), GuardianSource(verdict)
    initial = ReviewState(snapshot=snapshot, captured_json=canonical(captured))
    kwargs = dict(state_type=ReviewState, bindings={}, model_operations=operations(generator, guardian))
    runner = (compile_reference(SPEC, **kwargs).plan if driver == "reference"
              else generate_graph(SPEC, **kwargs).candidate)
    result = runner.run(initial, run_id="review", log=RunLog(operator[2] / "review.jsonl"))
    assert result.terminal == "COMPLETED"
    assert result.used_steps == 2
    assert result.state.result.post == POST
    assert result.state.review.verdict == verdict
    assert result.state.review.draft_digest == hashlib.sha256(POST.encode()).hexdigest()
    assert initial.result is initial.review is None
    request = json.loads(guardian.requests[0].request_json)
    original = json.loads(json.loads(generator.requests[0].request_json)["input"][0]["content"][0]["text"])
    review_input = json.loads(request["messages"][1]["content"])
    assert review_input == {**original, "draft": {"post": POST, "digest": result.state.review.draft_digest}}
    assert request["model"] == captured["models"][1]["model"]
    assert request["tools"] == [] and request["stream"] is False
    assert len(generator.requests) == len(guardian.requests) == 1


@pytest.mark.parametrize("driver", ["reference", "generated"])
@pytest.mark.parametrize("fault", ["digest", "excerpt", "source", "quote", "missing_criterion",
    "duplicate_criterion", "verdict", "fixes", "scope", "image", "edited_post", "duplicate_field",
    "long", "empty_detail", "unknown_criterion", "fenced_json",
    "missing_required_fixes", "missing_optional_preferences", "missing_scope",
    "missing_image_consistency", "missing_all_top_level_fields"])
def test_invalid_review_never_becomes_editorial_completion(operator, driver, fault):
    runs, snapshot, _ = setup(operator)
    from agent_lab.model_operation import ModelResponse

    class InvalidGuardian(GuardianSource):
        def invoke(self, request):
            response = super().invoke(request)
            body = json.loads(response.body)
            if fault == "digest": body["draft_digest"] = "0" * 64
            elif fault == "excerpt": body["findings"][0]["excerpt"] = "not in draft"
            elif fault == "source": body["findings"][0]["references"] = [{"source": "missing", "quote": "Synthetic"}]
            elif fault == "quote": body["findings"][0]["references"] = [{"source": "audience", "quote": "fabricated"}]
            elif fault == "missing_criterion": body["findings"].pop()
            elif fault == "duplicate_criterion": body["findings"][0] = body["findings"][1]
            elif fault == "verdict": body["verdict"] = "Changes requested"
            elif fault == "fixes": body["required_fixes"] = ["Change this"]
            elif fault == "scope": body["scope"] = "publication"
            elif fault == "image": body["image_consistency"] = "Reviewed"
            elif fault == "edited_post": body["post"] = "New draft"
            elif fault == "long": body["optional_preferences"] = ["x" * 65536]
            elif fault == "empty_detail": body["findings"][0]["detail"] = " "
            elif fault == "unknown_criterion": body["findings"][0]["criterion"] = "image"
            elif fault.startswith("missing_"):
                fields = ("required_fixes", "optional_preferences", "scope", "image_consistency")
                for field in fields if fault == "missing_all_top_level_fields" else (fault.removeprefix("missing_"),):
                    body.pop(field)
            raw = json.dumps(body)
            if fault == "duplicate_field": raw = raw[:-1] + ',"verdict":"Approved"}'
            if fault == "fenced_json": raw = "```json\n" + raw + "\n```"
            return ModelResponse(body=raw)

    generator, guardian = FixtureSource(), InvalidGuardian()
    initial = ReviewState(snapshot=snapshot, captured_json=canonical(runs.source.load(snapshot)))
    kwargs = dict(state_type=ReviewState, bindings={}, model_operations=operations(generator, guardian))
    runner = (compile_reference(SPEC, **kwargs).plan if driver == "reference"
              else generate_graph(SPEC, **kwargs).candidate)
    result = runner.run(initial, run_id="invalid", log=RunLog(operator[2] / "invalid.jsonl"))
    assert result.terminal == "FAILED_VALIDATION"
    assert result.state.result.post == POST and result.state.review is None
    assert result.used_steps == 2 and len(guardian.requests) == 1


@pytest.mark.parametrize("driver", ["reference", "generated"])
def test_step_budget_prevents_guardian_even_with_generation_allowance(operator, driver):
    runs, snapshot, _ = setup(operator)
    generator, guardian = FixtureSource(), GuardianSource()
    spec = SPEC.model_copy(update={"budget": 1})
    kwargs = dict(state_type=ReviewState, bindings={}, model_operations=operations(generator, guardian))
    runner = (compile_reference(spec, **kwargs).plan if driver == "reference"
              else generate_graph(spec, **kwargs).candidate)
    result = runner.run(ReviewState(snapshot=snapshot, captured_json=canonical(runs.source.load(snapshot))),
                        run_id="limited", log=RunLog(operator[2] / "limited.jsonl"))
    assert result.terminal == "FAILED_BUDGET" and result.used_steps == 1
    assert len(generator.requests) == 1 and not guardian.requests
