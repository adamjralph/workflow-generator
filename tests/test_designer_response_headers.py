"""Public provider adapters with synthetic HTTP bytes; no live credentials/network."""
import asyncio
import json

import pytest

from agent_lab.designer.codex import CodexError, CodexSource
from agent_lab.designer.vertex import VertexError, VertexSource
from agent_lab.model_operation import ModelRequest
from tests.test_designer_codex import credentials, request as codex_request, completed
from tests.test_designer_vertex import CREDENTIALS, REPLY, request as vertex_request


def provider(tmp_path, kind):
    auth = tmp_path / "auth.json"
    if kind == "codex":
        credentials(auth)
        return CodexSource(auth), codex_request()
    auth.write_text(json.dumps(CREDENTIALS))
    auth.chmod(0o600)
    return VertexSource(auth, "project-fixture"), vertex_request()


def http_responses(monkeypatch, kind, extra="", *, target="generation", body=None, framing=None,
                   chunk_extension=None, trailers=b""):
    calls = []

    class Writer:
        def write(self, data):
            pass

        async def drain(self):
            pass

        def close(self):
            pass

    async def connect(host, port, **kwargs):
        calls.append(host)
        oauth = host == "oauth2.googleapis.com"
        payload = (json.dumps({"access_token": "synthetic-access", "token_type": "Bearer", "expires_in": 3600}).encode()
                   if oauth else completed() if kind == "codex" else json.dumps(REPLY).encode())
        selected = oauth == (target == "oauth")
        if selected and body is not None:
            payload = body
        mime = "text/event-stream" if kind == "codex" else "application/json"
        headers = f"Content-Type: {mime}\r\nContent-Length: {len(payload)}\r\n"
        if selected and framing is not None:
            headers = f"Content-Type: {mime}\r\n" + framing
        if selected and chunk_extension is not None:
            headers = f"Content-Type: {mime}\r\nTransfer-Encoding: chunked\r\n"
            payload = (f"{len(payload):x}".encode() + chunk_extension + b"\r\n" + payload
                       + b"\r\n0\r\n" + trailers + b"\r\n")
        wire = ("HTTP/1.1 200 OK\r\n" + headers + (extra if selected else "") + "\r\n").encode() + payload
        reader = asyncio.StreamReader()
        reader.feed_data(wire)
        reader.feed_eof()
        return reader, Writer()

    monkeypatch.setattr(asyncio, "open_connection", connect)
    return calls


@pytest.mark.parametrize("kind,target", [("codex", "generation"), ("vertex", "generation"), ("vertex", "oauth")])
@pytest.mark.parametrize("header", ["Set-Cookie", "Cache-Control", "Vary", "Warning", "Link", "Server-Timing", "Via", "Allow", "Accept-Ranges",
                                    "Content-Language", "Pragma", "Accept-Patch", "Accept-Post", "Alt-Svc", "Preference-Applied"])
def test_repeated_metadata_does_not_block_valid_response(tmp_path, monkeypatch, kind, target, header):
    source, request = provider(tmp_path, kind)
    before = (tmp_path / "auth.json").read_bytes()
    first, second = ("en", "fr") if header == "Content-Language" else ("PRIVATE_COOKIE=a", "PRIVATE_COOKIE=b")
    calls = http_responses(monkeypatch, kind, f"{header}: {first}\r\n{header.lower()}: {second}\r\n", target=target)
    result = source.invoke(request)
    assert result.body == (" Exact text\n" if kind == "codex" else '{"verdict":"Approved"}')
    assert "PRIVATE_COOKIE" not in result.model_dump_json()
    assert len(calls) == (1 if kind == "codex" else 2)
    assert (tmp_path / "auth.json").read_bytes() == before


@pytest.mark.parametrize("kind", ["codex", "vertex"])
@pytest.mark.parametrize("extra", [
    "Content-Length: 1\r\n", "cOnTeNt-TyPe: text/plain\r\n",
    "Content-Encoding: identity\r\nContent-Encoding: identity\r\n",
    "Transfer-Encoding: chunked\r\nTransfer-Encoding: chunked\r\n",
    "Location: /a\r\nLocation: /b\r\n", "Content-Type : text/plain\r\n",
    " folded: PRIVATE_HEADER\r\n", "Bad Header: PRIVATE_HEADER\r\n",
    "X-Test: PRIVATE_HEADER\x00\r\n",
])
def test_invalid_headers_have_sanitized_stage(tmp_path, monkeypatch, kind, extra):
    source, request = provider(tmp_path, kind)
    calls = http_responses(monkeypatch, kind, extra)
    with pytest.raises((CodexError, VertexError)) as caught:
        source.invoke(request)
    assert caught.value.code == "invalid_http_headers"
    assert caught.value.provider_status == 200
    assert "PRIVATE_HEADER" not in str(caught.value)
    assert caught.value.__context__ is None
    assert len(calls) == (1 if kind == "codex" else 2)


@pytest.mark.parametrize("kind,target,code", [
    ("codex", "generation", "invalid_response_body"),
    ("vertex", "generation", "invalid_response_body"),
    ("vertex", "oauth", "invalid_auth_response"),
])
def test_response_validation_stages_are_distinct_and_sanitized(tmp_path, monkeypatch, kind, target, code):
    source, request = provider(tmp_path, kind)
    body = (b'event: error\ndata: {"type":"error","message":"PRIVATE_BODY"}\n\n'
            if kind == "codex" else b'{"error":"PRIVATE_BODY"}')
    calls = http_responses(monkeypatch, kind, body=body, target=target)
    with pytest.raises((CodexError, VertexError)) as caught:
        source.invoke(request)
    assert caught.value.code == code
    assert "PRIVATE_BODY" not in str(caught.value)
    assert caught.value.__context__ is None
    assert len(calls) == (2 if kind == "vertex" and target == "generation" else 1)
    if kind == "vertex":
        assert caught.value.auth_requests == 1


@pytest.mark.parametrize("kind", ["codex", "vertex"])
def test_invalid_request_is_distinct_and_never_connects(tmp_path, monkeypatch, kind):
    source, request = provider(tmp_path, kind)
    calls = http_responses(monkeypatch, kind)
    invalid = ModelRequest.model_validate({**request.model_dump(), "request_json": '{"SECRET_REQUEST":true}'})
    with pytest.raises((CodexError, VertexError)) as caught:
        source.invoke(invalid)
    assert caught.value.code == "invalid_request"
    assert not calls
    assert "SECRET_REQUEST" not in str(caught.value)


@pytest.mark.parametrize("kind", ["codex", "vertex"])
@pytest.mark.parametrize("extension,trailers", [
    (b";bad=\x00", b""), (b";", b""), (b';key="unfinished', b""),
    (b"", b"not a header\r\n"),
    (b"", b"Content-Length: 7\r\nContent-Length: 8\r\n"),
    (b"", b"Transfer-Encoding: chunked\r\n"),
    (b"", b"Content-Type: text/plain\r\n"),
    (b"", b"Authorization: PRIVATE_TRAILER\r\n"),
    (b"", b" folded: PRIVATE_TRAILER\r\n"),
    (b"", b"X-Test: PRIVATE_TRAILER\x00\r\n"),
])
def test_invalid_chunk_extensions_and_trailers_fail_closed(tmp_path, monkeypatch, kind, extension, trailers):
    source, request = provider(tmp_path, kind)
    http_responses(monkeypatch, kind, chunk_extension=extension, trailers=trailers)
    with pytest.raises((CodexError, VertexError)) as caught:
        source.invoke(request)
    assert caught.value.code == "invalid_http_framing"
    assert "PRIVATE_TRAILER" not in str(caught.value)


@pytest.mark.parametrize("kind", ["codex", "vertex"])
def test_valid_chunk_extensions_and_metadata_trailers_are_discarded(tmp_path, monkeypatch, kind):
    source, request = provider(tmp_path, kind)
    http_responses(monkeypatch, kind, chunk_extension=b'; name = "escaped\\\\value"; flag',
                   trailers=b"Server-Timing: PRIVATE_TRAILER\r\nServer-Timing: second\r\n")
    result = source.invoke(request)
    assert "PRIVATE_TRAILER" not in result.model_dump_json()


@pytest.mark.parametrize("kind", ["codex", "vertex"])
@pytest.mark.parametrize("framing,body", [
    ("Content-Length: 1\r\nTransfer-Encoding: chunked\r\n", b"x"),
    ("Transfer-Encoding: \r\n", b"x"),
    ("Content-Length: +1\r\n", b"x"),
    ("Transfer-Encoding: chunked\r\n", b"+1\r\nx\r\n0\r\n\r\n"),
    ("Transfer-Encoding: chunked\r\n", b"1\r\nxXX0\r\n\r\n"),
])
def test_ambiguous_framing_has_distinct_stage(tmp_path, monkeypatch, kind, framing, body):
    source, request = provider(tmp_path, kind)
    calls = http_responses(monkeypatch, kind, framing=framing, body=body)
    with pytest.raises((CodexError, VertexError)) as caught:
        source.invoke(request)
    assert caught.value.code == "invalid_http_framing"
    assert caught.value.provider_status == 200
    assert len(calls) == (1 if kind == "codex" else 2)
