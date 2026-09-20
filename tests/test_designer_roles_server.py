"""Actual loopback HTTP for the bounded role mode."""
import json
from pathlib import Path

import pytest

from test_designer_server import credentials, request, running_server
from test_designer_roles import DEFAULT, altered_candidate


def test_http_role_design_check_and_selected_fixture(tmp_path):
    with running_server(tmp_path) as server:
        headers = credentials(server)
        status, _, body = request(server, "/api/design", method="POST", headers=headers,
                                   body=json.dumps(DEFAULT))
        assert status == 200
        assert len(json.loads(body)["catalog"]["roles"]) == 3
        for fixture, outcome in (("with_evidence", "evidence_present"),
                                 ("without_evidence", "evidence_missing")):
            status, _, body = request(server, "/api/run", method="POST", headers=headers,
                body=json.dumps({"design": DEFAULT, "request": {"fixture": fixture}}))
            assert status == 200
            result = json.loads(body)
            assert result["succeeded"] is True
            assert result["output"]["state"]["verdict"]["result"] == outcome
            assert "passed" not in result
        status, _, body = request(server, "/api/check", method="POST", headers=headers,
                                   body=json.dumps(DEFAULT))
        assert status == 200
        assert json.loads(body)["passed"] is True
        assert json.loads(body)["completed_cases"] == ["with_evidence", "without_evidence"]


def test_http_rejected_designs_and_fixed_fixture_boundary_cannot_execute(tmp_path):
    def forbidden(design):
        pytest.fail("invalid HTTP input reached generation")
    with running_server(tmp_path, candidate_factory=forbidden) as server:
        headers = credentials(server)
        for change in ({"consumer": "studio_producer"}, {"producer": "unknown"},
                       {"consumer": "studio_producer", "output": "caption"},
                       {"output": "Evidence_Handoff"}, {"catalog": {}}, {"bindings": {}},
                       {"code": "print(1)"}, {"evidence_dir": "/tmp"}, {"budget": 1},
                       {"consumer": True}, {"output": None}):
            for endpoint in ("design", "check", "run"):
                design = {**DEFAULT, **change}
                raw = {"design": design, "request": {"fixture": "with_evidence"}} if endpoint == "run" else design
                status, _, body = request(server, f"/api/{endpoint}", method="POST", headers=headers, body=json.dumps(raw))
                assert status == 400
                assert json.loads(body).get("passed", json.loads(body).get("succeeded")) is False
        for selection in ({}, None, "with_evidence", {"fixture": 1}, {"fixture": "unknown"},
                          {"fixture": "with_evidence", "verdict": {}},
                          {"fixture": "with_evidence", "brief": {"text": "custom"}},
                          {"fixture": "with_evidence", "path": "/tmp/source"}):
            status, _, body = request(server, "/api/run", method="POST", headers=headers,
                body=json.dumps({"design": DEFAULT, "request": selection}))
            assert status == 400
            assert json.loads(body)["succeeded"] is False
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("corruption", ["malformed", "missing-review"])
def test_http_malformed_repository_catalog_cannot_execute(tmp_path, monkeypatch, corruption):
    from agent_lab.designer import author_design
    catalog = author_design(DEFAULT).view()["catalog"]
    if corruption == "malformed":
        catalog["roles"][0]["accepts"] = "bounded_writing_brief"
    else:
        catalog["roles"][2]["reviews"] = []
    original = Path.read_text
    def corrupted(path, *args, **kwargs):
        return json.dumps(catalog) if path.name == "role_catalog.json" else original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "read_text", corrupted)
    def forbidden(design):
        pytest.fail("malformed contract reached generation")
    with running_server(tmp_path, candidate_factory=forbidden) as server:
        headers = credentials(server)
        for endpoint in ("design", "check", "run"):
            raw = {"design": DEFAULT, "request": {"fixture": "with_evidence"}} if endpoint == "run" else DEFAULT
            status, _, body = request(server, f"/api/{endpoint}", method="POST", headers=headers, body=json.dumps(raw))
            assert status == 400
            assert json.loads(body)["findings"]
    assert list(tmp_path.iterdir()) == []


def test_http_role_mode_preserves_exact_security_and_size_boundary(tmp_path):
    def forbidden(design):
        pytest.fail("unsafe HTTP request reached generation")
    with running_server(tmp_path, candidate_factory=forbidden) as server:
        good = credentials(server)
        body = json.dumps({"design": DEFAULT, "request": {"fixture": "with_evidence"}})
        for key, value in (("Host", "localhost"), ("Host", "evil.invalid"),
                           ("Origin", "null"), ("Origin", good["Origin"] + "/"),
                           ("X-Designer-Token", "incorrect")):
            status, _, response = request(server, "/api/run", method="POST",
                                          headers={**good, key: value}, body=body)
            assert status == 403
            assert json.loads(response)["succeeded"] is False
        for missing in ("Origin", "X-Designer-Token"):
            status, _, _ = request(server, "/api/run", method="POST",
                                   headers={k: v for k, v in good.items() if k != missing}, body=body)
            assert status == 403
        status, _, _ = request(server, "/api/run", method="POST", headers=good, body=" " * 4097)
        assert status == 400
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("failure", ["generation", "unsupported", "budget", "route", "behavior", "execution", "audit"])
def test_http_role_failures_remain_visible(tmp_path, monkeypatch, failure):
    if failure == "audit":
        original = Path.open
        def fail(path, mode="r", *args, **kwargs):
            if path.suffix == ".jsonl" and mode == "a+":
                raise OSError("audit unavailable")
            return original(path, mode, *args, **kwargs)
        monkeypatch.setattr(Path, "open", fail)
    options = {} if failure == "audit" else {"candidate_factory": altered_candidate(failure)}
    with running_server(tmp_path, **options) as server:
        headers = credentials(server)
        status, _, body = request(server, "/api/check", method="POST", headers=headers, body=json.dumps(DEFAULT))
        result = json.loads(body)
        assert status in (200, 500)
        assert result["passed"] is False
        if failure != "behavior":
            status, _, body = request(server, "/api/run", method="POST", headers=headers,
                body=json.dumps({"design": DEFAULT, "request": {"fixture": "with_evidence"}}))
            assert status == (200 if failure == "execution" else 500)
            assert json.loads(body)["succeeded"] is False
