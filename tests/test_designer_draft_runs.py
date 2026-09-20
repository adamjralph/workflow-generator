"""Captured Generator runs through the real graph with no live credentials."""
import json
import os
from pathlib import Path

import pytest

from agent_lab.designer.linkedin import DraftState, SPEC, canonical, operation
from agent_lab.generation import generate_graph
from agent_lab.reference import compile_reference
from agent_lab.runlog import RunLog

from agent_lab.designer.draft_runs import DraftRuns
from agent_lab.designer.drafts import DraftSource
from agent_lab.model_operation import ModelResponse
from tests.test_designer_drafts import draft, operator  # noqa: F401


RESULT = {"post": "Make one small change.", "reader": "Builders", "one_point": "Start small",
          "support": [], "limitations": ["No external claims"], "blocked_reason": None}


class Source:
    mode = "fixture"

    def __init__(self, result=RESULT):
        self.result = result
        self.requests = []

    def invoke(self, request):
        self.requests.append(request)
        return ModelResponse(body=json.dumps(self.result), input_tokens=12, output_tokens=8)


def setup(operator, source=None):
    config, folder, evidence = operator
    draft(folder, "old.md")
    capture = DraftSource(config, evidence)
    snapshot = capture.capture()["snapshot"]
    source = source or Source()
    runs = DraftRuns(capture, evidence, source)
    return runs, snapshot, source


def test_generator_uses_exact_capture_and_persists_exchange_before_not_reviewed(operator):
    runs, snapshot, source = setup(operator)
    identity = runs.create_request(snapshot)
    result = runs.run(snapshot, identity["run_request"])
    assert result["status"] == "not_reviewed"
    assert result["result"] == RESULT
    assert result["usage"] == {"input_tokens": 12, "output_tokens": 8,
                               "reasoning_tokens": None, "cache_read_tokens": None}
    assert len(source.requests) == 1
    assert source.requests[0].input_digest == snapshot
    payload = json.loads(source.requests[0].request_json)
    assert payload["input"][0]["role"] == "user"
    assert payload["input"][0]["content"][0]["type"] == "input_text"
    assert json.loads(payload["input"][0]["content"][0]["text"])["selected"]["name"] == "old.md"
    for path in result["evidence"]:
        assert Path(path).is_file()
    assert runs.run(snapshot, identity["run_request"]) == result
    assert len(source.requests) == 1


@pytest.mark.parametrize("driver", ["reference", "generated"])
@pytest.mark.parametrize("change,terminal", [({}, "NOT_REVIEWED"),
    ({"post": None, "blocked_reason": "Need public authorization"}, "BLOCKED"),
    ({"post": "x" * 3001}, "FAILED_VALIDATION"),
    ({"post": "Unsafe — voice"}, "FAILED_VALIDATION"),
    ({"support": [{"claim": "Make one small change.", "source": "missing", "quote": "invented"}]}, "FAILED_VALIDATION"),
    ({"post": None, "blocked_reason": None}, "FAILED_VALIDATION"),
    ({"review": "Approved"}, "FAILED_VALIDATION")])
def test_literal_generator_outcomes_in_both_independent_drivers(operator, driver, change, terminal):
    runs, snapshot, _ = setup(operator)
    captured = runs.source.load(snapshot)
    initial = DraftState(snapshot=snapshot, captured_json=canonical(captured))
    source = Source({**RESULT, **change})
    kwargs = dict(state_type=DraftState, bindings={}, model_operations={"draft_linkedin": operation(source)})
    plan = (compile_reference(SPEC, **kwargs).plan if driver == "reference"
            else generate_graph(SPEC, **kwargs).candidate)
    log = RunLog(operator[2] / "literal.jsonl")
    result = plan.run(initial, run_id="literal", log=log)
    assert result.terminal == terminal
    assert len(source.requests) == 1
    assert result.used_steps == 1
    assert result.state.result is None if terminal == "FAILED_VALIDATION" else result.state.result is not None


def test_restart_after_interrupted_reservation_never_resends(operator):
    class Interrupted(Source):
        def invoke(self, request):
            self.requests.append(request)
            raise SystemExit("simulated process interruption")
    source = Interrupted()
    runs, snapshot, _ = setup(operator, source)
    identity = runs.create_request(snapshot)
    with pytest.raises(SystemExit):
        runs.run(snapshot, identity["run_request"])
    fresh = DraftRuns(DraftSource(operator[0], operator[2]), operator[2], source)
    assert fresh.run(snapshot, identity["run_request"])["status"] == "uncertain"
    assert len(source.requests) == 1


def test_run_loads_immutable_capture_not_current_source_or_profiles(operator):
    runs, snapshot, source = setup(operator)
    identity = runs.create_request(snapshot)
    for path in operator[0].parent.rglob("*"):
        if path.is_file():
            path.write_text("CHANGED AFTER CAPTURE")
    result = runs.run(snapshot, identity["run_request"])
    assert result["status"] == "not_reviewed"
    assert "CHANGED AFTER CAPTURE" not in source.requests[0].request_json


def test_opaque_identity_is_bound_to_exact_capture_before_any_invocation(operator):
    runs, snapshot, source = setup(operator)
    identity = runs.create_request(snapshot)
    draft(operator[1], "older.md", "processed: false\ndate_created: 2025-01-01")
    other = runs.source.capture()["snapshot"]
    with pytest.raises(ValueError, match="match capture"):
        runs.run(other, identity["run_request"])
    assert source.requests == []


@pytest.mark.parametrize("phase", ["reservation", "exchange", "audit", "receipt"])
def test_filesystem_failure_cannot_complete_or_resend(operator, monkeypatch, phase):
    runs, snapshot, source = setup(operator)
    identity = runs.create_request(snapshot)
    link = os.link
    invoked = False
    def failing_link(src, dst, *args, **kwargs):
        nonlocal invoked
        name = Path(dst).name
        hit = ((phase == "reservation" and name == "attempt.json")
               or (phase == "exchange" and len(name) == 69 and name.endswith(".json"))
               or (phase == "audit" and len(name) == 70 and name.endswith(".jsonl"))
               or (phase == "receipt" and name == "receipt.json"))
        if hit:
            invoked = True
            raise OSError("SECRET_DISK_FAILURE")
        return link(src, dst, *args, **kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(os, "link", failing_link)
        result = runs.run(snapshot, identity["run_request"])
    assert invoked
    assert result["status"] == "uncertain"
    assert not result["succeeded"] and result["result"] is None
    assert "SECRET_DISK_FAILURE" not in json.dumps(result)
    calls = len(source.requests)
    assert calls == (0 if phase == "reservation" else 1)
    assert runs.run(snapshot, identity["run_request"])["status"] == "uncertain"
    assert len(source.requests) == calls


def test_captured_generator_replays_exact_exchange_independently_offline(operator):
    from agent_lab.conformance import check_conformance
    from agent_lab.model_operation import ModelRequest
    runs, snapshot, _ = setup(operator)
    identity = runs.create_request(snapshot)
    view = runs.run(snapshot, identity["run_request"])
    exchange_path = next(Path(p) for p in view["evidence"] if len(Path(p).name) == 69)
    exchange = json.loads(exchange_path.read_bytes())
    recorded_request = ModelRequest.model_validate(exchange["request"])
    assert exchange["request_digest"] == recorded_request.digest
    assert exchange["limits"]["attempts"] == 1
    class Recorded:
        mode = "recorded"
        def __init__(self):
            self.used = False
        def invoke(self, request):
            assert not self.used and request == recorded_request
            self.used = True
            return ModelResponse.model_validate(exchange["response"])
    reference, candidate = Recorded(), Recorded()
    captured = runs.source.load(snapshot)
    initial = DraftState(snapshot=snapshot, captured_json=canonical({key: captured[key] for key in
        ("selected", "guidance", "models", "instruction_version")}))
    graph = generate_graph(SPEC, state_type=DraftState, bindings={},
                           model_operations={"draft_linkedin": operation(candidate)}).candidate
    report = check_conformance(SPEC, graph, state_type=DraftState, bindings={},
        model_operations={"draft_linkedin": operation(reference)}, cases={"captured": initial},
        evidence_dir=operator[2] / "offline")
    assert report.passed and reference.used and candidate.used
    assert report.outputs[0].terminal == "NOT_REVIEWED"
    assert report.outputs[0].state.result.post == "Make one small change."


def test_real_codex_adapter_and_graph_with_injected_transport(operator):
    from agent_lab.designer.codex import CodexSource
    from tests.test_designer_codex import credentials
    config, folder, evidence = operator
    draft(folder, "old.md")
    (config.parent / "generator.yaml").write_text("model:\n  provider: openai-codex\n  default: captured-model\n")
    auth = config.parent / "auth.json"
    credentials(auth)
    original = auth.read_bytes()
    calls = []
    async def transport(body, headers, deadline):
        calls.append(json.loads(body))
        assert calls[-1]["model"] == "captured-model"
        assert calls[-1]["input"][0]["content"][0]["type"] == "input_text"
        assert calls[-1]["tools"] == []
        payload = {"type": "response.completed", "response": {"status": "completed",
            "id": "request-1", "model": "resolved-model", "output": [{"type": "message",
            "role": "assistant", "status": "completed", "content": [{"type": "output_text",
            "text": json.dumps(RESULT)}]}]}}
        yield ("data: " + json.dumps(payload) + "\n\n").encode()
    capture = DraftSource(config, evidence)
    snapshot = capture.capture()["snapshot"]
    runs = DraftRuns(capture, evidence, CodexSource(auth, transport=transport))
    identity = runs.create_request(snapshot)
    result = runs.run(snapshot, identity["run_request"])
    assert result["status"] == "not_reviewed"
    assert result["usage"] == dict.fromkeys(("input_tokens", "output_tokens", "reasoning_tokens", "cache_read_tokens"))
    assert len(calls) == 1 and auth.read_bytes() == original


@pytest.mark.parametrize("code,status,http_status", [
    ("credentials_unavailable", "failed", None), ("provider_rejected", "failed", 403),
    ("invalid_response", "failed", None), ("deadline_exceeded", "uncertain", None)])
def test_typed_sanitized_source_failure_survives_evidence_and_duplicate(operator, code, status, http_status):
    from agent_lab.designer.codex import CodexError, CodexUncertain
    class FailedSource(Source):
        def invoke(self, request):
            self.requests.append(request)
            error = CodexUncertain if status == "uncertain" else CodexError
            raise error("SECRET_PROVIDER_TEXT", code=code, provider_status=http_status)
    runs, snapshot, source = setup(operator, FailedSource())
    identity = runs.create_request(snapshot)
    view = runs.run(snapshot, identity["run_request"])
    assert view["status"] == status
    assert view["failure"] == {"status": status, "code": code, "provider_status": http_status}
    exchange = next(Path(p) for p in view["evidence"] if len(Path(p).name) == 69)
    record = json.loads(exchange.read_bytes())
    assert record["failure"] == view["failure"]
    assert "SECRET_PROVIDER_TEXT" not in exchange.read_text() + json.dumps(view)
    assert runs.run(snapshot, identity["run_request"]) == view
    assert len(source.requests) == 1


def test_failed_receipt_directory_sync_never_leaves_success_for_duplicate(operator, monkeypatch):
    runs, snapshot, source = setup(operator)
    identity = runs.create_request(snapshot)
    receipt = operator[2] / "draft-runs" / identity["run_request"] / "receipt.json"
    fsync = os.fsync
    def fail_receipt_sync(fd):
        if receipt.exists():
            raise OSError("directory sync failed after receipt link")
        return fsync(fd)
    with monkeypatch.context() as patch:
        patch.setattr(os, "fsync", fail_receipt_sync)
        assert runs.run(snapshot, identity["run_request"])["status"] == "uncertain"
    assert runs.run(snapshot, identity["run_request"])["status"] == "uncertain"
    assert len(source.requests) == 1


def test_receipt_rechecks_exchange_integrity_before_duplicate_success(operator):
    runs, snapshot, source = setup(operator)
    identity = runs.create_request(snapshot)
    result = runs.run(snapshot, identity["run_request"])
    exchange = next(Path(p) for p in result["evidence"] if len(Path(p).name) == 69)
    exchange.write_text("corrupt")
    assert runs.run(snapshot, identity["run_request"])["status"] == "uncertain"
    assert len(source.requests) == 1
