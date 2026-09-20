"""Local HTTP boundary exercised with real requests and real core execution."""
import contextlib
import http.client
import json
import re
import threading

import pytest
from pathlib import Path

from agent_lab.designer.server import create_server

ANSWERS = {"threshold": 50, "below": "REVIEW", "at_or_above": "ACCEPTED"}


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
        assert [case["score"] for case in design["cases"]] == [49, 50, 51]
        status, _, body = request(server, "/api/check", method="POST",
                                  body=json.dumps(ANSWERS), headers=headers)
        assert status == 200
        result = json.loads(body)
        assert result["passed"] is True
        assert len(result["completed_cases"]) == 3
        assert len(result["evidence"]) == 3
        for item in result["evidence"]:
            assert Path(item["reference_log"]).is_file()
            assert Path(item["candidate_log"]).is_file()


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


@pytest.mark.parametrize("raw", [None, {}, {**ANSWERS, "threshold": True},
                                    {**ANSWERS, "evidence_dir": "/tmp/injected"},
                                    {**ANSWERS, "candidate_factory": "code"}])
def test_invalid_answers_fail_without_evidence(tmp_path, raw):
    root = tmp_path / "evidence"
    with running_server(root) as server:
        status, _, body = request(server, "/api/check", method="POST", body=json.dumps(raw),
                                  headers=credentials(server))
        assert status == 400
        assert json.loads(body)["passed"] is False
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
