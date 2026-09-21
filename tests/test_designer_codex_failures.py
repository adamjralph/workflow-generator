"""Failure classifications exposed to AttemptSource, without provider secrets."""
import asyncio

import pytest

from agent_lab.designer import codex
from tests.test_designer_codex import credentials, request


@pytest.mark.parametrize("case, error, code, status", [
    ("malformed", codex.CodexError, "invalid_response_body", None),
    ("limit", codex.CodexError, "response_limit", None),
    ("timeout", codex.CodexUncertain, "deadline_exceeded", None),
    ("unfinished", codex.CodexUncertain, "transport_incomplete", None),
    ("transport", codex.CodexUncertain, "transport_incomplete", None),
    ("rejected", codex.CodexError, "provider_rejected", 401),
])
def test_typed_sanitized_failure(tmp_path, case, error, code, status):
    auth = tmp_path / "auth.json"
    token = credentials(auth)
    calls = []

    async def transport(body, headers, deadline):
        calls.append(body)
        if case == "timeout":
            raise TimeoutError(token)
        if case == "transport":
            raise OSError(token)
        if case == "rejected":
            raise codex.CodexError(token, code="provider_rejected", provider_status=401)
        yield {"malformed": b'data: {"secret":"fixture-refresh"}\n\n',
               "limit": b"x" * (codex.STREAM_LIMIT + 1),
               "unfinished": b"data: "}[case]

    with pytest.raises(error) as caught:
        codex.CodexSource(auth, transport=transport).invoke(request())
    failure = caught.value
    assert failure.code == code
    assert failure.provider_status == status
    assert token not in str(failure)
    assert "fixture-refresh" not in str(failure)
    assert failure.__context__ is None
    assert failure.__cause__ is None
    assert len(calls) == 1


@pytest.mark.parametrize("status", [401, 403, 429, 500, 408, 504])
def test_http_failure_status_survives_queue(tmp_path, monkeypatch, status):
    auth = tmp_path / "auth.json"
    token = credentials(auth)

    class Writer:
        def write(self, data):
            pass

        async def drain(self):
            pass

        def close(self):
            pass

    async def connect(*args, **kwargs):
        reader = asyncio.StreamReader()
        reader.feed_data(f"HTTP/1.1 {status} {token}\r\n\r\n{token}".encode())
        reader.feed_eof()
        return reader, Writer()

    monkeypatch.setattr(asyncio, "open_connection", connect)
    error = codex.CodexUncertain if status in (408, 504) else codex.CodexError
    with pytest.raises(error) as caught:
        codex.CodexSource(auth).invoke(request())
    assert caught.value.code == ("deadline_exceeded" if status in (408, 504) else "provider_rejected")
    assert caught.value.provider_status == status
    assert token not in str(caught.value)


@pytest.mark.parametrize("unsafe", ["symlink", "owner"])
def test_auth_boundary_rejects_without_transport_or_writes(tmp_path, monkeypatch, unsafe):
    auth = tmp_path / "auth.json"
    credentials(auth)
    before = auth.read_bytes()
    selected = auth
    if unsafe == "symlink":
        selected = tmp_path / "linked.json"
        selected.symlink_to(auth)
    else:
        monkeypatch.setattr(codex.os, "getuid", lambda: auth.stat().st_uid + 1)
    calls = []

    async def transport(*args):
        calls.append(args)
        yield b""

    with pytest.raises(codex.CodexError) as caught:
        codex.CodexSource(selected, transport=transport).invoke(request())
    assert caught.value.code == "credentials_unavailable"
    assert caught.value.provider_status is None
    assert not calls
    assert auth.read_bytes() == before
    if unsafe == "symlink":
        assert selected.is_symlink()


@pytest.mark.parametrize("framing", ["length", "chunk", "headers"])
def test_http_envelope_limits_are_classified(tmp_path, monkeypatch, framing):
    auth = tmp_path / "auth.json"
    credentials(auth)

    class Writer:
        def write(self, data):
            pass

        async def drain(self):
            pass

        def close(self):
            pass

    async def connect(*args, **kwargs):
        reader = asyncio.StreamReader(limit=codex.STREAM_LIMIT)
        head = b"HTTP/1.1 200 OK\r\nContent-Type: text/event-stream\r\n"
        if framing == "length":
            wire = head + f"Content-Length: {codex.STREAM_LIMIT + 1}\r\n\r\n".encode()
        elif framing == "chunk":
            wire = head + b"Transfer-Encoding: chunked\r\n\r\n10001\r\n"
        else:
            wire = head + b"X-Large: " + b"x" * codex.STREAM_LIMIT + b"\r\n\r\n"
        reader.feed_data(wire)
        reader.feed_eof()
        return reader, Writer()

    monkeypatch.setattr(asyncio, "open_connection", connect)
    with pytest.raises(codex.CodexError) as caught:
        codex.CodexSource(auth).invoke(request())
    assert caught.value.code == "response_limit"


def test_local_deadline_is_classified(tmp_path, monkeypatch):
    auth = tmp_path / "auth.json"
    credentials(auth)
    monkeypatch.setattr(codex, "REQUEST_TIMEOUT", 0.02)

    async def transport(*args):
        await asyncio.sleep(1)
        yield b""

    with pytest.raises(codex.CodexUncertain) as caught:
        codex.CodexSource(auth, transport=transport).invoke(request())
    assert caught.value.code == "deadline_exceeded"
    assert caught.value.provider_status is None
