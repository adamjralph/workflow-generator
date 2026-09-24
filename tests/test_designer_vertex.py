"""Offline tests at VertexSource's approved transport/invoke seam."""
import asyncio
import copy
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

import pytest

from agent_lab.designer.vertex import VertexError, VertexSource, VertexUncertain
from agent_lab.model_operation import ModelRequest

TOKEN = "fixture-access-token"
CREDENTIALS = {"type": "authorized_user", "client_id": "fixture-client-id",
               "client_secret": "fixture-client-secret", "refresh_token": "fixture-refresh-token"}
REPLY: dict[str, Any] = {"id": "request-123", "object": "chat.completion", "model": "reported-model",
         "choices": [{"index": 0, "finish_reason": "stop",
                      "message": {"role": "assistant", "content": "{\"verdict\":\"Approved\"}"}}],
         "usage": {"prompt_tokens": 40, "completion_tokens": 12, "total_tokens": 52,
                   "prompt_tokens_details": {"cached_tokens": 10},
                   "completion_tokens_details": {"reasoning_tokens": 3}}}


def request(**changes: object) -> ModelRequest:
    body = {"model": "google/gemini-3.1-pro-preview", "messages": [
        {"role": "system", "content": "Review faithfully."},
        {"role": "user", "content": "Original article and exact draft."}], "tools": [], "stream": False}
    body.update(changes)
    return ModelRequest(operation="review_linkedin", operation_version="1", schema_version="1",
                        input_digest="a" * 64, request_json=json.dumps(
                            body, sort_keys=True, separators=(",", ":"), ensure_ascii=False))


@pytest.fixture
def auth(tmp_path: Path) -> Path:
    path = tmp_path / "adc.json"
    path.write_text(json.dumps(CREDENTIALS))
    path.chmod(0o600)
    return path


def test_one_readonly_auth_then_one_exact_generation(auth: Path) -> None:
    original = auth.read_bytes()
    calls: list[tuple[str, bytes, dict[str, str], float]] = []

    async def transport(url: str, body: bytes, headers: dict[str, str], deadline: float) -> AsyncIterator[bytes]:
        calls.append((url, body, headers, deadline))
        if len(calls) == 1:
            yield b'{"access_token":"fixture-access-token","token_type":"Bearer","expires_in":3600}'
        else:
            yield json.dumps(REPLY).encode()

    response = VertexSource(auth, "project-123", transport=transport).invoke(request())
    assert response.body == '{"verdict":"Approved"}'
    assert (response.input_tokens, response.output_tokens, response.reasoning_tokens,
            response.cache_read_tokens) == (40, 12, 3, 10)
    assert (response.provider_request_id, response.resolved_model) == ("request-123", "reported-model")
    assert response.auth_requests == 1
    assert len(calls) == 2
    assert calls[0][0] == "https://oauth2.googleapis.com/token"
    assert "Authorization" not in calls[0][2]
    assert parse_qs(calls[0][1].decode()) == {
        "grant_type": ["refresh_token"], "client_id": ["fixture-client-id"],
        "client_secret": ["fixture-client-secret"], "refresh_token": ["fixture-refresh-token"]}
    assert calls[1][0] == "https://aiplatform.googleapis.com/v1beta1/projects/project-123/locations/global/endpoints/openapi/chat/completions"
    assert calls[1][1] == request().request_json.encode()
    assert calls[1][2]["Authorization"] == "Bearer " + TOKEN
    assert calls[0][3] == calls[1][3]
    assert auth.read_bytes() == original
    assert list(auth.parent.iterdir()) == [auth]


def test_rejects_tool_calls_hidden_outside_message(auth: Path) -> None:
    reply = {**REPLY, "tool_calls": [{"function": {"name": "steal"}}]}

    async def transport(url: str, body: bytes, headers: dict[str, str], deadline: float) -> AsyncIterator[bytes]:
        if url.endswith("/token"):
            yield b'{"access_token":"fixture-access-token","token_type":"Bearer","expires_in":3600}'
        else:
            yield json.dumps(reply).encode()

    with pytest.raises(VertexError) as failure:
        VertexSource(auth, "project-123", transport=transport).invoke(request())
    assert failure.value.code == "invalid_response_body"
    assert failure.value.auth_requests == 1


class Exchange:
    """Literal provider fixture with an observable no-retry/auth boundary."""
    def __init__(self, generation: object = REPLY, *, oauth: bytes | Exception | None = None) -> None:
        self.generation = generation
        self.oauth = oauth if oauth is not None else b'{"access_token":"fixture-access-token","token_type":"Bearer","expires_in":3600}'
        self.calls: list[str] = []

    async def __call__(self, url: str, body: bytes, headers: dict[str, str], deadline: float) -> AsyncIterator[bytes]:
        self.calls.append(url)
        result = self.oauth if url.endswith("/token") else self.generation
        if isinstance(result, Exception):
            raise result
        raw = result if isinstance(result, bytes) else json.dumps(result).encode()
        # Exercise collection across arbitrary UTF-8/JSON boundaries.
        for index in range(0, len(raw), 13):
            yield raw[index:index + 13]


@pytest.mark.parametrize(("change", "reason"), [
    (lambda reply: reply["choices"][0]["message"].update(extra_content={"google": {"opaque": True}}),
     "unknown_message_field"),
    (lambda reply: reply["usage"].update(extra_properties={"opaque": True}),
     "unsupported_usage_value"),
    (lambda reply: reply["usage"].update(total_tokens=999), "inconsistent_accounting"),
    (lambda reply: reply["choices"][0]["message"].update(content="fixture-access-token"),
     "unsafe_output"),
])
def test_vertex_rejection_has_only_sanitized_parse_reason(auth: Path, change: Any, reason: str) -> None:
    reply = copy.deepcopy(REPLY)
    change(reply)
    source = VertexSource(auth, "project-123", transport=Exchange(reply))
    with pytest.raises(VertexError) as caught:
        source.invoke(request())
    assert caught.value.code == "invalid_response_body"
    assert caught.value.parse_reason == reason
    assert "fixture-access-token" not in str(caught.value)


def test_vertex_parse_reason_is_persisted_without_response_text(auth: Path, tmp_path: Path) -> None:
    from agent_lab.designer.draft_runs import AttemptSource, Evidence

    reply = copy.deepcopy(REPLY)
    reply["choices"][0]["message"]["extra_content"] = {"private": "SECRET_REPLY_MARKER"}
    directory = tmp_path / "run"
    directory.mkdir(mode=0o700)
    attempt = AttemptSource(VertexSource(auth, "project-123", transport=Exchange(reply)),
                            Evidence(directory), {"run_request": "a" * 64, "snapshot": "b" * 64})
    with pytest.raises(ValueError, match="Model source failed"):
        attempt.invoke(request())
    assert attempt.failure is not None
    assert attempt.failure.parse_reason == "unknown_message_field"
    assert attempt.exchange is not None
    saved = attempt.exchange.read_bytes()
    assert b'"parse_reason":"unknown_message_field"' in saved
    assert b"SECRET_REPLY_MARKER" not in saved
    assert b"fixture-access-token" not in saved


def test_gemini_thinking_metadata_and_separate_reasoning_usage(auth: Path) -> None:
    reply = copy.deepcopy(REPLY)
    reply["model"] = "google/gemini-3.8-flash"
    reply["choices"][0]["message"]["extra_content"] = {"google": {"thought_signature": "opaque-signature"}}
    reply["usage"] = {"prompt_tokens": 21, "completion_tokens": 1, "total_tokens": 135,
                      "completion_tokens_details": {"reasoning_tokens": 113},
                      "extra_properties": {"google": {"traffic_type": "on_demand"}}}
    result = VertexSource(auth, "project-123", transport=Exchange(reply)).invoke(request())
    assert (result.input_tokens, result.output_tokens, result.reasoning_tokens) == (21, 1, 113)
    assert result.body == '{"verdict":"Approved"}'


def test_gemini_long_thought_signature_within_response_cap(auth: Path) -> None:
    reply = copy.deepcopy(REPLY)
    reply["model"] = "google/gemini-3.8-flash"
    reply["choices"][0]["message"]["extra_content"] = {
        "google": {"thought_signature": "S" * 10680}}
    result = VertexSource(auth, "project-123", transport=Exchange(reply)).invoke(request())
    assert result.body == '{"verdict":"Approved"}'


@pytest.mark.parametrize("model", ["google/gemini-3.1-pro-preview", "google/gemini-30-flash",
                                    "google/gemini-3.8-flash-preview", "other/gemini-3.8-flash"])
def test_unobserved_models_do_not_gain_flash_metadata_exception(auth: Path, model: str) -> None:
    reply = copy.deepcopy(REPLY)
    reply["model"] = model
    reply["choices"][0]["message"]["extra_content"] = {"google": {"thought_signature": "opaque-signature"}}
    reply["usage"] = {"prompt_tokens": 21, "completion_tokens": 1, "total_tokens": 135,
                      "completion_tokens_details": {"reasoning_tokens": 113},
                      "extra_properties": {"google": {"traffic_type": "on_demand"}}}
    with pytest.raises(VertexError) as caught:
        VertexSource(auth, "project-123", transport=Exchange(reply)).invoke(request())
    assert caught.value.code == "invalid_response_body"


@pytest.mark.parametrize("kind", ["signature-structure", "signature-empty", "traffic-structure",
                                 "traffic-control", "contradictory-total", "tool-call", "secret-in-signature"])
def test_gemini_thinking_metadata_still_fails_closed(auth: Path, kind: str) -> None:
    reply = copy.deepcopy(REPLY)
    reply["model"] = "google/gemini-3.8-flash"
    message = reply["choices"][0]["message"]
    message["extra_content"] = {"google": {"thought_signature": "opaque-signature"}}
    usage = reply["usage"]
    usage.update(prompt_tokens=21, completion_tokens=1, total_tokens=135,
                 completion_tokens_details={"reasoning_tokens": 113},
                 extra_properties={"google": {"traffic_type": "on_demand"}})
    if kind == "signature-structure":
        message["extra_content"]["google"]["tool_request"] = "hidden"
    elif kind == "signature-empty":
        message["extra_content"]["google"]["thought_signature"] = ""
    elif kind == "traffic-structure":
        usage["extra_properties"]["google"]["other"] = "hidden"
    elif kind == "traffic-control":
        usage["extra_properties"]["google"]["traffic_type"] = "\nunsafe"
    elif kind == "contradictory-total":
        usage["total_tokens"] = 134
    elif kind == "tool-call":
        message["tool_calls"] = [{"id": "unexpected"}]
    else:
        message["extra_content"]["google"]["thought_signature"] = TOKEN
    with pytest.raises(VertexError) as caught:
        VertexSource(auth, "project-123", transport=Exchange(reply)).invoke(request())
    assert caught.value.code == "invalid_response_body"


@pytest.mark.parametrize("changes", [
    {"tools": [{"type": "function"}]}, {"stream": True}, {"temperature": 0},
    {"model": ""}, {"model": 42}, {"messages": []},
    {"messages": [{"role": "user", "content": "wrong order"}]},
    {"messages": [{"role": "system", "content": "ok"}, {"role": "user", "content": [{"text": "no"}]}]},
])
def test_invalid_request_never_reads_credentials_or_authenticates(tmp_path: Path, changes: dict[str, object]) -> None:
    transport = Exchange()
    with pytest.raises(VertexError) as failure:
        VertexSource(tmp_path / "missing", "project-123", transport=transport).invoke(request(**changes))
    assert failure.value.code == "invalid_request"
    assert failure.value.auth_requests == 0
    assert transport.calls == []


@pytest.mark.parametrize("kind", ["missing", "symlink", "fifo", "directory", "large", "writable", "bad-json", "duplicate", "wrong-type", "missing-secret", "custom-url"])
def test_unsafe_credentials_fail_without_network(auth: Path, kind: str) -> None:
    if kind == "missing":
        auth.unlink()
    elif kind == "symlink":
        target = auth.with_suffix(".target")
        auth.rename(target)
        auth.symlink_to(target)
    elif kind == "fifo":
        auth.unlink()
        os.mkfifo(auth)
    elif kind == "directory":
        auth.unlink()
        auth.mkdir()
    elif kind == "large":
        auth.write_bytes(b" " * 65537)
    elif kind == "writable":
        auth.chmod(0o666)
    elif kind == "bad-json":
        auth.write_text("{secret")
    elif kind == "duplicate":
        auth.write_text('{"type":"authorized_user","type":"service_account"}')
    else:
        data = dict(CREDENTIALS)
        if kind == "wrong-type":
            data["type"] = "service_account"
        elif kind == "missing-secret":
            del data["refresh_token"]
        else:
            data["token_uri"] = "https://secret.invalid/token"
        auth.write_text(json.dumps(data))
    transport = Exchange()
    with pytest.raises(VertexError) as failure:
        VertexSource(auth, "project-123", transport=transport).invoke(request())
    assert failure.value.code == "credentials_unavailable"
    assert failure.value.auth_requests == 0
    assert transport.calls == []
    assert "secret.invalid" not in str(failure.value)


@pytest.mark.parametrize("oauth", [b"{}", b"[]", b'{"error":"fixture-refresh-token"}',
    b'{"access_token":"bad\\r\\nheader","token_type":"Bearer","expires_in":3600}',
    b'{"access_token":"ok","token_type":"Basic","expires_in":3600}',
    b'{"access_token":"ok","token_type":"Bearer","expires_in":0}', b"x" * 65537,
    VertexError("fixture-client-secret", code="provider_rejected", provider_status=401),
    TimeoutError("fixture-refresh-token"), OSError("fixture-client-secret")])
def test_auth_failure_never_generates_or_retries(auth: Path, oauth: bytes | Exception) -> None:
    transport = Exchange(oauth=oauth)
    with pytest.raises((VertexError, VertexUncertain)) as failure:
        VertexSource(auth, "project-123", transport=transport).invoke(request())
    assert transport.calls == ["https://oauth2.googleapis.com/token"]
    assert isinstance(failure.value, (VertexError, VertexUncertain))
    assert failure.value.auth_requests == 1
    assert all(secret not in str(failure.value) for secret in CREDENTIALS.values())
    if isinstance(oauth, VertexError):
        assert failure.value.provider_status == 401


@pytest.mark.parametrize("failure", [VertexError("unsafe", code="provider_rejected", provider_status=429),
    VertexUncertain("unsafe", code="deadline_exceeded", provider_status=504),
    TimeoutError("unsafe"), ConnectionError("unsafe")])
def test_generation_failures_are_sanitized_and_never_retried(auth: Path, failure: Exception) -> None:
    transport = Exchange(failure)
    with pytest.raises((VertexError, VertexUncertain)) as caught:
        VertexSource(auth, "project-123", transport=transport).invoke(request())
    assert isinstance(caught.value, (VertexError, VertexUncertain))
    assert caught.value.auth_requests == 1
    assert len(transport.calls) == 2
    assert "unsafe" not in str(caught.value)
    if isinstance(failure, (VertexError, VertexUncertain)):
        assert caught.value.code == failure.code
        assert caught.value.provider_status == failure.provider_status


@pytest.mark.parametrize("kind", ["tool", "function", "refusal", "length", "two-choices", "bad-role", "empty", "bad-usage", "bool-usage", "negative-usage", "bad-details", "inconsistent-total", "excess-reasoning", "secret", "escaped-secret", "secret-metadata", "bad-json", "duplicate", "oversize"])
def test_malformed_or_secret_response_fails_closed(auth: Path, kind: str) -> None:
    data = copy.deepcopy(REPLY)
    choice = data["choices"][0]
    message = choice["message"]
    raw: object = data
    if kind == "tool":
        message["tool_calls"] = [{"id": "call-1"}]
    elif kind == "function":
        message["function_call"] = {"name": "run"}
    elif kind == "refusal":
        message["refusal"] = "no"
    elif kind == "length":
        choice["finish_reason"] = "length"
    elif kind == "two-choices":
        data["choices"].append(copy.deepcopy(choice))
    elif kind == "bad-role":
        message["role"] = "user"
    elif kind == "empty":
        message["content"] = ""
    elif kind == "bad-usage":
        data["usage"] = []
    elif kind == "bool-usage":
        data["usage"]["prompt_tokens"] = True
    elif kind == "negative-usage":
        data["usage"]["prompt_tokens"] = -1
    elif kind == "bad-details":
        data["usage"]["completion_tokens_details"] = "no"
    elif kind == "inconsistent-total":
        data["usage"]["total_tokens"] = 999
    elif kind == "excess-reasoning":
        data["usage"]["completion_tokens_details"]["reasoning_tokens"] = 13
    elif kind in ("secret", "escaped-secret"):
        message["content"] = "Echo " + TOKEN
        if kind == "escaped-secret":
            raw = json.dumps(data).replace("fixture", "\\u0066ixture").encode()
    elif kind == "secret-metadata":
        data["id"] = "fixture-refresh-token"
    elif kind == "bad-json":
        raw = b"{"
    elif kind == "duplicate":
        raw = b'{"choices":[],"choices":[]}'
    elif kind == "oversize":
        raw = b" " * 65537
    transport = Exchange(raw)
    with pytest.raises(VertexError) as caught:
        VertexSource(auth, "project-123", transport=transport).invoke(request())
    assert caught.value.auth_requests == 1
    assert caught.value.code == ("response_limit" if kind == "oversize" else "invalid_response_body")
    assert len(transport.calls) == 2
    assert TOKEN not in str(caught.value)


def test_unknown_usage_is_not_fabricated(auth: Path) -> None:
    data = copy.deepcopy(REPLY)
    del data["usage"]
    del data["id"]
    del data["model"]
    response = VertexSource(auth, "project-123", "us-central1", transport=Exchange(data)).invoke(request())
    assert (response.input_tokens, response.output_tokens, response.reasoning_tokens,
            response.cache_read_tokens, response.provider_request_id, response.resolved_model) == (None,) * 6


@pytest.mark.parametrize("phase", ["auth", "generation"])
def test_deadline_includes_authentication(auth: Path, monkeypatch: pytest.MonkeyPatch, phase: str) -> None:
    monkeypatch.setattr("agent_lab.designer.vertex.REQUEST_TIMEOUT", 0.04)
    calls: list[str] = []

    async def slow(url: str, body: bytes, headers: dict[str, str], deadline: float) -> AsyncIterator[bytes]:
        calls.append(url)
        if phase == "generation" and url.endswith("/token"):
            yield b'{"access_token":"fixture-access-token","token_type":"Bearer","expires_in":3600}'
            return
        await asyncio.sleep(1)
        yield b"{}"

    started = time.monotonic()
    with pytest.raises(VertexUncertain) as caught:
        VertexSource(auth, "project-123", transport=slow).invoke(request())
    assert time.monotonic() - started < 0.5
    assert caught.value.code == "deadline_exceeded"
    assert caught.value.auth_requests == 1
    assert calls[0] == "https://oauth2.googleapis.com/token"
    assert len(calls) == (1 if phase == "auth" else 2)


def test_slow_credential_open_cannot_send_late(auth: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("agent_lab.designer.vertex.REQUEST_TIMEOUT", 0.04)
    original = os.open
    released = threading.Event()
    finished = threading.Event()

    def slow_open(path: Any, flags: int, *args: Any, **kwargs: Any) -> int:
        released.wait(1)
        result = original(path, flags, *args, **kwargs)
        finished.set()
        return result

    monkeypatch.setattr(os, "open", slow_open)
    transport = Exchange()
    try:
        with pytest.raises(VertexUncertain) as caught:
            VertexSource(auth, "project-123", transport=transport).invoke(request())
        assert caught.value.auth_requests == 0
    finally:
        released.set()
    assert finished.wait(1)
    time.sleep(0.05)
    assert transport.calls == []


def test_secret_escaped_inside_semantic_json_body_is_rejected(auth: Path) -> None:
    data = copy.deepcopy(REPLY)
    data["choices"][0]["message"]["content"] = '{"secret":"fixture\\u002daccess-token"}'
    with pytest.raises(VertexError):
        VertexSource(auth, "project-123", transport=Exchange(data)).invoke(request())


def test_unused_credential_tokens_cannot_echo_in_generation(auth: Path) -> None:
    auth.write_text(json.dumps({**CREDENTIALS, "id_token": "unused-identity-secret"}))
    data = copy.deepcopy(REPLY)
    data["choices"][0]["message"]["content"] = "unused-identity-secret"
    with pytest.raises(VertexError):
        VertexSource(auth, "project-123", transport=Exchange(data)).invoke(request())


def test_non_utf8_oauth_is_rejected_before_generation(auth: Path) -> None:
    raw = '{"access_token":"fixture-access-token","token_type":"Bearer","expires_in":3600}'.encode("utf-16")
    transport = Exchange(oauth=raw)
    with pytest.raises(VertexError):
        VertexSource(auth, "project-123", transport=transport).invoke(request())
    assert len(transport.calls) == 1


@pytest.mark.parametrize("status", [302, 401, 429, 500, 504])
def test_default_transport_never_follows_redirects_or_retries(auth: Path, monkeypatch: pytest.MonkeyPatch, status: int) -> None:
    connected: list[str] = []
    sent: list[bytes] = []

    class Writer:
        def write(self, data: bytes) -> None:
            sent.append(data)

        async def drain(self) -> None:
            pass

        def close(self) -> None:
            pass

    async def connect(host: str, port: int, **kwargs: Any) -> tuple[asyncio.StreamReader, Writer]:
        connected.append(host)
        assert port == 443
        assert kwargs["server_hostname"] == host
        assert kwargs["ssl"].check_hostname
        reader = asyncio.StreamReader()
        reader.feed_data(f"HTTP/1.1 {status} Ignored\r\nLocation: https://secret.invalid\r\n\r\n".encode())
        reader.feed_eof()
        return reader, Writer()

    monkeypatch.setenv("HTTPS_PROXY", "https://proxy.invalid:443")
    monkeypatch.setattr(asyncio, "open_connection", connect)
    with pytest.raises((VertexError, VertexUncertain)) as caught:
        VertexSource(auth, "project-123").invoke(request())
    assert isinstance(caught.value, (VertexError, VertexUncertain))
    assert caught.value.provider_status == status
    assert caught.value.auth_requests == 1
    assert connected == ["oauth2.googleapis.com"]
    assert len(sent) == 1
    assert b"POST /token HTTP/1.1" in sent[0]
    assert "secret.invalid" not in str(caught.value)


@pytest.mark.parametrize("framing", ["length", "chunked", "eof"])
def test_default_transport_collects_bounded_json_without_proxy(auth: Path, monkeypatch: pytest.MonkeyPatch, framing: str) -> None:
    connected: list[str] = []
    sent: list[bytes] = []

    class Writer:
        def write(self, data: bytes) -> None:
            sent.append(data)

        async def drain(self) -> None:
            pass

        def close(self) -> None:
            pass

    async def connect(host: str, port: int, **kwargs: Any) -> tuple[asyncio.StreamReader, Writer]:
        connected.append(host)
        data = (b'{"access_token":"fixture-access-token","token_type":"Bearer","expires_in":3600}'
                if len(connected) == 1 else json.dumps(REPLY).encode())
        head = b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n"
        if framing == "length":
            head += f"Content-Length: {len(data)}\r\n".encode()
        elif framing == "chunked":
            head += b"Transfer-Encoding: chunked\r\n"
            data = f"{len(data):x}\r\n".encode() + data + b"\r\n0\r\n\r\n"
        reader = asyncio.StreamReader()
        reader.feed_data(head + b"\r\n" + data)
        reader.feed_eof()
        return reader, Writer()

    monkeypatch.setenv("HTTPS_PROXY", "https://proxy.invalid:443")
    monkeypatch.setattr(asyncio, "open_connection", connect)
    response = VertexSource(auth, "project-123", "us-central1").invoke(request())
    assert response.body == '{"verdict":"Approved"}'
    assert connected == ["oauth2.googleapis.com", "us-central1-aiplatform.googleapis.com"]
    assert b"Authorization:" not in sent[0]
    assert b"fixture-client-secret" not in sent[1]
    assert b"Authorization: Bearer fixture-access-token" in sent[1]


def test_concurrent_invocations_have_independent_auth_accounting(auth: Path) -> None:
    source = VertexSource(auth, "project-123", transport=Exchange())
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(source.invoke, request()) for _ in range(2)]
    assert [future.result().auth_requests for future in futures] == [1, 1]
