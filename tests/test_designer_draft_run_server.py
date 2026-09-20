"""Ticket 21: actual HTTP requests, real DraftRuns and fixture model sources."""
import json
import re
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from agent_lab.model_operation import ModelResponse
from tests.test_designer_drafts import draft, operator  # noqa: F401
from tests.test_designer_server import credentials, request, running_server


POST = '<script>window.injected=true</script>\r\nA synthetic post.'
RESULT = {"post": POST, "reader": "Synthetic reader", "one_point": "One synthetic point",
          "support": [], "limitations": ["Synthetic fixture only"], "blocked_reason": None}


class FixtureSource:
    mode = "fixture"

    def __init__(self, outcome="draft", entered=None, release=None):
        self.requests = []
        self.outcome = outcome
        self.entered = entered
        self.release = release

    def invoke(self, model_request):
        self.requests.append(model_request)
        if self.entered is not None:
            self.entered.set()
        if self.release is not None:
            assert self.release.wait(5)
        if self.outcome == "exception":
            raise RuntimeError("SECRET_PROVIDER_FAILURE bearer-secret")
        if self.outcome == "timeout":
            raise TimeoutError("SECRET_PROVIDER_FAILURE bearer-secret")
        result = dict(RESULT)
        if self.outcome == "blocked":
            result.update(post=None, blocked_reason="Insufficient public support")
        return ModelResponse(body="not JSON" if self.outcome == "invalid" else json.dumps(result),
                             input_tokens=17, output_tokens=9)


def post(server, endpoint, value, headers=None):
    status, _, body = request(server, endpoint, method="POST", headers=headers or credentials(server),
                              body=json.dumps(value))
    return status, json.loads(body)


def capture(server):
    status, result = post(server, "/api/drafts/capture", {})
    assert status == 200 and result["succeeded"] is True
    assert result["status"] == "ready"
    assert re.fullmatch("[0-9a-f]{64}", result["run_request"])
    return {key: result[key] for key in ("snapshot", "run_request")}


def test_http_explicit_run_duplicate_and_intentional_new_request(operator):
    config, folder, evidence = operator
    selected = draft(folder, "old.md")
    original = selected.read_bytes()
    source = FixtureSource()
    with running_server(evidence, draft_config=config, draft_model_source=source) as server:
        assert request(server, "/api/drafts")[0] == 200
        identity = capture(server)
        assert source.requests == []
        status, result = post(server, "/api/drafts/run", identity)
        assert status == 200 and result["status"] == "not_reviewed"
        assert result["result"] == RESULT
        assert result["usage"]["input_tokens"] == 17
        assert result["usage"]["output_tokens"] == 9
        assert len(source.requests) == 1
        assert post(server, "/api/drafts/run", identity) == (status, result)
        assert len(source.requests) == 1
        status, new = post(server, "/api/drafts/request", {"snapshot": identity["snapshot"]})
        assert status == 200 and new["run_request"] != identity["run_request"]
        assert len(source.requests) == 1
        assert post(server, "/api/drafts/run", {key: new[key] for key in identity})[1]["status"] == "not_reviewed"
        assert len(source.requests) == 2
    assert selected.read_bytes() == original


@pytest.mark.parametrize("outcome,expected", [("blocked", "blocked"), ("invalid", "failed"),
                                               ("exception", "failed"), ("timeout", "uncertain")])
def test_http_failure_states_never_retry_or_expose_provider_errors(operator, outcome, expected):
    config, folder, evidence = operator
    draft(folder, "old.md")
    source = FixtureSource(outcome)
    with running_server(evidence, draft_config=config, draft_model_source=source) as server:
        identity = capture(server)
        status, result = post(server, "/api/drafts/run", identity)
        assert status == 200 and result["status"] == expected
        assert not result["succeeded"]
        assert "SECRET_PROVIDER_FAILURE" not in json.dumps(result)
        assert "bearer-secret" not in json.dumps(result)
        assert post(server, "/api/drafts/run", identity) == (status, result)
        assert len(source.requests) == 1


def test_http_concurrent_duplicate_has_one_invocation(operator):
    config, folder, evidence = operator
    draft(folder, "old.md")
    entered, release = threading.Event(), threading.Event()
    source = FixtureSource(entered=entered, release=release)
    with running_server(evidence, draft_config=config, draft_model_source=source) as server:
        identity = capture(server)
        with ThreadPoolExecutor() as pool:
            first = pool.submit(post, server, "/api/drafts/run", identity)
            try:
                assert entered.wait(5)
                assert post(server, "/api/drafts/run", identity)[1]["status"] == "running"
            finally:
                release.set()
            assert first.result()[1]["status"] == "not_reviewed"
        assert len(source.requests) == 1


@pytest.mark.parametrize("endpoint", ["/api/drafts/request", "/api/drafts/run"])
@pytest.mark.parametrize("bad", [{}, {"snapshot": "../escape"}, {"snapshot": "0" * 64, "prompt": "injected"},
                                  {"snapshot": "0" * 64, "run_request": "0" * 64, "auth_file": "/secret"}])
def test_strict_draft_request_fields(operator, endpoint, bad):
    config, folder, evidence = operator
    source = FixtureSource()
    with running_server(evidence, draft_config=config, draft_model_source=source) as server:
        assert post(server, endpoint, bad)[0] == 400
        assert not source.requests


@pytest.mark.parametrize("endpoint", ["/api/drafts/request", "/api/drafts/run"])
@pytest.mark.parametrize("change,expected", [("origin", 403), ("token", 403), ("host", 403),
                                              ("type", 415), ("large", 400), ("duplicate", 400)])
def test_draft_routes_retain_request_boundaries(operator, endpoint, change, expected):
    config, folder, evidence = operator
    draft(folder, "old.md")
    source = FixtureSource()
    with running_server(evidence, draft_config=config, draft_model_source=source) as server:
        identity = capture(server)
        headers = credentials(server)
        body = json.dumps(identity if endpoint.endswith("run") else {"snapshot": identity["snapshot"]})
        if change == "origin":
            headers["Origin"] = "http://localhost"
        elif change == "host":
            headers["Host"] = "localhost"
        elif change == "token":
            headers["X-Designer-Token"] = "incorrect"
        elif change == "type":
            headers["Content-Type"] = "text/plain"
        elif change == "large":
            body = " " * 4097
        else:
            body = '{"snapshot":"secret","snapshot":"secret"}'
        status, _, response = request(server, endpoint, method="POST", headers=headers, body=body)
        assert status == expected
        assert b"secret" not in response
        assert not source.requests


def test_missing_auth_only_matters_on_explicit_run(operator):
    config, folder, evidence = operator
    draft(folder, "old.md")
    (config.parent / "generator.yaml").write_text("model:\n  provider: openai-codex\n  default: gpt-5.6-sol\n")
    with running_server(evidence, draft_config=config, codex_auth_file=config.parent / "absent-auth.json") as server:
        assert request(server, "/api/drafts")[0] == 200
        identity = capture(server)
        status, result = post(server, "/api/drafts/run", identity)
        assert status == 200 and result["status"] == "failed"
        assert not result["succeeded"]
