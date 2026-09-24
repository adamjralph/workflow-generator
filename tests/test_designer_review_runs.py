"""Durable two-attempt captured runs, exercised through the public run seam."""
import pytest
import json
from pathlib import Path

from agent_lab.designer.draft_runs import DraftRuns
from agent_lab.designer import linkedin_review
from tests.test_designer_drafts import operator  # noqa: F401
from tests.test_designer_draft_runs import setup
from tests.test_designer_review_server import GuardianSource
from tests.test_designer_draft_run_server import FixtureSource, POST


def test_pair_reserves_before_each_send_and_binds_completed_receipt(operator):
    old, snapshot, _ = setup(operator)
    generator, guardian = FixtureSource(), GuardianSource("Changes requested")
    runs = DraftRuns(old.source, operator[2], generator, guardian_source=guardian)
    identity = runs.create_request(snapshot)
    result = runs.run(snapshot, identity["run_request"])
    assert result["status"] == "completed" and result["succeeded"]
    assert result["result"]["post"] == POST
    assert result["review"]["verdict"] == "Changes requested"
    assert result["used_steps"] == result["generation_attempts"] == 2
    assert len(generator.requests) == len(guardian.requests) == 1
    receipt = json.loads(Path(result["evidence"][-1]).read_bytes())
    assert receipt["format_version"] == 2
    assert receipt["draft_digest"] == result["draft_digest"]
    assert receipt["review_digest"] and len(receipt["exchanges"]) == 2
    assert len(receipt["digests"]) >= 7
    assert runs.run(snapshot, identity["run_request"]) == result


def test_guardian_request_requires_bare_json_and_exact_named_source_quotes(operator):
    old, snapshot, _ = setup(operator)
    generator, guardian = FixtureSource(), GuardianSource()
    runs = DraftRuns(old.source, operator[2], generator, guardian_source=guardian)
    identity = runs.create_request(snapshot)
    assert runs.run(snapshot, identity["run_request"])["status"] == "completed"
    request = guardian.requests[0]
    assert request.operation_version == linkedin_review.VERSION
    instructions = json.loads(request.request_json)["messages"][0]["content"]
    assert "no Markdown code fences" in instructions
    assert "no preamble or trailing commentary" in instructions
    assert "copy source exactly from selected.name or guidance[].name" in instructions
    assert "contiguous substring of that named item's text" in instructions
    assert "use references: []" in instructions
    assert "include every top-level field" in instructions
    assert "required_fixes and optional_preferences must be arrays" in instructions
    assert "scope must be 'copy-only'" in instructions
    assert "image_consistency must be 'Image consistency not reviewed.'" in instructions


def test_pending_previous_guardian_prompt_version_cannot_send(operator, monkeypatch):
    old, snapshot, _ = setup(operator)
    generator, guardian = FixtureSource(), GuardianSource()
    runs = DraftRuns(old.source, operator[2], generator, guardian_source=guardian)
    with monkeypatch.context() as patch:
        patch.setattr(linkedin_review, "VERSION", "4")
        pending = runs.create_request(snapshot)
    result = runs.run(snapshot, pending["run_request"])
    assert result["status"] == "failed"
    assert result["failure"]["code"] == "preflight_failed"
    assert not generator.requests and not guardian.requests


def test_completed_v4_pair_receipt_reads_under_v5_without_new_calls(operator, monkeypatch):
    old, snapshot, _ = setup(operator)
    generator, guardian = FixtureSource(), GuardianSource()
    runs = DraftRuns(old.source, operator[2], generator, guardian_source=guardian)
    with monkeypatch.context() as patch:
        patch.setattr(linkedin_review, "VERSION", "4")
        nodes = list(linkedin_review.SPEC.nodes)
        nodes[1] = nodes[1].model_copy(update={"operation_version": "4"})
        patch.setattr(linkedin_review, "SPEC", linkedin_review.SPEC.model_copy(update={"nodes": tuple(nodes)}))
        pending = runs.create_request(snapshot)
        completed = runs.run(snapshot, pending["run_request"])
    assert completed["status"] == "completed"
    receipt_path = Path(completed["evidence"][-1])
    receipt_before = receipt_path.read_bytes()
    assert runs.run(snapshot, pending["run_request"]) == completed
    assert receipt_path.read_bytes() == receipt_before
    assert len(generator.requests) == len(guardian.requests) == 1


@pytest.mark.parametrize("phase", ["generator", "guardian"])
def test_restart_after_incomplete_role_never_resumes_or_sends(operator, phase):
    old, snapshot, _ = setup(operator)

    class InterruptedGenerator(FixtureSource):
        def invoke(self, request):
            super().invoke(request)
            raise SystemExit("simulated interruption")

    class InterruptedGuardian(GuardianSource):
        def invoke(self, request):
            super().invoke(request)
            raise SystemExit("simulated interruption")

    generator = InterruptedGenerator() if phase == "generator" else FixtureSource()
    guardian = InterruptedGuardian() if phase == "guardian" else GuardianSource()
    runs = DraftRuns(old.source, operator[2], generator, guardian_source=guardian)
    identity = runs.create_request(snapshot)
    with pytest.raises(SystemExit):
        runs.run(snapshot, identity["run_request"])
    restarted = DraftRuns(old.source, operator[2], generator, guardian_source=guardian)
    assert restarted.run(snapshot, identity["run_request"])["status"] == "uncertain"
    assert len(generator.requests) == 1
    assert len(guardian.requests) == (1 if phase == "guardian" else 0)


@pytest.mark.parametrize("phase", ["reservation", "exchange", "audit", "receipt"])
def test_guardian_storage_failures_preserve_partial_evidence_never_retry(operator, monkeypatch, phase):
    import os
    old, snapshot, _ = setup(operator)
    generator, guardian = FixtureSource(), GuardianSource()
    runs = DraftRuns(old.source, operator[2], generator, guardian_source=guardian)
    identity = runs.create_request(snapshot)
    link = os.link
    hit = False

    def fail(src, dst, *args, **kwargs):
        nonlocal hit
        name = Path(dst).name
        target = ((phase == "reservation" and name == "guardian-attempt.json")
                  or (phase == "exchange" and guardian.requests and len(name) == 69)
                  or (phase == "audit" and name.endswith(".jsonl") and len(name) == 70)
                  or (phase == "receipt" and name == "receipt.json"))
        if target:
            hit = True
            raise OSError("SECRET_STORAGE_FAILURE")
        return link(src, dst, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(os, "link", fail)
        result = runs.run(snapshot, identity["run_request"])
    assert hit and result["status"] == "uncertain" and not result["succeeded"]
    assert result["result"]["post"] == POST
    assert "SECRET_STORAGE_FAILURE" not in json.dumps(result)
    assert len(guardian.requests) == (0 if phase == "reservation" else 1)
    assert runs.run(snapshot, identity["run_request"])["status"] == "uncertain"
    assert len(generator.requests) == 1


def test_missing_generator_audit_event_stops_before_guardian(operator, monkeypatch):
    old, snapshot, _ = setup(operator)
    generator, guardian = FixtureSource(), GuardianSource()
    runs = DraftRuns(old.source, operator[2], generator, guardian_source=guardian)
    identity = runs.create_request(snapshot)
    original_open = Path.open

    def lost_append(path, mode="r", *args, **kwargs):
        if path.name == "run.jsonl" and mode == "a+":
            return original_open(Path("/dev/null"), mode, *args, **kwargs)
        return original_open(path, mode, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "open", lost_append)
        result = runs.run(snapshot, identity["run_request"])
    assert result["status"] == "uncertain" and not result["succeeded"]
    assert len(generator.requests) == 1 and not guardian.requests
    assert runs.run(snapshot, identity["run_request"])["status"] == "uncertain"


def test_legacy_requests_and_receipts_are_never_upgraded_into_reviewed_pairs(operator):
    old, snapshot, generator = setup(operator)
    first = old.create_request(snapshot)
    saved = old.run(snapshot, first["run_request"])
    unclaimed = old.create_request(snapshot)
    guardian = GuardianSource()
    paired = DraftRuns(old.source, operator[2], generator, guardian_source=guardian)
    assert paired.run(snapshot, first["run_request"]) == saved
    assert paired.run(snapshot, unclaimed["run_request"])["status"] == "not_reviewed"
    assert not guardian.requests


def test_rerun_warning_survives_restart_without_changing_source_selection(operator):
    old, snapshot, _ = setup(operator)
    runs = DraftRuns(old.source, operator[2], FixtureSource(), guardian_source=GuardianSource())
    first = runs.create_request(snapshot)
    assert not first["previously_attempted"]
    assert not runs.create_request(snapshot)["previously_attempted"]
    runs.run(snapshot, first["run_request"])
    fresh = DraftRuns(old.source, operator[2], FixtureSource(), guardian_source=GuardianSource())
    assert fresh.create_request(snapshot)["previously_attempted"]
    assert old.source.capture()["snapshot"] == snapshot


def test_changed_vertex_routing_after_request_requires_new_explicit_request(operator):
    from agent_lab.designer.vertex import VertexSource
    old, snapshot, generator = setup(operator)
    (operator[0].parent / "guardian.yaml").write_text("model:\n  provider: vertex\n  default: exact-guardian\n")
    snapshot = old.source.capture()["snapshot"]
    adc = operator[0].parent / "unused-adc.json"
    first = DraftRuns(old.source, operator[2], generator,
        guardian_source=VertexSource(adc, "approved-project"))
    identity = first.create_request(snapshot)
    changed = DraftRuns(old.source, operator[2], generator,
        guardian_source=VertexSource(adc, "different-project"))
    result = changed.run(snapshot, identity["run_request"])
    assert result["status"] == "failed"
    assert result["failure"]["code"] == "preflight_failed" and not generator.requests
    assert identity["execution_options"]["guardian"]["project"] == "approved-project"


@pytest.mark.parametrize("driver", ["reference", "generated"])
def test_both_real_adapters_reserve_before_auth_and_generation_and_preserve_sources(operator, driver):
    from agent_lab.designer.codex import CodexSource
    from agent_lab.designer.vertex import VertexSource, TOKEN_ENDPOINT
    from agent_lab.designer.drafts import DraftSource
    from tests.test_designer_drafts import draft
    from tests.test_designer_codex import credentials, completed
    from tests.test_designer_vertex import CREDENTIALS, REPLY, TOKEN
    from agent_lab.model_operation import ModelRequest
    from agent_lab.designer.linkedin import canonical
    from tests.test_designer_draft_run_server import RESULT
    from urllib.parse import parse_qs

    config, folder, evidence = operator
    for role, provider in [("generator", "openai-codex"), ("guardian", "vertex")]:
        (config.parent / (role + ".yaml")).write_text(f"model:\n  provider: {provider}\n  default: exact-{role}\n")
    draft(folder, "old.md")
    auth = config.parent / "codex.json"
    credentials(auth)
    adc = config.parent / "adc.json"
    adc.write_text(json.dumps(CREDENTIALS))
    capture = DraftSource(config, evidence)
    snapshot = capture.capture()["snapshot"]
    originals = {p: p.read_bytes() for p in config.parent.rglob("*") if p.is_file()}
    calls = []
    review_fixture = GuardianSource()
    run_directory = None

    async def codex_transport(body, headers, deadline):
        reservation = json.loads((run_directory / "attempt.json").read_bytes())
        assert reservation["ordinal"] == 1 and reservation["limits"]["attempts"] == 2
        assert reservation["request"]["request_json"].encode() == body
        assert json.loads(body)["model"] == "exact-generator"
        calls.append("generator")
        yield completed(output=[{"type": "message", "role": "assistant", "status": "completed",
            "content": [{"type": "output_text", "text": json.dumps(RESULT)}]}])

    async def vertex_transport(url, body, headers, deadline):
        reservation = json.loads((run_directory / "guardian-attempt.json").read_bytes())
        assert reservation["ordinal"] == 2
        events = (run_directory / "run.jsonl").read_text().splitlines()
        assert len(events) == 1 and json.loads(events[0])["detail"]["used_steps"] == 1
        if url == TOKEN_ENDPOINT:
            assert calls == ["generator"]
            assert parse_qs(body.decode())["grant_type"] == ["refresh_token"]
            calls.append("auth")
            yield json.dumps({"access_token": TOKEN, "token_type": "Bearer", "expires_in": 3600}).encode()
        else:
            assert calls == ["generator", "auth"]
            calls.append("guardian")
            assert reservation["request"]["request_json"].encode() == body
            assert json.loads(body)["model"] == "exact-guardian"
            request = ModelRequest.model_validate(reservation["request"])
            reviewed = review_fixture.invoke(request)
            yield canonical({**REPLY, "choices": [{"index": 0, "finish_reason": "stop",
                "message": {"role": "assistant", "content": reviewed.body}}]}).encode()

    generator = CodexSource(auth, transport=codex_transport)
    guardian = VertexSource(adc, "fixture-project", transport=vertex_transport)
    runs = DraftRuns(capture, evidence, generator, guardian_source=guardian)
    identity = runs.create_request(snapshot)
    run_directory = evidence / "draft-runs" / identity["run_request"]
    if driver == "generated":
        result = runs.run(snapshot, identity["run_request"])
        assert result["status"] == "completed"
        assert result["auth_requests"] == 1 and result["generation_attempts"] == 2
        assert result["role_usage"]["guardian"]["reasoning_tokens"] == 3
        assert runs.run(snapshot, identity["run_request"]) == result
    else:
        from agent_lab.designer.draft_runs import Evidence, AttemptBudget, AttemptSource
        from agent_lab.designer.linkedin_review import ReviewState, SPEC, operations
        from agent_lab.reference import compile_reference
        from agent_lab.runlog import RunLog
        store, budget = Evidence(run_directory), AttemptBudget()
        store.publish("run.jsonl", b"")
        reserved_generator = AttemptSource(generator, store, identity, budget)
        reserved_guardian = AttemptSource(guardian, store, identity, budget)
        compiled = compile_reference(SPEC, state_type=ReviewState, bindings={},
            model_operations=operations(reserved_generator, reserved_guardian))
        result = compiled.plan.run(ReviewState(snapshot=snapshot, captured_json=canonical(capture.load(snapshot))),
            run_id=identity["run_request"], log=RunLog(run_directory / "run.jsonl"))
        assert result.terminal == "COMPLETED" and result.used_steps == 2
        assert result.state.result.post == POST and result.state.review.verdict == "Approved"
        assert reserved_guardian.response.auth_requests == 1
        assert reserved_guardian.response.reasoning_tokens == 3
        assert budget.operations == ["draft_linkedin", "review_linkedin"]
        request = ModelRequest.model_validate(json.loads(store.read("guardian-attempt.json"))["request"])
        with pytest.raises(ValueError, match="Role attempt exhausted"):
            reserved_guardian.invoke(request)
        with pytest.raises(ValueError, match="allowance exhausted"):
            AttemptSource(guardian, store, identity, budget).invoke(request)
    assert calls == ["generator", "auth", "guardian"]
    assert all(p.read_bytes() == value for p, value in originals.items())
    serialized = b"".join(p.read_bytes() for p in run_directory.iterdir() if p.is_file())
    assert TOKEN.encode() not in serialized and CREDENTIALS["refresh_token"].encode() not in serialized
