"""Custom execution shares the local HTTP security boundary."""
import json
from copy import deepcopy
from pathlib import Path

import pytest

from test_designer_custom import INVALID, REQUEST, failing_candidate

from test_designer_server import credentials, request, running_server
from test_designer_triage import DEFAULT, EXPECTED


def test_http_custom_runs_remain_separate_from_supplied_case_checks(tmp_path):
    with running_server(tmp_path) as server:
        headers = credentials(server)
        for row in EXPECTED:
            initial = dict(zip(("request_id", "category", "urgency", "description"), row[:4]))
            status, _, body = request(server, "/api/run", method="POST", headers=headers,
                                      body=json.dumps({"design": DEFAULT, "request": initial}))
            assert status == 200
            result = json.loads(body)
            assert result["succeeded"] is True
            assert "passed" not in result
            assert result["input"] == initial
            assert result["output"]["state"]["summary"] == row[6]
            assert [edge[0] for edge in result["output"]["route"]] == row[7]
        status, _, body = request(server, "/api/check", method="POST", headers=headers,
                                  body=json.dumps(DEFAULT))
        assert status == 200
        assert json.loads(body)["passed"] is True
        assert json.loads(body)["cases"] == ["B-N", "B-U", "T-N", "T-U", "G-N", "G-U"]


def test_http_invalid_fields_envelopes_and_designs_never_execute(tmp_path):
    def forbidden(design):
        pytest.fail("invalid input reached generation")
    bad_design = deepcopy(DEFAULT)
    bad_design["entry"] = "missing"
    bodies = [{"design": DEFAULT, "request": value} for value in INVALID]
    bodies += [None, [], {}, {"design": DEFAULT},
               {"design": bad_design, "request": REQUEST},
               {"design": {"nodes": []}, "request": REQUEST}]
    bodies += [{"design": DEFAULT, "request": REQUEST, key: "/tmp/arbitrary"}
               for key in ("code", "input_file", "evidence_dir", "candidate_factory")]
    with running_server(tmp_path, candidate_factory=forbidden) as server:
        headers = credentials(server)
        for body in bodies:
            status, _, data = request(server, "/api/run", method="POST", headers=headers,
                                      body=json.dumps(body))
            assert status == 400
            assert json.loads(data)["succeeded"] is False
        assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("field,value,status", [
    ("Host", "localhost", 403), ("Origin", "null", 403),
    ("Origin", "https://example.com", 403), ("X-Designer-Token", "wrong", 403),
    ("Content-Type", "text/plain", 415), ("Content-Length", "4097", 400),
    ("Content-Length", "0", 400), ("Transfer-Encoding", "chunked", 400),
])
def test_custom_execution_retains_security_and_body_bounds(tmp_path, field, value, status):
    def forbidden(design):
        pytest.fail("unsafe request reached generation")
    with running_server(tmp_path, candidate_factory=forbidden) as server:
        headers = {**credentials(server), field: value}
        actual, _, body = request(server, "/api/run", method="POST", headers=headers,
                                  body=json.dumps({"design": DEFAULT, "request": REQUEST}))
        assert actual == status
        assert json.loads(body)["succeeded"] is False
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("failure", ["generation", "unsupported", "execution", "budget", "evidence"])
def test_http_custom_failure_cannot_be_success(tmp_path, failure):
    root = tmp_path / "evidence"
    with running_server(root, **({} if failure == "evidence" else
                                {"candidate_factory": failing_candidate(failure)})) as server:
        if failure == "evidence":
            root.write_text("blocked")
        status, _, data = request(server, "/api/run", method="POST", headers=credentials(server),
                                  body=json.dumps({"design": DEFAULT, "request": REQUEST}))
        result = json.loads(data)
        assert result["succeeded"] is False
        assert "passed" not in result
        if failure == "execution":
            assert status == 200
            assert result["output"]["terminal"] == "FAILED_VALIDATION"
            assert Path(result["evidence"]).is_relative_to(root)
        else:
            assert status == 500
