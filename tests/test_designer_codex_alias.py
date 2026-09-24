"""Picker-only Codex context variants must retain provenance but use wire slugs."""
import json

import pytest

from agent_lab.designer.linkedin import DraftState, canonical, prepare
from agent_lab.designer import linkedin
from agent_lab.designer.draft_checks import DraftChecks
from agent_lab.designer.draft_runs import DraftRuns
from agent_lab.designer.drafts import DraftSource
from agent_lab.model_operation import ModelResponse
from tests.test_designer_draft_runs import Source, setup
from tests.test_designer_drafts import draft, operator  # noqa: F401
from tests.test_designer_draft_run_server import POST, RESULT
from tests.test_designer_review_server import FixtureSource, GuardianSource


def state(model: str, provider: str = "openai-codex") -> DraftState:
    captured = {"models": [{"role": "generator", "provider": provider, "model": model}],
                "selected": {"name": "sample.md", "text": "sample"}, "guidance": []}
    return DraftState(snapshot="a" * 64, captured_json=canonical(captured))


@pytest.mark.parametrize("configured,wire", [
    ("gpt-6-sol-900k", "gpt-6-sol"),
    ("gpt-6-astra-900k", "gpt-6-astra"),
    ("gpt-5.4-900k", "gpt-5.4"),
    ("gpt-daybreak-blue-latest-900k", "gpt-daybreak-blue-latest"),
    ("gpt-6-terra-2026-09-22-900k", "gpt-6-terra-2026-09-22"),
    ("gpt-5.6-luna-2026-07-09-900k", "gpt-5.6-luna-2026-07-09"),
    ("gpt-6-sol", "gpt-6-sol"),
])
def test_prepared_request_wire_slug_and_captured_identity(configured, wire):
    initial = state(configured)
    request = prepare(initial)
    assert json.loads(initial.captured_json)["models"][0]["model"] == configured
    assert json.loads(request.request_json)["model"] == wire
    assert request.input_digest == initial.snapshot


@pytest.mark.parametrize("configured", ["gpt-5.5-900k", "gpt-5.4-mini-900k",
    "gpt-6-sol-2026-99-99-900k", "gpt-6-sol-pro-900k", "gpt-6-sol-900k-900k"])
def test_ineligible_context_variant_fails_before_request(configured):
    with pytest.raises(ValueError, match="Unsupported Codex context variant"):
        prepare(state(configured))


def test_non_codex_model_is_never_mapped():
    initial = state("gpt-6-sol-900k", provider="fixture-provider")
    assert json.loads(prepare(initial).request_json)["model"] == "gpt-6-sol-900k"


def test_prepared_instructions_demand_literal_public_copy_support():
    request = prepare(state("gpt-6-sol"))
    instructions = json.loads(request.request_json)["instructions"]
    assert "claim must be a verbatim contiguous substring of post" in instructions
    assert "quote must be a verbatim contiguous substring of the named source" in instructions
    assert "If a claim cannot be copied exactly from the finished post" in instructions
    assert "do not paraphrase" in instructions
    assert request.operation_version == "3"


def test_pending_v2_pair_cannot_send_after_instruction_change(operator, monkeypatch):
    config, folder, evidence = operator
    draft(folder, "old.md")
    capture = DraftSource(config, evidence)
    snapshot = capture.capture()["snapshot"]
    generator, guardian = FixtureSource(), GuardianSource()
    runs = DraftRuns(capture, evidence, generator, guardian_source=guardian)
    with monkeypatch.context() as patch:
        patch.setattr(linkedin, "VERSION", "2")
        pending = runs.create_request(snapshot)
    result = runs.run(snapshot, pending["run_request"])
    assert result["status"] == "failed"
    assert result["failure"]["code"] == "preflight_failed"
    assert not generator.requests and not guardian.requests


@pytest.mark.parametrize("old_version", ["1", "2"])
def test_pending_old_guardian_parser_contract_cannot_send(operator, monkeypatch, old_version):
    from agent_lab.designer import linkedin_review

    config, folder, evidence = operator
    draft(folder, "old.md")
    capture = DraftSource(config, evidence)
    snapshot = capture.capture()["snapshot"]
    generator, guardian = FixtureSource(), GuardianSource()
    runs = DraftRuns(capture, evidence, generator, guardian_source=guardian)
    with monkeypatch.context() as patch:
        patch.setattr(linkedin_review, "VERSION", old_version)
        pending = runs.create_request(snapshot)
    result = runs.run(snapshot, pending["run_request"])
    assert result["status"] == "failed"
    assert result["failure"]["code"] == "preflight_failed"
    assert not generator.requests and not guardian.requests


def test_completed_pair_remains_readable_after_guardian_version_change(operator, monkeypatch):
    from agent_lab.designer import linkedin_review

    config, folder, evidence = operator
    draft(folder, "old.md")
    capture = DraftSource(config, evidence)
    snapshot = capture.capture()["snapshot"]
    generator, guardian = FixtureSource(), GuardianSource()
    runs = DraftRuns(capture, evidence, generator, guardian_source=guardian)
    pending = runs.create_request(snapshot)
    completed = runs.run(snapshot, pending["run_request"])
    assert completed["status"] == "completed"
    with monkeypatch.context() as patch:
        patch.setattr(linkedin_review, "VERSION", "1")
        assert runs.run(snapshot, pending["run_request"]) == completed
    assert len(generator.requests) == len(guardian.requests) == 1


@pytest.mark.parametrize("claim,completed", [
    ("A synthetic post.", True),
    ("A paraphrased post.", False),
])
def test_exact_source_quote_but_paraphrased_post_claim_stops_before_review(operator, claim, completed):
    config, folder, evidence = operator
    draft(folder, "old.md")
    capture = DraftSource(config, evidence)
    snapshot = capture.capture()["snapshot"]

    class SupportedFixture:
        mode = "fixture"
        def __init__(self):
            self.requests = []
        def invoke(self, request):
            self.requests.append(request)
            result = {**RESULT, "support": [{"claim": claim, "source": "old.md",
                                              "quote": "Synthetic body."}]}
            return ModelResponse(body=json.dumps(result), input_tokens=17, output_tokens=9)

    generator, guardian = SupportedFixture(), GuardianSource()
    runs = DraftRuns(capture, evidence, generator, guardian_source=guardian)
    request = runs.create_request(snapshot)
    result = runs.run(snapshot, request["run_request"])
    assert len(generator.requests) == 1
    assert len(guardian.requests) == int(completed)
    assert result["status"] == ("completed" if completed else "failed")
    assert result["generation_attempts"] == (2 if completed else 1)
    assert runs.run(snapshot, request["run_request"]) == result
    assert len(generator.requests) == 1 and len(guardian.requests) == int(completed)
    checked = DraftChecks(capture, evidence).check(snapshot, request["run_request"])
    assert checked["passed"] is completed
    assert checked["model_calls"] == checked["auth_requests"] == 0
    if not completed:
        assert result["failure"]["code"] == "invalid_output"
        assert checked["findings"][0]["code"] == "invalid_recording"


def test_run_evidence_keeps_configured_and_wire_model_without_extra_calls(operator):
    config, folder, evidence = operator
    draft(folder, "old.md")
    profile = config.parent / "generator.yaml"
    profile.write_text("model:\n  provider: openai-codex\n  default: gpt-6-sol-900k\n")
    capture = DraftSource(config, evidence)
    snapshot = capture.capture()["snapshot"]
    assert capture.load(snapshot)["models"][0]["model"] == "gpt-6-sol-900k"
    source = Source()
    runs = DraftRuns(capture, evidence, source)
    identity = runs.create_request(snapshot)
    result = runs.run(snapshot, identity["run_request"])
    assert len(source.requests) == 1
    assert json.loads(source.requests[0].request_json)["model"] == "gpt-6-sol"
    assert result["status"] == "not_reviewed"
    attempt = json.loads((evidence / "draft-runs" / identity["run_request"] / "attempt.json").read_text())
    assert json.loads(attempt["request"]["request_json"])["model"] == "gpt-6-sol"
    assert attempt["request_digest"] == source.requests[0].digest
    assert capture.load(snapshot)["models"][0]["model"] == "gpt-6-sol-900k"


def test_stale_pending_pair_is_rejected_before_either_role(operator, monkeypatch):
    config, folder, evidence = operator
    draft(folder, "old.md")
    capture = DraftSource(config, evidence)
    snapshot = capture.capture()["snapshot"]
    generator, guardian = FixtureSource(), GuardianSource()
    runs = DraftRuns(capture, evidence, generator, guardian_source=guardian)
    with monkeypatch.context() as patch:
        patch.setattr(linkedin, "VERSION", "1")
        pending = runs.create_request(snapshot)
    result = runs.run(snapshot, pending["run_request"])
    assert result["status"] == "failed"
    assert result["failure"]["code"] == "preflight_failed"
    assert not generator.requests and not guardian.requests


def test_stale_pending_legacy_generator_does_not_send(operator, monkeypatch):
    config, folder, evidence = operator
    draft(folder, "old.md")
    capture = DraftSource(config, evidence)
    snapshot = capture.capture()["snapshot"]
    generator = Source()
    old = DraftRuns(capture, evidence, generator)
    with monkeypatch.context() as patch:
        patch.setattr(linkedin, "VERSION", "1")
        pending = old.create_request(snapshot)
    paired = DraftRuns(capture, evidence, generator, guardian_source=GuardianSource())
    result = paired.run(snapshot, pending["run_request"])
    assert result["status"] == "failed"
    assert result["failure"]["code"] == "preflight_failed"
    assert not generator.requests


def test_unversioned_historical_pending_generator_does_not_send(operator):
    config, folder, evidence = operator
    draft(folder, "old.md")
    capture = DraftSource(config, evidence)
    snapshot = capture.capture()["snapshot"]
    generator = Source()
    runs = DraftRuns(capture, evidence, generator)
    pending = runs.create_request(snapshot)
    path = evidence / "draft-runs" / pending["run_request"] / "request.json"
    historic = json.loads(path.read_bytes())
    assert historic.pop("operation_version") == linkedin.VERSION
    path.write_bytes(canonical(historic).encode())  # synthetic pre-version format
    result = runs.run(snapshot, pending["run_request"])
    assert result["status"] == "failed"
    assert result["failure"]["code"] == "preflight_failed"
    assert not generator.requests


def test_completed_legacy_receipt_remains_readable_after_version_change(operator, monkeypatch):
    config, folder, evidence = operator
    draft(folder, "old.md")
    capture = DraftSource(config, evidence)
    snapshot = capture.capture()["snapshot"]
    generator = Source()
    runs = DraftRuns(capture, evidence, generator)
    pending = runs.create_request(snapshot)
    original = runs.run(snapshot, pending["run_request"])
    assert original["status"] == "not_reviewed"
    assert len(generator.requests) == 1
    with monkeypatch.context() as patch:
        patch.setattr(linkedin, "VERSION", str(int(linkedin.VERSION) + 1))
        assert runs.run(snapshot, pending["run_request"]) == original
    assert len(generator.requests) == 1


def test_corrected_alias_completed_pair_replays_without_provider_calls(operator):
    config, folder, evidence = operator
    draft(folder, "old.md")
    (config.parent / "generator.yaml").write_text(
        "model:\n  provider: openai-codex\n  default: gpt-6-sol-900k\n")
    capture = DraftSource(config, evidence)
    snapshot = capture.capture()["snapshot"]
    generator, guardian = FixtureSource(), GuardianSource("Changes requested")
    runs = DraftRuns(capture, evidence, generator, guardian_source=guardian)
    pending = runs.create_request(snapshot)
    result = runs.run(snapshot, pending["run_request"])
    assert result["status"] == "completed"
    assert len(generator.requests) == len(guardian.requests) == 1
    assert json.loads(generator.requests[0].request_json)["model"] == "gpt-6-sol"
    checked = DraftChecks(capture, evidence).check(snapshot, pending["run_request"])
    assert checked["passed"] and checked["completed_cases"] == ["completed_pair"]
    assert checked["model_calls"] == checked["auth_requests"] == 0
