"""Local HTTP boundary exercised with real requests and real core execution."""
import contextlib
import http.client
import json
import re
import threading

import pytest
from pathlib import Path

from agent_lab.designer.server import create_server
from agent_lab.runlog import RunLog

ANSWERS = {"nodes": [
    {"id": "start", "operation": "receive", "done": "choose"},
    {"id": "choose", "operation": "compare", "threshold": 50,
     "below": "REVIEW", "at_or_above": "ACCEPTED"},
]}


@contextlib.contextmanager
def running_server(root: Path, **kwargs):
    server = create_server(root, **kwargs)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def request(server, path="/", *, method="GET", body=None, headers=None):
    connection = http.client.HTTPConnection(*server.server_address, timeout=10)
    connection.request(method, path, body=body, headers=headers or {})
    response = connection.getresponse()
    result = response.status, dict(response.getheaders()), response.read()
    connection.close()
    return result


def credentials(server):
    status, headers, page = request(server)
    assert status == 200
    assert "Content-Security-Policy" in headers
    token = re.search(rb'name="request-token" content="([^"]+)"', page)[1].decode()
    host = f"127.0.0.1:{server.server_port}"
    return {"Host": host, "Origin": f"http://{host}",
            "Content-Type": "application/json", "X-Designer-Token": token}


def test_http_authors_design_and_checks_real_cases(tmp_path):
    with running_server(tmp_path / "evidence") as server:
        headers = credentials(server)
        status, _, body = request(server, "/api/design", method="POST",
                                  body=json.dumps(ANSWERS), headers=headers)
        assert status == 200
        design = json.loads(body)
        assert design["answers"] == ANSWERS
        assert [case["score"] for case in design["cases"]] == [48, 49, 50, 51]
        assert design["budget"] == 2
        status, _, body = request(server, "/api/check", method="POST",
                                  body=json.dumps(ANSWERS), headers=headers)
        assert status == 200
        result = json.loads(body)
        assert result["passed"] is True
        assert result["cases"] == result["completed_cases"] == ["score_48", "score_49", "score_50", "score_51"]
        assert len(result["evidence"]) == 4
        for item, outcome, terminal in zip(result["evidence"],
                                          ["below", "below", "at_or_above", "at_or_above"],
                                          ["REVIEW", "REVIEW", "ACCEPTED", "ACCEPTED"], strict=True):
            assert Path(item["reference_log"]).is_file()
            events = RunLog(Path(item["candidate_log"])).read()
            assert [(event.node, event.transition, event.detail["target"]) for event in events] == [
                ("start", "done", "choose"), ("choose", outcome, terminal),
            ]
            assert events[-1].terminal == terminal


@pytest.mark.parametrize("field,value", [
    ("Host", "evil.example"), ("Host", "localhost"),
    ("Origin", "https://evil.example"), ("Origin", "null"),
    ("Origin", None), ("X-Designer-Token", None), ("X-Designer-Token", "wrong"),
    ("Content-Type", "text/plain"),
])
def test_cross_site_and_uncredentialed_posts_cannot_execute(tmp_path, field, value):
    root = tmp_path / "evidence"
    with running_server(root) as server:
        headers = credentials(server)
        if value is None:
            del headers[field]
        else:
            headers[field] = value
        status, _, body = request(server, "/api/check", method="POST",
                                  body=json.dumps(ANSWERS), headers=headers)
        assert status in (403, 415)
        assert json.loads(body)["passed"] is False
        assert not list(root.rglob("*.jsonl"))


@pytest.mark.parametrize("path", ["/../server.py", "/%2e%2e/server.py", "/api/check?x=1", "/static/../../HANDOFF.md"])
def test_only_exact_paths_are_served(tmp_path, path):
    with running_server(tmp_path / "evidence") as server:
        status, _, _ = request(server, path)
        assert status == 404
        status, _, _ = request(server, path, method="POST", body=json.dumps(ANSWERS),
                               headers=credentials(server))
        assert status == 404


def test_page_token_is_not_served_under_foreign_host(tmp_path):
    with running_server(tmp_path / "evidence") as server:
        status, headers, body = request(server, headers={"Host": "evil.example"})
        assert status == 403
        assert b"request-token" not in body
        assert "Access-Control-Allow-Origin" not in headers


@pytest.mark.parametrize("endpoint", ["/api/design", "/api/check"])
@pytest.mark.parametrize("raw", [
    None, {}, {"nodes": []},
    {**ANSWERS, "evidence_dir": "/tmp/injected"},
    {**ANSWERS, "candidate_factory": "code"},
    {**ANSWERS, "budget": 100},
    {**ANSWERS, "bindings": {"receive_request": "exec"}},
    {"nodes": [{"id": "start", "operation": "receive", "done": "deleted"}]},
    {"nodes": [{"id": "start", "operation": "receive", "done": "start"}]},
    {"nodes": [ANSWERS["nodes"][0], {**ANSWERS["nodes"][1], "threshold": True}]},
    {"nodes": [ANSWERS["nodes"][0], {**ANSWERS["nodes"][1], "threshold": "50"}]},
    {"nodes": [ANSWERS["nodes"][0], {**ANSWERS["nodes"][1], "threshold": 50.0}]},
    {"nodes": [ANSWERS["nodes"][0], {**ANSWERS["nodes"][1], "operation": "os.system"}]},
    {"nodes": [{"id": "start", "operation": "receive"}]},
    {"nodes": [ANSWERS["nodes"][0],
               {"id": "choose", "operation": "compare", "threshold": 50, "below": "REVIEW"}]},
    {"nodes": [{"id": "start", "operation": "receive", "done": "a"},
               {"id": "a", "operation": "adjust", "adjustment": True, "done": "ACCEPTED"}]},
    {"nodes": [{"id": "start", "operation": "receive", "done": "a"},
               *[{"id": identity, "operation": "adjust", "adjustment": 10, "done": target}
                 for identity, target in zip("abcdef", ["b", "c", "d", "e", "f", "ACCEPTED"], strict=True)]]},
    {"nodes": [{"id": "start", "operation": "receive", "done": "a"},
               *[{"id": identity, "operation": "compare", "threshold": 50,
                  "below": target, "at_or_above": "ACCEPTED"}
                 for identity, target in zip("abc", ["b", "c", "REVIEW"], strict=True)]]},
    {"nodes": [{"id": "start", "operation": "receive", "done": "ACCEPTED"},
               {"id": "unused", "operation": "adjust", "adjustment": 10, "done": "REVIEW"}]},
])
def test_invalid_answers_fail_without_generation_or_evidence(tmp_path, raw, endpoint):
    root = tmp_path / "evidence"
    calls = []
    def forbidden(design):
        calls.append(design)
        raise RuntimeError("invalid draft reached generation")
    with running_server(root, candidate_factory=forbidden) as server:
        status, _, body = request(server, endpoint, method="POST", body=json.dumps(raw),
                                  headers=credentials(server))
        assert status == 400
        result = json.loads(body)
        assert result["passed"] is False
        assert result["findings"]
        assert not calls
        assert not list(root.rglob("*.jsonl"))


def test_startup_rejects_protected_source_and_symlinks(tmp_path):
    source = Path(__file__).resolve().parents[1]
    link = tmp_path / "source-link"
    link.symlink_to(source, target_is_directory=True)
    for root in (source / "forbidden-evidence", link / "forbidden-evidence"):
        with pytest.raises(ValueError):
            create_server(root)


def test_operator_can_protect_an_additional_hermes_installation(tmp_path):
    installation = tmp_path / "other-installation"
    with pytest.raises(ValueError, match="outside Hermes"):
        create_server(installation / "evidence", protected_roots=(installation,))
    assert not installation.exists()


def test_generation_exception_is_visible_json_failure(tmp_path):
    def broken(design):
        raise RuntimeError("deliberate generation failure")
    with running_server(tmp_path / "evidence", candidate_factory=broken) as server:
        status, _, body = request(server, "/api/check", method="POST", body=json.dumps(ANSWERS),
                                  headers=credentials(server))
        assert status in (200, 500)
        result = json.loads(body)
        assert result["passed"] is False
        assert "deliberate generation failure" in str(result["findings"])


@pytest.mark.parametrize("failure", ["checking", "audit"])
def test_checking_and_evidence_failures_are_visible_over_http(tmp_path, monkeypatch, failure):
    kwargs = {}
    if failure == "checking":
        kwargs["candidate_factory"] = lambda design: object()
    else:
        def fail_write(self, event):
            raise OSError("evidence unavailable")
        monkeypatch.setattr(RunLog, "append_next", fail_write)
    with running_server(tmp_path / "evidence", **kwargs) as server:
        status, _, body = request(server, "/api/check", method="POST", body=json.dumps(ANSWERS),
                                  headers=credentials(server))
        assert status == 200
        result = json.loads(body)
        assert result["passed"] is False
        assert result["completed_cases"] == []
        assert result["findings"]
        assert result["findings"][0]["code"] == ("unsupported_candidate" if failure == "checking" else "incomplete")


@pytest.mark.parametrize("body", [b"{", b"null", b"[]"])
def test_malformed_or_nonobject_json_cannot_execute(tmp_path, body):
    calls = []
    def forbidden(design):
        calls.append(design)
    with running_server(tmp_path / "evidence", candidate_factory=forbidden) as server:
        status, _, response = request(server, "/api/check", method="POST", body=body,
                                      headers=credentials(server))
        assert status == 400
        assert json.loads(response)["passed"] is False
        assert not calls
        assert not list((tmp_path / "evidence").rglob("*.jsonl"))
