"""Public HTTP runs with real adapters over synthetic HTTP response bytes."""
import json
from pathlib import Path

import pytest

from tests.test_designer_drafts import draft, operator  # noqa: F401
from tests.test_designer_draft_run_server import FixtureSource, capture, post
from tests.test_designer_response_headers import http_responses, provider
from tests.test_designer_review_server import GuardianSource
from tests.test_designer_server import running_server


@pytest.mark.parametrize("kind,target", [("codex", "generation"), ("vertex", "generation"), ("vertex", "oauth")])
@pytest.mark.parametrize("head,code,status", [
    (b"PRIVATE_STATUS\r\n\r\n", "invalid_http_status", None),
    (b"HTTP/1.1 200 OK\r\nPRIVATE_HEADER\r\n\r\n", "invalid_http_header", 200),
    (b"HTTP/1.1 200 OK\r\nX-Private: PRIVATE_VALUE\r\nx-private: PRIVATE_COOKIE\r\n\r\n",
     "duplicate_http_header", 200),
    (b"HTTP/1.1 200 OK\r\nContent-Type: PRIVATE_MIME\r\n\r\n", "unsupported_http_content_type", 200),
    (b"HTTP/1.1 200 OK\r\n\r\n", "missing_http_content_type", 200),
    (b"HTTP/1.1 200 OK\r\nContent-Type: \t\r\n\r\n", "empty_http_content_type", 200),
    (b"HTTP/1.1 200 OK\r\nContent-Type: {mime}\r\nContent-Encoding: PRIVATE_ENCODING\r\n\r\n",
     "unsupported_http_content_encoding", 200),
])
def test_wire_rule_survives_run_receipt_duplicate_and_offline_check(
        operator, tmp_path, monkeypatch, kind, target, head, code, status):
    config, folder, evidence = operator
    draft(folder, "old.md")
    source, _ = provider(tmp_path, kind)
    role = "generator" if kind == "codex" else "guardian"
    provider_name = "openai-codex" if kind == "codex" else "vertex"
    (config.parent / f"{role}.yaml").write_text(f"model:\n  provider: {provider_name}\n  default: fixture-model\n")
    originals = {p: p.read_bytes() for p in config.parent.rglob("*") if p.is_file()}
    auth_before = (tmp_path / "auth.json").read_bytes()
    mime = b"text/event-stream" if kind == "codex" else b"application/json"
    calls = http_responses(monkeypatch, kind, target=target, response_head=head.replace(b"{mime}", mime))
    guardian = GuardianSource() if kind == "codex" else source
    generator = source if kind == "codex" else FixtureSource()
    with running_server(evidence, draft_config=config, draft_model_source=generator,
                        guardian_model_source=guardian) as server:
        identity = capture(server)
        http_status, result = post(server, "/api/drafts/run", identity)
        assert http_status == 200 and result["status"] == "failed"
        assert result["failure"] == {
            "status": "failed", "code": code, "provider_status": status,
            "header_observation": {
                "version": 1, "section_bytes": len(head.replace(b"{mime}", mime)),
                "field_lines": {"invalid_http_status": 0, "missing_http_content_type": 0,
                                "duplicate_http_header": 2, "unsupported_http_content_encoding": 2}.get(code, 1),
                "content_type": code in {"unsupported_http_content_type", "empty_http_content_type",
                                         "unsupported_http_content_encoding"},
                "content_length": False, "transfer_encoding": False,
                "content_encoding": code == "unsupported_http_content_encoding",
            },
        }
        assert result["auth_requests"] == (0 if kind == "codex" else 1)
        assert result["review"] is None
        assert (result["result"] is None) == (kind == "codex")
        receipt_path = Path(result["evidence"][-1])
        receipt = json.loads(receipt_path.read_text())
        assert receipt["view"] == result
        exchange = json.loads((receipt_path.parent / receipt["exchanges"][-1]).read_text())
        assert exchange["failure"] == result["failure"]
        saved = {p: p.read_bytes() for p in evidence.rglob("*") if p.is_file()}
        assert all(b"PRIVATE_" not in raw for raw in saved.values())
        assert "PRIVATE_" not in json.dumps(result)

        def deny_network(*args, **kwargs):
            raise AssertionError("Offline inspection must not contact providers")

        monkeypatch.setattr("asyncio.open_connection", deny_network)
        assert post(server, "/api/drafts/run", identity) == (http_status, result)
        check = post(server, "/api/drafts/check", identity)[1]
        assert not check["passed"] and check["findings"][0]["code"] == "invalid_recording"
        assert check["evidence"] == []
        assert all(p.read_bytes() == raw for p, raw in saved.items())
    assert len(calls) == (2 if kind == "vertex" and target == "generation" else 1)
    if kind == "codex":
        assert guardian.requests == []
    assert all(p.read_bytes() == raw for p, raw in originals.items())
    assert (tmp_path / "auth.json").read_bytes() == auth_before
