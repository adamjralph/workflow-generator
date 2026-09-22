"""Approved public adapter and durable-failure seams; synthetic inputs only."""
import asyncio
import socket

import pytest
from pydantic import ValidationError

from agent_lab.model_operation import ModelFailure

from agent_lab.designer.codex import CodexError
from agent_lab.designer.vertex import VertexError
from tests.test_designer_response_headers import http_responses, provider


@pytest.fixture(autouse=True)
def deny_real_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("Real network and DNS are forbidden")

    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket.socket, "connect_ex", denied)
    monkeypatch.setattr(socket, "getaddrinfo", denied)


@pytest.mark.parametrize("kind,target", [("codex", "generation"), ("vertex", "generation"), ("vertex", "oauth")])
def test_missing_type_reports_empty_first_section(tmp_path, monkeypatch, kind, target):
    source, request = provider(tmp_path, kind)
    calls = http_responses(monkeypatch, kind, target=target,
                           response_head=b"HTTP/1.1 200 OK\r\n\r\n")
    if kind == "codex":
        assert source.invoke(request).body == " Exact text\n"
        assert calls == ["chatgpt.com"]
        return
    with pytest.raises((CodexError, VertexError)) as caught:
        source.invoke(request)
    assert caught.value.code == "missing_http_content_type"
    assert caught.value.provider_status == 200
    assert caught.value.header_observation.model_dump() == {
        "version": 1, "section_bytes": 19, "field_lines": 0,
        "content_type": False, "content_length": False,
        "transfer_encoding": False, "content_encoding": False,
    }
    assert len(calls) == (2 if kind == "vertex" and target == "generation" else 1)


@pytest.mark.parametrize("kind,target", [("codex", "generation"), ("vertex", "generation"), ("vertex", "oauth")])
@pytest.mark.parametrize("head,code,status,count,flags", [
    (b"HTTP/1.1 200 OK\r\nDate: PRIVATE_DATE\r\nSet-Cookie: PRIVATE_ONE\r\nset-cookie: PRIVATE_TWO\r\nContent-Length: 0\r\n\r\n",
     "missing_http_content_type", 200, 4, (False, True, False, False)),
    (b"HTTP/1.1 200 OK\r\ncOnTeNt-TyPe: PRIVATE_MIME\r\nContent-Length: 0\r\nTransfer-Encoding: chunked\r\nContent-Encoding: gzip\r\n\r\n",
     "unsupported_http_content_type", 200, 4, (True, True, True, True)),
    (b"HTTP/1.1 200 OK\r\nPRIVATE_BROKEN\r\nContent-Type: PRIVATE_MIME\r\n\r\n",
     "invalid_http_header", 200, 2, (True, False, False, False)),
    (b"HTTP/1.1 200 OK\r\nContent-Type: first\r\ncontent-type: second\r\n\r\n",
     "duplicate_http_header", 200, 2, (True, False, False, False)),
    (b"HTTP/1.1 103 Early Hints\r\nLink: PRIVATE_LINK\r\n\r\n",
     "provider_rejected", 103, 1, (False, False, False, False)),
    (b"HTTP/1.1 408 Timeout\r\n\r\n", "deadline_exceeded", 408, 0, (False, False, False, False)),
    (b"PRIVATE_STATUS\r\nContent-Type: PRIVATE_MIME\r\n\r\n",
     "invalid_http_status", None, 1, (True, False, False, False)),
    (b"HTTP/1.1 200 OK\r\n Content-Type: PRIVATE_MIME\r\nContent-Length : 0\r\n\r\n",
     "invalid_http_header", 200, 2, (False, False, False, False)),
])
def test_rejection_observes_only_first_section(tmp_path, monkeypatch, kind, target, head, code, status, count, flags):
    from agent_lab.designer.codex import CodexUncertain
    from agent_lab.designer.vertex import VertexUncertain

    source, request = provider(tmp_path, kind)
    auth = (tmp_path / "auth.json").read_bytes()
    calls = http_responses(monkeypatch, kind, target=target, response_head=head,
                           body=b"HTTP/1.1 200 OK\r\nContent-Type: PRIVATE_SECOND\r\n\r\nPRIVATE_BODY")
    connect = asyncio.open_connection
    reads, closed, writes = [], [], []

    async def guarded_connect(host, port, **kwargs):
        reader, writer = await connect(host, port, **kwargs)
        selected = (host == "oauth2.googleapis.com") == (target == "oauth")
        if not selected:
            return reader, writer

        class FirstSectionOnly:
            async def readuntil(self, delimiter):
                assert not reads and delimiter == b"\r\n\r\n"
                reads.append(delimiter)
                return await reader.readuntil(delimiter)

            async def read(self, size):
                raise AssertionError("Must not inspect body or second response")

            async def readexactly(self, size):
                raise AssertionError("Must not inspect body or second response")

        class ClosingWriter:
            def write(self, data):
                writes.append(data)
                writer.write(data)

            async def drain(self):
                await writer.drain()

            def close(self):
                closed.append(True)
                writer.close()

        return FirstSectionOnly(), ClosingWriter()

    monkeypatch.setattr(asyncio, "open_connection", guarded_connect)
    with pytest.raises((CodexError, VertexError, CodexUncertain, VertexUncertain)) as caught:
        source.invoke(request)
    failure = caught.value
    if kind == "codex" and code == "missing_http_content_type":
        # Accepted absent MIME, but declared zero-length body cannot complete SSE.
        assert (failure.code, failure.provider_status) == ("transport_incomplete", None)
        assert failure.header_observation is None
        assert len(reads) == len(closed) == len(writes) == len(calls) == 1
        assert "PRIVATE_" not in str(failure)
        assert (tmp_path / "auth.json").read_bytes() == auth
        return
    assert (failure.code, failure.provider_status) == (code, status)
    assert failure.header_observation.model_dump() == {
        "version": 1, "section_bytes": len(head), "field_lines": count,
        "content_type": flags[0], "content_length": flags[1],
        "transfer_encoding": flags[2], "content_encoding": flags[3],
    }
    assert len(reads) == len(closed) == len(writes) == 1
    assert len(calls) == (2 if kind == "vertex" and target == "generation" else 1)
    assert b"PRIVATE_" not in failure.header_observation.model_dump_json().encode()
    assert "PRIVATE_" not in str(failure)
    assert (tmp_path / "auth.json").read_bytes() == auth


@pytest.mark.parametrize("kind,target", [("codex", "generation"), ("vertex", "generation"), ("vertex", "oauth")])
@pytest.mark.parametrize("case", ["oversized", "incomplete", "framing", "body"])
def test_no_observation_outside_rejected_bounded_headers(tmp_path, monkeypatch, kind, target, case):
    from agent_lab.designer.codex import CodexUncertain
    from agent_lab.designer.vertex import VertexUncertain

    source, request = provider(tmp_path, kind)
    mime = b"text/event-stream" if kind == "codex" else b"application/json"
    if case == "oversized":
        head = b"HTTP/1.1 200 OK\r\nX: " + b"x" * 65536 + b"\r\n\r\n"
    elif case == "incomplete":
        head = b"HTTP/1.1 200 OK\r\n"
    else:
        head = b"HTTP/1.1 200 OK\r\nContent-Type: " + mime + b"\r\nContent-Length: "
        head += b"PRIVATE_LENGTH\r\n\r\n" if case == "framing" else b"0\r\n\r\n"
    http_responses(monkeypatch, kind, target=target, response_head=head, body=b"")
    with pytest.raises((CodexError, VertexError, CodexUncertain, VertexUncertain)) as caught:
        source.invoke(request)
    assert caught.value.header_observation is None
    assert caught.value.code == {
        "oversized": "response_limit", "incomplete": "transport_incomplete",
        "framing": "invalid_http_framing",
        "body": ("invalid_auth_response" if target == "oauth" else
                 "transport_incomplete" if kind == "codex" else "invalid_response_body"),
    }[case]


@pytest.mark.parametrize("kind,target", [("codex", "generation"), ("vertex", "generation"), ("vertex", "oauth")])
@pytest.mark.parametrize("size", [65536, 65537])
def test_header_observation_limit_is_inclusive(tmp_path, monkeypatch, kind, target, size):
    from agent_lab.designer.codex import CodexUncertain

    source, request = provider(tmp_path, kind)
    head = b"HTTP/1.1 200 OK\r\nX: " + b"x" * (size - 24) + b"\r\n\r\n"
    assert len(head) == size
    http_responses(monkeypatch, kind, target=target, response_head=head, body=b"")
    with pytest.raises((CodexError, VertexError, CodexUncertain)) as caught:
        source.invoke(request)
    if size == 65536 and kind == "codex":
        assert caught.value.code == "transport_incomplete"
        assert caught.value.header_observation is None
    elif size == 65536:
        assert caught.value.code == "missing_http_content_type"
        assert caught.value.header_observation.model_dump() == {
            "version": 1, "section_bytes": 65536, "field_lines": 1,
            "content_type": False, "content_length": False,
            "transfer_encoding": False, "content_encoding": False,
        }
    else:
        assert caught.value.code == "response_limit"
        assert caught.value.header_observation is None


def test_historical_failure_roundtrip_omits_observation():
    historical = {"status": "failed", "code": "missing_http_content_type", "provider_status": 200}
    assert ModelFailure.model_validate(historical).model_dump() == historical


@pytest.mark.parametrize("change", [
    {"version": 2}, {"version": True}, {"section_bytes": 65537}, {"section_bytes": -1},
    {"section_bytes": True}, {"field_lines": -1}, {"field_lines": 32767},
    {"content_type": "false"}, {"content_type": 0}, {"raw": "PRIVATE_DATA"},
])
def test_persisted_failure_rejects_unapproved_observation_schema(change):
    observation = {"version": 1, "section_bytes": 19, "field_lines": 0,
                   "content_type": False, "content_length": False,
                   "transfer_encoding": False, "content_encoding": False, **change}
    with pytest.raises(ValidationError):
        ModelFailure.model_validate({"status": "failed", "code": "missing_http_content_type",
                                     "provider_status": 200, "header_observation": observation})
