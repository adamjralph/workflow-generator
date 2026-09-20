"""Controlled-source behavior at the loopback HTTP and operator CLI seams."""
import json
import select
import subprocess
import sys
from urllib.request import urlopen

from tests.test_designer_roles import DEFAULT
from tests.test_designer_server import credentials, request, running_server

import pytest

BRIEF = {"request_id": "local-brief", "text": "Write a local update.",
         "evidence_labels": ["local-note"]}


def post(server, endpoint, value):
    status, _, body = request(server, f"/api/source/{endpoint}", method="POST",
                              headers=credentials(server), body=json.dumps(value))
    return status, json.loads(body)


def test_source_availability_is_fixed_name_and_host_protected(tmp_path):
    for options, available in (({}, False), ({"source_file": tmp_path / "private.json"}, True)):
        with running_server(tmp_path / "evidence", **options) as server:
            status, _, body = request(server, "/api/source")
            assert status == 200
            assert json.loads(body) == {"available": available, "source": "Local writing brief"}
            status, _, body = request(server, "/api/source", headers={"Host": "evil.test"})
            assert status == 403
            assert str(tmp_path).encode() not in body


def test_capture_run_and_independent_check_replay_without_rereading_source(tmp_path):
    source = tmp_path / "private.json"
    original = json.dumps(BRIEF).encode()
    source.write_bytes(original)
    source.chmod(0o444)
    with running_server(tmp_path / "evidence", source_file=source) as server:
        status, captured = post(server, "capture", {})
        assert status == 200
        assert captured["input"] == BRIEF
        assert captured["source"] == "Local writing brief"
        assert source.read_bytes() == original
        assert source.stat().st_mode & 0o222 == 0
        source.unlink()
        payload = {"design": DEFAULT, "snapshot": captured["snapshot"]}
        status, result = post(server, "run", payload)
        assert status == 200
        assert result["succeeded"] is True
        assert "passed" not in result
        assert result["output"]["state"]["verdict"] == {
            "request_id": "local-brief", "evidence_count": 1, "result": "evidence_present"}
        status, result = post(server, "check", payload)
        assert status == 200
        assert result["passed"] is True
        assert result["completed_cases"] == ["captured_input"]
        assert result["input"] == BRIEF
        source.write_text(json.dumps({**BRIEF, "evidence_labels": []}))
        status, recaptured = post(server, "capture", {})
        assert status == 200
        assert recaptured["snapshot"] != captured["snapshot"]
        status, result = post(server, "run", {**payload, "snapshot": recaptured["snapshot"]})
        assert status == 200
        assert result["output"]["state"]["verdict"]["result"] == "evidence_missing"


@pytest.mark.parametrize("endpoint,flag", [("capture", "succeeded"), ("run", "succeeded"),
                                         ("check", "passed")])
def test_source_requests_retain_auth_body_and_strict_json_boundary(tmp_path, endpoint, flag):
    source = tmp_path / "brief.json"
    source.write_text(json.dumps(BRIEF))
    with running_server(tmp_path / "evidence", source_file=source) as server:
        headers = credentials(server)
        path = f"/api/source/{endpoint}"
        for field, value in (("Host", "evil.test"), ("Origin", "https://evil.test"),
                             ("X-Designer-Token", "wrong")):
            status, _, body = request(server, path, method="POST", body="{}",
                                      headers={**headers, field: value})
            assert status == 403
            assert json.loads(body)[flag] is False
        for changes, expected in (({"Content-Type": "text/plain"}, 415),
                                  ({"Content-Length": "4097"}, 400),
                                  ({"Transfer-Encoding": "chunked"}, 400)):
            status, _, body = request(server, path, method="POST", body="{}",
                                      headers={**headers, **changes})
            assert status == expected
            assert json.loads(body)[flag] is False
        payload = {} if endpoint == "capture" else {"design": DEFAULT, "snapshot": "a" * 64}
        invalid = [None, [], {**payload, "source_file": str(source)},
                   {**payload, "evidence_dir": str(tmp_path)},
                   {**payload, "code": "execute"}]
        bodies = [json.dumps(item) for item in invalid] + ["{", '{"extra":NaN}']
        if endpoint != "capture":
            bodies += ['{"design":{},"design":' + json.dumps(DEFAULT) +
                       ',"snapshot":"' + "a" * 64 + '"}',
                       json.dumps({"design": DEFAULT, "snapshot": 1})]
        for raw in bodies:
            status, _, body = request(server, path, method="POST", headers=headers, body=raw)
            assert status == 400
            assert json.loads(body)[flag] is False
        assert not (tmp_path / "evidence").exists()


@pytest.mark.parametrize("endpoint,flag", [("capture", "succeeded"), ("run", "succeeded"),
                                         ("check", "passed")])
def test_missing_source_or_snapshot_errors_do_not_disclose_operator_paths(tmp_path, endpoint, flag):
    source = tmp_path / "secret-operator-path.json"
    with running_server(tmp_path / "evidence", source_file=source) as server:
        payload = {} if endpoint == "capture" else {"design": DEFAULT, "snapshot": "a" * 64}
        status, result = post(server, endpoint, payload)
        assert status >= 400
        assert result[flag] is False
        assert str(tmp_path) not in json.dumps(result)
        assert source.name not in json.dumps(result)


@pytest.mark.parametrize("endpoint,flag", [("run", "succeeded"), ("check", "passed")])
def test_corrupt_snapshot_and_path_selection_cannot_succeed(tmp_path, endpoint, flag):
    source = tmp_path / "brief.json"
    source.write_text(json.dumps(BRIEF))
    root = tmp_path / "evidence"
    with running_server(root, source_file=source) as server:
        _, captured = post(server, "capture", {})
        (root / "snapshots" / f'{captured["snapshot"]}.json').write_text('{}')
        for snapshot in (captured["snapshot"], str(source), "../brief.json", None):
            status, result = post(server, endpoint, {"design": DEFAULT, "snapshot": snapshot})
            assert status >= 400
            assert result[flag] is False
        assert json.loads(source.read_text()) == BRIEF


def test_unconfigured_source_never_runs_or_checks(tmp_path):
    with running_server(tmp_path / "evidence") as server:
        for endpoint, flag in (("capture", "succeeded"), ("run", "succeeded"), ("check", "passed")):
            status, result = post(server, endpoint, {})
            assert status >= 400
            assert result[flag] is False
    assert not (tmp_path / "evidence").exists()


def test_cli_source_file_enables_fixed_name_source_over_http(tmp_path):
    source = tmp_path / "private.json"
    source.write_text(json.dumps(BRIEF))
    process = subprocess.Popen(
        [sys.executable, "-m", "agent_lab.designer", "--evidence-dir", str(tmp_path / "evidence"),
         "--source-file", str(source)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        assert select.select([process.stdout], [], [], 10)[0], "CLI did not announce server"
        line = process.stdout.readline()
        assert line.startswith("Open http://127.0.0.1:"), line
        with urlopen(line.strip().removeprefix("Open ") + "api/source", timeout=5) as response:
            assert json.load(response) == {"available": True, "source": "Local writing brief"}
    finally:
        process.terminate()
        process.communicate(timeout=5)
