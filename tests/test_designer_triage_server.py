"""Ticket 15 via authenticated real loopback HTTP, using the existing adapter."""
import json
from copy import deepcopy

import pytest

from test_designer_server import credentials, request, running_server
from test_designer_triage import DEFAULT, EXPECTED, invalid_designs
from agent_lab.generation import generate_graph
from agent_lab.reference import TransformResult


def test_http_six_inputs_and_candidate_outputs(tmp_path):
    with running_server(tmp_path) as server:
        headers = credentials(server)
        status, _, body = request(server, "/api/design", method="POST", headers=headers, body=json.dumps(DEFAULT))
        assert status == 200
        assert [c["request_id"] for c in json.loads(body)["cases"]] == ["B-N", "B-U", "T-N", "T-U", "G-N", "G-U"]
        status, _, body = request(server, "/api/check", method="POST", headers=headers, body=json.dumps(DEFAULT))
        result = json.loads(body)
        assert status == 200
        assert result["passed"] is True
        assert [o["state"]["summary"] for o in result["outputs"]] == [e[6] for e in EXPECTED]
        for evidence in result["evidence"]:
            assert evidence["candidate_log"].startswith(str(tmp_path) + "/")


@pytest.mark.parametrize("endpoint", ["/api/design", "/api/check"])
@pytest.mark.parametrize("raw", list(invalid_designs()) + [
    {**DEFAULT, "cases": [{"description": "custom is ticket 16"}]},
    {**DEFAULT, "evidence_dir": "/tmp/unapproved"},
])
def test_http_rejects_all_invalid_paths_before_generation(tmp_path, endpoint, raw):
    def forbidden(design):
        pytest.fail("Invalid HTTP input reached generation")
    with running_server(tmp_path, candidate_factory=forbidden) as server:
        status, _, body = request(server, endpoint, method="POST", headers=credentials(server), body=json.dumps(raw))
        assert status == 400
        assert json.loads(body)["passed"] is False
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("field,value", [("Host", "localhost"), ("Origin", "http://evil.example"), ("X-Designer-Token", "wrong"), ("Content-Type", "text/plain")])
def test_triage_retains_exact_security_boundary(tmp_path, field, value):
    with running_server(tmp_path) as server:
        headers = credentials(server)
        headers[field] = value
        status, _, body = request(server, "/api/check", method="POST", headers=headers, body=json.dumps(DEFAULT))
        assert status in (403, 415)
        assert json.loads(body)["passed"] is False
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("failure", ["generation", "execution", "checking", "evidence"])
def test_triage_http_failure_is_visible(tmp_path, failure):
    def candidate(design):
        if failure == "generation":
            raise RuntimeError("generation unavailable")
        if failure == "checking":
            return object()
        bindings = dict(design.bindings)
        bindings["billing_team"] = lambda state: TransformResult(state, "not_a_route")
        return generate_graph(design.spec, state_type=design.state_type, bindings=bindings).candidate
    root = tmp_path / "evidence"
    with running_server(root, **({} if failure == "evidence" else {"candidate_factory": candidate})) as server:
        if failure == "evidence":
            root.write_text("blocked")
        status, _, body = request(server, "/api/check", method="POST", headers=credentials(server), body=json.dumps(DEFAULT))
        assert status == (500 if failure == "generation" else 200)
        result = json.loads(body)
        assert result["passed"] is False
        assert result["findings"]
