"""Ticket 22: real HTTP and drivers; fixture sources only, no live calls."""
import hashlib
import json
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from agent_lab.model_operation import ModelResponse
from tests.test_designer_drafts import draft, operator  # noqa: F401
from tests.test_designer_draft_run_server import FixtureSource, POST, RESULT, capture, post
from tests.test_designer_server import running_server

CRITERIA = ("brand_voice", "linkedin_fit", "strong_hook", "aida", "source_coherent_cta",
            "supported_claims", "privacy", "reader_fit", "one_point_clarity", "current_positioning")
DETAIL = '<img src=x onerror="window.injected=true"> Fixture finding.'


class GuardianSource:
    mode = "fixture"

    def __init__(self, verdict="Approved", outcome=None, entered=None, release=None):
        self.verdict, self.outcome = verdict, outcome
        self.entered, self.release = entered, release
        self.requests = []
        self.review = None

    def invoke(self, request):
        self.requests.append(request)
        if self.entered:
            self.entered.set()
        if self.release:
            assert self.release.wait(5)
        if self.outcome == "timeout":
            raise TimeoutError("SECRET_PROVIDER_FAILURE")
        if self.outcome == "exception":
            raise RuntimeError("SECRET_PROVIDER_FAILURE")
        payload = json.loads(json.loads(request.request_json)["messages"][1]["content"])
        assert payload["draft"] == {"post": POST, "digest": hashlib.sha256(POST.encode()).hexdigest()}
        assert payload["selected"]["text"] and payload["guidance"]
        status = {"Approved": "pass", "Changes requested": "changes_requested", "Blocked": "blocked"}[self.verdict]
        self.review = {
            "draft_digest": payload["draft"]["digest"], "verdict": self.verdict,
            "findings": [{"criterion": criterion, "status": status if i == 0 else "pass",
                          "detail": DETAIL, "excerpt": POST, "references": []}
                         for i, criterion in enumerate(CRITERIA)],
            "required_fixes": [] if status == "pass" else ["Clarify the opening."],
            "optional_preferences": ["Consider a shorter ending."], "scope": "copy-only",
            "image_consistency": "Image consistency not reviewed.",
        }
        if self.outcome == "digest":
            self.review["draft_digest"] = "0" * 64
        return ModelResponse(body="not JSON" if self.outcome == "invalid" else json.dumps(self.review),
                             input_tokens=31, output_tokens=23, auth_requests=1)


@pytest.mark.parametrize("verdict", ["Approved", "Changes requested", "Blocked"])
def test_http_completed_pair_exact_draft_usage_duplicate_and_new_run(operator, verdict):
    config, folder, evidence = operator
    selected = draft(folder, "old.md")
    original = selected.read_bytes()
    generator, guardian = FixtureSource(), GuardianSource(verdict)
    with running_server(evidence, draft_config=config, draft_model_source=generator,
                        guardian_model_source=guardian) as server:
        _, captured = post(server, "/api/drafts/capture", {})
        identity = {key: captured[key] for key in ("snapshot", "run_request")}
        assert not generator.requests and not guardian.requests
        status, result = post(server, "/api/drafts/run", identity)
        assert status == 200 and result["status"] == "completed" and result["succeeded"]
        assert result["result"] == RESULT and result["review"] == guardian.review
        payload = json.loads(json.loads(guardian.requests[0].request_json)["messages"][1]["content"])
        assert payload["selected"] == captured["selected"]
        assert payload["guidance"] == [
            {key: item[key] for key in ("name", "digest", "text")} for item in captured["guidance"]]
        # Filesystem provenance is local, not sent to either provider.
        assert all("path" not in item for item in payload["guidance"])
        assert result["draft_digest"] == hashlib.sha256(POST.encode()).hexdigest()
        assert result["used_steps"] == result["generation_attempts"] == 2
        assert result["auth_requests"] == 1
        for role, tokens, auth in [("generator", 17, 0), ("guardian", 31, 1)]:
            assert result["role_usage"][role]["input_tokens"] == tokens
            assert result["role_usage"][role]["auth_requests"] == auth
        for row, req in zip(result["attribution"], [generator.requests[0], guardian.requests[0]], strict=True):
            assert row["operation"] == req.operation
            assert row["operation_version"] == req.operation_version
            assert row["schema_version"] == req.schema_version
        assert post(server, "/api/drafts/run", identity) == (status, result)
        assert len(generator.requests) == len(guardian.requests) == 1
        _, fresh = post(server, "/api/drafts/request", {"snapshot": identity["snapshot"]})
        assert fresh["run_request"] != identity["run_request"]
        assert len(generator.requests) == len(guardian.requests) == 1
        assert post(server, "/api/drafts/run", {k: fresh[k] for k in identity})[1]["status"] == "completed"
        assert len(generator.requests) == len(guardian.requests) == 2
    assert selected.read_bytes() == original


@pytest.mark.parametrize("outcome,expected", [("invalid", "failed"), ("digest", "failed"),
                                               ("exception", "failed"), ("timeout", "uncertain")])
def test_http_guardian_failure_retains_exact_generator_without_retry(operator, outcome, expected):
    config, folder, evidence = operator
    draft(folder, "old.md")
    generator, guardian = FixtureSource(), GuardianSource(outcome=outcome)
    with running_server(evidence, draft_config=config, draft_model_source=generator,
                        guardian_model_source=guardian) as server:
        identity = capture(server)
        status, result = post(server, "/api/drafts/run", identity)
        assert status == 200 and result["status"] == expected and not result["succeeded"]
        assert result["result"] == RESULT and result["review"] is None
        assert "SECRET_PROVIDER_FAILURE" not in json.dumps(result)
        assert post(server, "/api/drafts/run", identity) == (status, result)
        assert len(generator.requests) == len(guardian.requests) == 1


@pytest.mark.parametrize("outcome", ["blocked", "invalid", "timeout"])
def test_http_generator_stop_never_invokes_guardian(operator, outcome):
    config, folder, evidence = operator
    draft(folder, "old.md")
    generator, guardian = FixtureSource(outcome), GuardianSource()
    with running_server(evidence, draft_config=config, draft_model_source=generator,
                        guardian_model_source=guardian) as server:
        identity = capture(server)
        result = post(server, "/api/drafts/run", identity)[1]
        assert not result["succeeded"] and result["review"] is None
        assert len(generator.requests) == 1 and not guardian.requests


def test_http_concurrent_guardian_and_restart_never_repeat_pair(operator):
    config, folder, evidence = operator
    draft(folder, "old.md")
    entered, release = threading.Event(), threading.Event()
    generator, guardian = FixtureSource(), GuardianSource(entered=entered, release=release)
    options = dict(draft_config=config, draft_model_source=generator, guardian_model_source=guardian)
    with running_server(evidence, **options) as server:
        identity = capture(server)
        with ThreadPoolExecutor() as pool:
            first = pool.submit(post, server, "/api/drafts/run", identity)
            try:
                assert entered.wait(5)
                assert post(server, "/api/drafts/run", identity)[1]["status"] == "running"
            finally:
                release.set()
            completed = first.result()
            assert completed[1]["status"] == "completed"
    with running_server(evidence, **options) as server:
        assert post(server, "/api/drafts/run", identity) == completed
    assert len(generator.requests) == len(guardian.requests) == 1
