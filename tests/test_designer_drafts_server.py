"""Real loopback HTTP and CLI boundaries for capture-only draft previews."""
import http.client
import json
import selectors
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from tests.test_designer_drafts import draft, operator  # noqa: F401
from tests.test_designer_server import credentials, request, running_server


def test_capture_without_operator_configuration_is_unavailable(tmp_path: Path) -> None:
    with running_server(tmp_path / "evidence") as server:
        status, _, body = request(server, "/api/drafts/capture", method="POST",
                                  headers=credentials(server), body="{}")
        assert status == 400
        assert json.loads(body)["succeeded"] is False
    assert not (tmp_path / "evidence").exists()


def test_http_captures_oldest_draft_without_exposing_profile_secrets(operator) -> None:
    config, folder, evidence = operator
    selected = draft(folder, "old.md")
    draft(folder, "new.md", "processed: false\ndate_created: 2026-02-01")

    def forbidden_candidate(design):
        pytest.fail("capture must not invoke the trusted candidate factory")

    with running_server(evidence, draft_config=config, candidate_factory=forbidden_candidate) as server:
        status, _, body = request(server, "/api/drafts/capture", method="POST",
                                  headers=credentials(server), body="{}")
    assert status == 200
    result = json.loads(body)
    assert result["succeeded"] is True
    assert result["selected"]["name"] == "old.md"
    assert result["selected"]["text"].encode() == selected.read_bytes()
    assert result["max_model_calls"] == 2
    assert len(result["guidance"]) == 14
    assert result["models"] == [
        {"role": "generator", "provider": "synthetic", "model": "generator-model"},
        {"role": "guardian", "provider": "synthetic", "model": "guardian-model"},
    ]
    assert b"TOP_SECRET" not in body
    assert b"TOP_SECRET" not in Path(result["evidence"][0]).read_bytes()


@pytest.mark.parametrize("configured", [False, True])
def test_availability_is_configuration_only_without_input_reads(operator, configured) -> None:
    config, folder, evidence = operator
    with running_server(evidence, draft_config=config if configured else None) as server:
        # Removing every input after startup must not affect this availability-only GET.
        for path in config.parent.rglob("*"):
            if path.is_file():
                path.unlink()
        folder.rmdir()
        status, headers, body = request(server, "/api/drafts")
        assert status == 200
        assert json.loads(body) == {"available": configured, "run_available": configured,
                                    "source": "LinkedIn draft capture"}
        assert headers["Cache-Control"] == "no-store"
        assert request(server, "/api/drafts", headers={"Host": "evil.invalid"})[0] == 403
    assert not evidence.exists()


@pytest.mark.parametrize("missing", ["drafts", "guidance", "profile"])
def test_missing_capture_inputs_return_sanitized_failure(operator, missing) -> None:
    config, folder, evidence = operator
    selected = draft(folder, "old.md")
    with running_server(evidence, draft_config=config) as server:
        if missing == "drafts":
            selected.unlink()
            folder.rmdir()
        else:
            (config.parent / ("generator_soul.md" if missing == "guidance" else "generator.yaml")).unlink()
        status, _, body = request(server, "/api/drafts/capture", method="POST",
                                  headers=credentials(server), body="{}")
    assert status == 500
    assert json.loads(body)["succeeded"] is False
    assert str(config.parent).encode() not in body
    assert b"TOP_SECRET" not in body
    assert not evidence.exists()


@pytest.mark.parametrize("body", [
    "[]", "null", "false", '"{}"', "{", '{"path":"x","path":"y"}',
    '{"x":NaN}', '{"x":Infinity}', '[' * 1500 + ']' * 1500,
    *[json.dumps({key: "browser-controlled"}) for key in (
        "path", "drafts_dir", "provider", "model", "credentials", "code", "root",
        "config", "draft_config", "guidance", "profiles", "candidate_factory", "snapshot")],
])
def test_capture_rejects_all_browser_configuration_and_nonempty_json(operator, body) -> None:
    config, folder, evidence = operator
    draft(folder, "old.md")
    with running_server(evidence, draft_config=config) as server:
        status, _, response = request(server, "/api/drafts/capture", method="POST",
                                      headers=credentials(server), body=body)
    assert status == 400
    assert json.loads(response)["succeeded"] is False
    assert not evidence.exists()


def test_capture_retains_exact_auth_and_body_boundaries(operator) -> None:
    config, folder, evidence = operator
    draft(folder, "old.md")
    with running_server(evidence, draft_config=config) as server:
        good = credentials(server)
        for key, value in (("Host", "localhost"), ("Host", "evil.invalid"),
                           ("Origin", "null"), ("Origin", good["Origin"] + "/"),
                           ("X-Designer-Token", "wrong")):
            status, _, body = request(server, "/api/drafts/capture", method="POST",
                                      headers={**good, key: value}, body="{}")
            assert status == 403
            assert json.loads(body)["succeeded"] is False
        for key in ("Origin", "X-Designer-Token"):
            assert request(server, "/api/drafts/capture", method="POST", body="{}",
                           headers={k: v for k, v in good.items() if k != key})[0] == 403
        for extra, body, expected in (({"Content-Type": "text/plain"}, "{}", 415),
                                      ({}, " " * 4097, 400),
                                      ({"Content-Length": "0"}, "", 400),
                                      ({"Content-Length": "-1"}, "", 400),
                                      ({"Transfer-Encoding": "chunked"}, "{}", 400)):
            assert request(server, "/api/drafts/capture", method="POST", body=body,
                           headers={**good, **extra})[0] == expected
        # http.client's mapping helper cannot express duplicate header fields.
        for key in ("Host", "Origin", "X-Designer-Token", "Content-Length", "Content-Type"):
            connection = http.client.HTTPConnection(*server.server_address, timeout=10)
            try:
                connection.putrequest("POST", "/api/drafts/capture", skip_host=True)
                for name, value in {**good, "Content-Length": "2"}.items():
                    connection.putheader(name, value)
                    if name == key:
                        connection.putheader(name, value)
                connection.endheaders(b"{}")
                response = connection.getresponse()
                assert response.status == (400 if key == "Content-Length" else
                                           415 if key == "Content-Type" else 403)
                assert json.loads(response.read())["succeeded"] is False
            finally:
                connection.close()
        assert not evidence.exists()
        status, _, body = request(server, "/api/drafts/capture", method="POST",
                                  headers=good, body="{}" + " " * 4094)
        assert status == 200
        assert json.loads(body)["succeeded"] is True


@pytest.mark.parametrize("kind", ["empty", "invalid", "profile"])
def test_selection_and_yaml_failures_are_visible_without_secret_disclosure(operator, kind) -> None:
    config, folder, evidence = operator
    if kind == "invalid":
        draft(folder, "old.md", 'processed: [\nsecret: TOP_SECRET')
    elif kind == "profile":
        draft(folder, "old.md")
        (config.parent / "generator.yaml").write_text('model: [\nsecret: TOP_SECRET')
    with running_server(evidence, draft_config=config) as server:
        status, _, body = request(server, "/api/drafts/capture", method="POST",
                                  headers=credentials(server), body="{}")
    assert status == (500 if kind == "profile" else 200)
    result = json.loads(body)
    assert result["succeeded"] is False
    assert result["findings"]
    assert b"TOP_SECRET" not in body
    assert str(config.parent).encode() not in body
    assert not evidence.exists()


def test_recapture_uses_current_readonly_inputs_and_pinned_manifest(operator) -> None:
    config, folder, evidence = operator
    selected = draft(folder, "old.md")
    originals = {}
    for path in config.parent.rglob("*"):
        if path.is_file():
            path.chmod(0o400)
            originals[path] = (path.read_bytes(), path.stat().st_mode, path.stat().st_mtime_ns)
    with running_server(evidence, draft_config=config) as server:
        headers = credentials(server)

        def capture():
            status, _, body = request(server, "/api/drafts/capture", method="POST",
                                      headers=headers, body="{}")
            assert status == 200
            return json.loads(body)

        first = capture()
        assert first["succeeded"] is True
        saved = Path(first["evidence"][0]).read_bytes()
        repeated = capture()
        assert repeated.pop("run_request") != first["run_request"]
        assert repeated == {key: value for key, value in first.items() if key != "run_request"}
        for path, original in originals.items():
            assert (path.read_bytes(), path.stat().st_mode, path.stat().st_mtime_ns) == original
        config.chmod(0o600)
        config.write_text('{"drafts_dir":"/untrusted-new-location"}')
        pinned = capture()
        assert pinned.pop("run_request") != first["run_request"]
        assert pinned == repeated
        selected.chmod(0o600)
        selected.write_bytes(selected.read_bytes() + b"Changed body.\n")
        second = capture()
        assert second["succeeded"] is True
        assert second["snapshot"] != first["snapshot"]
        assert second["selected"]["text"].endswith("Changed body.\n")
        assert Path(first["evidence"][0]).read_bytes() == saved
    assert {path.name for path in evidence.iterdir()} == {"draft-snapshots", "draft-runs"}
    assert not list((evidence / "draft-runs").glob("*/claimed.json"))


def test_concurrent_identical_http_captures_publish_one_immutable_bundle(operator) -> None:
    config, folder, evidence = operator
    draft(folder, "old.md")
    with running_server(evidence, draft_config=config) as server:
        headers = credentials(server)

        def capture(_):
            status, _, body = request(server, "/api/drafts/capture", method="POST",
                                      headers=headers, body="{}")
            assert status == 200
            return json.loads(body)

        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(capture, range(16)))
        assert results[0]["succeeded"] is True
        assert len({result["run_request"] for result in results}) == len(results)
        captured = {key: value for key, value in results[0].items() if key != "run_request"}
        assert all({key: value for key, value in result.items() if key != "run_request"}
                   == captured for result in results)
        bundle = Path(results[0]["evidence"][0])
        before = (bundle.read_bytes(), bundle.stat().st_mtime_ns)
        repeated = capture(None)
        assert repeated.pop("run_request") not in {result["run_request"] for result in results}
        assert repeated == captured
        assert (bundle.read_bytes(), bundle.stat().st_mtime_ns) == before
    assert list(bundle.parent.iterdir()) == [bundle]
    assert bundle.stat().st_mode & 0o077 == 0


def test_cli_starts_capture_mode_and_reports_availability(operator) -> None:
    config, folder, evidence = operator
    command = [sys.executable, "-m", "agent_lab.designer", "--evidence-dir", str(evidence),
               "--draft-config", str(config)]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        assert process.stdout is not None
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            assert selector.select(timeout=15), "CLI did not report its loopback URL"
        line = process.stdout.readline()
        assert line.startswith("Open http://127.0.0.1:"), line
        port = int(line.strip().removesuffix("/").rsplit(":", 1)[1])
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
        try:
            connection.request("GET", "/api/drafts")
            response = connection.getresponse()
            assert response.status == 200
            assert json.loads(response.read()) == {
                "available": True, "run_available": True, "source": "LinkedIn draft capture"}
        finally:
            connection.close()
        assert not evidence.exists()
    finally:
        process.terminate()
        process.communicate(timeout=10)


@pytest.mark.parametrize("kind", ["missing", "malformed", "duplicate", "incomplete", "overlap"])
def test_cli_rejects_invalid_operator_configuration_before_listening(operator, kind) -> None:
    config, folder, evidence = operator
    if kind == "missing":
        config.unlink()
    elif kind == "malformed":
        config.write_text('{secret: TOP_SECRET')
    elif kind == "duplicate":
        config.write_text('{"drafts_dir":"a", "drafts_dir":"b"}')
    elif kind == "incomplete":
        manifest = json.loads(config.read_text())
        del manifest["guidance"]["guardian_checklist"]
        config.write_text(json.dumps(manifest))
    elif kind == "overlap":
        evidence = folder
    process = subprocess.run(
        [sys.executable, "-m", "agent_lab.designer", "--evidence-dir", str(evidence),
         "--draft-config", str(config)], capture_output=True, text=True, timeout=10)
    assert process.returncode == 2
    assert "Open http" not in process.stdout
    assert "error:" in process.stderr
    assert "TOP_SECRET" not in process.stderr
    assert not (evidence / "draft-snapshots").exists()


def test_draft_mode_requires_run_identity_and_exposes_no_review_routes(operator) -> None:
    config, folder, evidence = operator
    draft(folder, "old.md")
    with running_server(evidence, draft_config=config) as server:
        headers = credentials(server)
        for path in ("/api/drafts/run", "/api/drafts/request"):
            assert request(server, path, method="POST", headers=headers, body="{}")[0] == 400
        for path in ("/api/drafts/check", "/api/drafts/load"):
            assert request(server, path, method="POST", headers=headers, body="{}")[0] == 404
    assert not evidence.exists()


def test_draft_capture_preserves_controlled_source_and_offline_fixture_execution(operator) -> None:
    from tests.test_designer_roles import DEFAULT
    from tests.test_designer_source_server import BRIEF

    config, folder, evidence = operator
    draft(folder, "old.md")
    brief = config.parent / "brief.json"
    brief.write_text(json.dumps(BRIEF))
    with running_server(evidence, draft_config=config, source_file=brief) as server:
        headers = credentials(server)
        status, _, body = request(server, "/api/drafts/capture", method="POST", headers=headers, body="{}")
        assert status == 200 and json.loads(body)["selected"]["name"] == "old.md"
        status, _, body = request(server, "/api/source/capture", method="POST", headers=headers, body="{}")
        assert status == 200
        captured = json.loads(body)
        assert captured["input"] == BRIEF
        for endpoint in ("/api/source/run", "/api/source/check"):
            status, _, body = request(server, endpoint, method="POST", headers=headers,
                body=json.dumps({"design": DEFAULT, "snapshot": captured["snapshot"]}))
            assert status == 200
            result = json.loads(body)
            assert result.get("passed", result.get("succeeded")) is True
        status, _, body = request(server, "/api/check", method="POST", headers=headers, body=json.dumps(DEFAULT))
        assert status == 200 and json.loads(body)["passed"] is True
