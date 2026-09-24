import base64
import json
import time
import asyncio
import os

import pytest
from pathlib import Path
from typing import AsyncIterator

from agent_lab.designer.codex import CodexError, CodexSource
from agent_lab.model_operation import ModelRequest


def credentials(path: Path, exp: float | None = None) -> str:
    claims = {"exp": exp if exp is not None else time.time() + 3600,
              "https://api.openai.com/auth": {"chatgpt_account_id": "fixture-account"}}
    token = "header." + base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=") + ".signature"
    path.write_text(json.dumps({"providers": {"openai-codex": {"tokens": {
        "access_token": token, "refresh_token": "fixture-refresh", "id_token": "fixture-id"}}}}))
    return token


def request() -> ModelRequest:
    return ModelRequest(operation="draft", operation_version="1", schema_version="1",
                        input_digest="digest", request_json=json.dumps({"model": "gpt-5-codex",
                        "instructions": "Write text", "input": "Hello", "tools": [],
                        "store": False, "stream": True}, sort_keys=True, separators=(",", ":")))


def completed(**extra: object) -> bytes:
    response = {"id": "resp_fixture", "model": "gpt-5-codex", "status": "completed",
                "output": [{"type": "message", "role": "assistant", "status": "completed",
                            "content": [{"type": "output_text", "text": " Exact text\n"}]}], **extra}
    return ("event: response.completed\ndata: " + json.dumps({"type": "response.completed", "response": response}) + "\n\n").encode()


def test_exact_text_and_unknown_usage_read_only(tmp_path: Path) -> None:
    auth = tmp_path / "auth.json"
    token = credentials(auth)
    before = auth.read_bytes()
    calls = []

    async def transport(body: bytes, headers: dict[str, str], deadline: float) -> AsyncIterator[bytes]:
        calls.append(body)
        assert headers["Authorization"] == "Bearer " + token
        assert headers["ChatGPT-Account-ID"] == "fixture-account"
        assert 0 < deadline - time.monotonic() <= 180
        data = completed()
        for pos in range(0, len(data), 7):
            yield data[pos:pos + 7]

    source = CodexSource(auth, transport=transport)
    result = source.invoke(request())
    assert source.mode == "live"
    assert result.body == " Exact text\n"
    assert result.provider_request_id == "resp_fixture"
    assert result.resolved_model == "gpt-5-codex"
    assert result.input_tokens is result.output_tokens is result.reasoning_tokens is result.cache_read_tokens is None
    assert calls == [request().request_json.encode()]
    assert auth.read_bytes() == before
    assert list(tmp_path.iterdir()) == [auth]


def test_stream_lifecycle_and_usage(tmp_path: Path) -> None:
    auth = tmp_path / "auth.json"
    credentials(auth)

    async def transport(body: bytes, headers: dict[str, str], deadline: float) -> AsyncIterator[bytes]:
        for obj in [
            {"type": "response.created", "response": {"id": "resp_fixture", "status": "in_progress"}},
            {"type": "response.in_progress", "response": {"id": "resp_fixture", "status": "in_progress"}},
            {"type": "response.output_item.added", "output_index": 0, "item": {
                "id": "msg_1", "type": "message", "role": "assistant", "status": "in_progress", "content": []}},
            {"type": "response.content_part.added", "output_index": 0, "content_index": 0,
             "part": {"type": "output_text", "text": ""}},
            {"type": "response.output_text.delta", "output_index": 0, "content_index": 0, "delta": " Exact text\n"},
            {"type": "response.output_text.done", "output_index": 0, "content_index": 0, "text": " Exact text\n"},
        ]:
            yield ("data: " + json.dumps(obj) + "\n\n").encode()
        yield completed(usage={"input_tokens": 12, "output_tokens": 8,
                               "input_tokens_details": {"cached_tokens": 4},
                               "output_tokens_details": {"reasoning_tokens": 3}})

    result = CodexSource(auth, transport=transport).invoke(request())
    assert result.body == " Exact text\n"
    assert (result.input_tokens, result.output_tokens, result.reasoning_tokens, result.cache_read_tokens) == (12, 8, 3, 4)


def test_codex_wire_input_items_pass_through_exactly(tmp_path: Path) -> None:
    auth = tmp_path / "auth.json"
    credentials(auth)
    original = request()
    body = json.loads(original.request_json)
    body["input"] = [{"role": "user", "content": [{"type": "input_text", "text": "Hello"}]}]
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":"))
    actual = original.model_copy(update={"request_json": encoded})
    calls = []

    async def transport(body: bytes, headers: dict[str, str], deadline: float) -> AsyncIterator[bytes]:
        calls.append(body)
        yield completed()

    assert CodexSource(auth, transport=transport).invoke(actual).body == " Exact text\n"
    assert calls == [encoded.encode()]


@pytest.mark.parametrize("change", [{"tools": [{"type": "web_search"}]}, {"store": True},
                                  {"stream": False}, {"input": [{"type": "function_call", "name": "bad"}]}])
def test_reject_unsafe_request_before_transport(tmp_path: Path, change: dict[str, object]) -> None:
    auth = tmp_path / "auth.json"
    credentials(auth)
    called = []

    async def transport(body: bytes, headers: dict[str, str], deadline: float) -> AsyncIterator[bytes]:
        called.append(True)
        yield completed()

    original = request()
    body = {**json.loads(original.request_json), **change}
    altered = original.model_copy(update={"request_json": json.dumps(body, sort_keys=True, separators=(",", ":"))})
    with pytest.raises(CodexError):
        CodexSource(auth, transport=transport).invoke(altered)
    assert not called


@pytest.mark.parametrize("state", ["missing", "expired", "malformed", "no-exp", "pool-only"])
def test_bad_credentials_operator_action_no_transport_or_writes(tmp_path: Path, state: str) -> None:
    auth = tmp_path / "auth.json"
    if state == "expired":
        credentials(auth, time.time() - 1)
    elif state == "malformed":
        auth.write_text("secret-malformed-auth")
    elif state == "no-exp":
        auth.write_text(json.dumps({"providers": {"openai-codex": {"tokens": {"access_token": "a.e30.c"}}}}))
    elif state == "pool-only":
        auth.write_text(json.dumps({"credential_pool": {"openai-codex": []}}))
    before = auth.read_bytes() if auth.exists() else None
    called = []

    async def transport(body: bytes, headers: dict[str, str], deadline: float) -> AsyncIterator[bytes]:
        called.append(True)
        yield completed()

    with pytest.raises(CodexError, match="hermes auth") as error:
        CodexSource(auth, transport=transport).invoke(request())
    assert "secret-malformed-auth" not in str(error.value)
    assert error.value.__context__ is None
    assert not called
    assert (auth.read_bytes() if auth.exists() else None) == before
    assert len(list(tmp_path.iterdir())) == (0 if before is None else 1)


@pytest.mark.parametrize("data", [
    b"data: {}\n\n", b"data: {broken}\n\n", completed() + completed(),
    completed(status="incomplete"), completed(output=[]),
    completed(output=[{"type": "function_call"}]),
    completed(output=[{"type": "message"}, {"type": "message"}]),
    completed(usage={"input_tokens": True}), completed(usage={"output_tokens": -1}),
    b'data: {"type":"response.failed","response":{"status":"failed"}}\n\n',
    b'data: {"type":"response.in_progress","response":{"id":"r","status":"queued"}}\n\n' + completed(),
    b'data: {"type":"response.function_call_arguments.delta","delta":"x"}\n\n' + completed(),
    b'data: {"type":"response.completed","type":"response.completed","response":' + completed().split(b'"response": ', 1)[1],
])
def test_reject_invalid_complete_envelopes(tmp_path: Path, data: bytes) -> None:
    auth = tmp_path / "auth.json"
    credentials(auth)
    calls = []

    async def transport(body: bytes, headers: dict[str, str], deadline: float) -> AsyncIterator[bytes]:
        calls.append(True)
        yield data

    with pytest.raises(CodexError):
        CodexSource(auth, transport=transport).invoke(request())
    assert calls == [True]


@pytest.mark.parametrize("field", ["body", "model", "id"])
@pytest.mark.parametrize("secret_kind", ["access", "refresh", "identity"])
def test_credential_echo_never_escapes(tmp_path: Path, field: str, secret_kind: str) -> None:
    auth = tmp_path / "auth.json"
    access = credentials(auth)
    secret = {"access": access, "refresh": "fixture-refresh", "identity": "fixture-id"}[secret_kind]
    extra: dict[str, object] = {field: secret}
    if field == "body":
        extra = {"output": [{"type": "message", "role": "assistant", "status": "completed",
                              "content": [{"type": "output_text", "text": "prefix " + secret}]}]}

    async def transport(body: bytes, headers: dict[str, str], deadline: float) -> AsyncIterator[bytes]:
        yield completed(**extra)

    with pytest.raises(CodexError) as error:
        CodexSource(auth, transport=transport).invoke(request())
    assert secret not in str(error.value)
    assert error.value.__cause__ is None


@pytest.mark.parametrize("overflow", [False, True])
def test_complete_stream_envelope_limit(tmp_path: Path, overflow: bool) -> None:
    auth = tmp_path / "auth.json"
    credentials(auth)
    final = completed()
    data = b":" + b" " * (524288 - len(final) - 3 + int(overflow)) + b"\n\n" + final

    async def transport(body: bytes, headers: dict[str, str], deadline: float) -> AsyncIterator[bytes]:
        for pos in range(0, len(data), 4096):
            yield data[pos:pos + 4096]

    source = CodexSource(auth, transport=transport)
    if overflow:
        with pytest.raises(CodexError):
            source.invoke(request())
    else:
        assert source.invoke(request()).body == " Exact text\n"


@pytest.mark.parametrize("when", ["headers", "body", "after-completion"])
def test_absolute_deadline_bounds_entire_stream(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, when: str) -> None:
    # Time is a system seam: shrink 180s to exercise a real wall-clock timeout.
    monkeypatch.setattr("agent_lab.designer.codex.REQUEST_TIMEOUT", 0.05)
    auth = tmp_path / "auth.json"
    credentials(auth)
    calls = []

    async def transport(body: bytes, headers: dict[str, str], deadline: float) -> AsyncIterator[bytes]:
        calls.append(True)
        if when == "headers":
            await asyncio.sleep(1)
        elif when == "after-completion":
            yield completed()
            await asyncio.sleep(1)
        else:
            for _ in range(100):
                yield b": keepalive\n\n"
                await asyncio.sleep(0.01)
        yield completed()

    started = time.monotonic()
    with pytest.raises(TimeoutError) as error:
        CodexSource(auth, transport=transport).invoke(request())
    assert error.value.__context__ is None
    assert time.monotonic() - started < 0.5
    assert calls == [True]


def test_transport_error_sanitized_and_never_retried(tmp_path: Path) -> None:
    auth = tmp_path / "auth.json"
    token = credentials(auth)
    calls = []

    async def transport(body: bytes, headers: dict[str, str], deadline: float) -> AsyncIterator[bytes]:
        calls.append(True)
        raise RuntimeError(token)
        yield b""  # pragma: no cover

    with pytest.raises(TimeoutError) as error:
        CodexSource(auth, transport=transport).invoke(request())
    assert token not in str(error.value)
    assert error.value.__context__ is None
    assert calls == [True]


@pytest.mark.parametrize("state", ["fifo", "oversized", "directory"])
def test_credentials_must_be_bounded_regular_file(tmp_path: Path, state: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("agent_lab.designer.codex.REQUEST_TIMEOUT", 0.05)
    auth = tmp_path / "auth.json"
    if state == "fifo":
        os.mkfifo(auth)
    elif state == "directory":
        auth.mkdir()
    else:
        credentials(auth)
        with auth.open("ab") as stream:
            stream.write(b" " * 1048576)
    calls = []

    async def transport(body: bytes, headers: dict[str, str], deadline: float) -> AsyncIterator[bytes]:
        calls.append(True)
        yield completed()

    with pytest.raises(CodexError, match="hermes auth"):
        CodexSource(auth, transport=transport).invoke(request())
    assert not calls


def test_credential_read_uses_whole_deadline_without_late_send(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import threading
    auth = tmp_path / "auth.json"
    credentials(auth)
    monkeypatch.setattr("agent_lab.designer.codex.REQUEST_TIMEOUT", 0.05)
    real_open = os.open
    finished = threading.Event()
    calls = []

    def slow_open(*args, **kwargs):
        time.sleep(0.15)
        fd = real_open(*args, **kwargs)
        finished.set()
        return fd

    monkeypatch.setattr("agent_lab.designer.codex.os.open", slow_open)

    async def transport(body: bytes, headers: dict[str, str], deadline: float) -> AsyncIterator[bytes]:
        calls.append(True)
        yield completed()

    started = time.monotonic()
    with pytest.raises(TimeoutError):
        CodexSource(auth, transport=transport).invoke(request())
    assert time.monotonic() - started < 0.12
    assert finished.wait(1)
    time.sleep(0.02)
    assert not calls


@pytest.mark.parametrize("usage", [[], False, "", {"input_tokens_details": []}, {"output_tokens_details": False}])
def test_malformed_usage_is_not_unknown(tmp_path: Path, usage: object) -> None:
    auth = tmp_path / "auth.json"
    credentials(auth)

    async def transport(body: bytes, headers: dict[str, str], deadline: float) -> AsyncIterator[bytes]:
        yield completed(usage=usage)

    with pytest.raises(CodexError):
        CodexSource(auth, transport=transport).invoke(request())


@pytest.mark.parametrize("events", [
    [{"type": "response.output_item.added", "output_index": 0, "item": {
        "type": "message", "role": "assistant", "status": "in_progress", "content": []}}] * 2,
    [{"type": "response.content_part.done", "output_index": 0, "content_index": 0,
      "part": {"type": "output_text", "text": "wrong"}}],
    [{"type": "response.output_item.done", "output_index": 0, "item": {
        "type": "message", "role": "assistant", "status": "completed",
        "content": [{"type": "output_text", "text": "wrong"}]}}],
    [{"type": "response.output_text.delta", "output_index": False, "content_index": 0, "delta": " Exact text\n"}],
])
def test_reject_contradictory_lifecycle(tmp_path: Path, events: list[dict[str, object]]) -> None:
    auth = tmp_path / "auth.json"
    credentials(auth)

    async def transport(body: bytes, headers: dict[str, str], deadline: float) -> AsyncIterator[bytes]:
        for event in events:
            yield ("data: " + json.dumps(event) + "\n\n").encode()
        yield completed()

    with pytest.raises(CodexError):
        CodexSource(auth, transport=transport).invoke(request())


@pytest.mark.parametrize("framing", ["length", "chunked", "eof", "truncated", "rejected", "redirect", "request-timeout", "gateway-timeout", "wrong-type", "encoded", "ambiguous"])
def test_default_http_transport_without_network(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, framing: str) -> None:
    auth = tmp_path / "auth.json"
    token = credentials(auth)
    payload = completed()
    status = {"rejected": "401 Unauthorized", "redirect": "307 Temporary Redirect",
              "request-timeout": "408 Request Timeout", "gateway-timeout": "504 Gateway Timeout"}.get(framing, "200 OK")
    headers = "Content-Type: text/event-stream\r\n"
    body = payload
    if framing in ("length", "truncated", "ambiguous"):
        headers += f"Content-Length: {len(payload)}\r\n"
        if framing == "truncated":
            body = payload[:-10]
    if framing in ("chunked", "ambiguous"):
        headers += "Transfer-Encoding: chunked\r\n"
        body = f"{len(payload):x}\r\n".encode() + payload + b"\r\n0\r\n\r\n"
    if framing == "wrong-type":
        headers = "Content-Type: application/json\r\n"
    if framing == "encoded":
        headers += "Content-Encoding: gzip\r\n"
    wire = f"HTTP/1.1 {status}\r\n{headers}\r\n".encode() + body
    connections = []

    class Writer:
        closed = False
        sent = b""

        def write(self, data: bytes) -> None:
            self.sent += data

        async def drain(self) -> None:
            pass

        def close(self) -> None:
            self.closed = True

    writer = Writer()

    async def connect(*args, **kwargs):
        connections.append(args)
        reader = asyncio.StreamReader()
        reader.feed_data(wire)
        reader.feed_eof()
        return reader, writer

    monkeypatch.setattr(asyncio, "open_connection", connect)
    source = CodexSource(auth)
    if framing in ("length", "chunked", "eof"):
        assert source.invoke(request()).body == " Exact text\n"
    else:
        error_type = TimeoutError if framing in ("truncated", "request-timeout", "gateway-timeout") else CodexError
        with pytest.raises(error_type) as error:
            source.invoke(request())
        assert token not in str(error.value)
        assert error.value.__context__ is None
    assert connections == [("chatgpt.com", 443)]
    assert writer.closed
    assert writer.sent.endswith(request().request_json.encode())


@pytest.mark.parametrize("data", [b"", b": keepalive\n\n", completed()[:-1],
    b'data: {"type":"response.created","response":{"id":"r","status":"in_progress"}}\n\n'])
def test_unfinished_exchange_is_uncertain(tmp_path: Path, data: bytes) -> None:
    auth = tmp_path / "auth.json"
    credentials(auth)
    calls = []

    async def transport(body: bytes, headers: dict[str, str], deadline: float) -> AsyncIterator[bytes]:
        calls.append(True)
        yield data

    with pytest.raises(TimeoutError) as error:
        CodexSource(auth, transport=transport).invoke(request())
    assert error.value.__context__ is None
    assert calls == [True]


def reasoning_events() -> list[dict]:
    reasoning = {"id": "rs_1", "type": "reasoning", "summary": []}
    message = {"id": "msg_1", "type": "message", "role": "assistant", "status": "completed",
               "content": [{"type": "output_text", "text": " Exact text\n"}]}
    return [
        {"type": "response.output_item.added", "output_index": 0, "item": reasoning},
        {"type": "response.output_item.done", "output_index": 0, "item": reasoning},
        {"type": "response.output_item.added", "output_index": 1,
         "item": {**message, "status": "in_progress", "content": []}},
        {"type": "response.output_text.delta", "output_index": 1, "content_index": 0,
         "item_id": "msg_1", "delta": " Exact text\n"},
        {"type": "response.output_item.done", "output_index": 1, "item": message},
        {"type": "response.completed", "response": {"id": "resp_1", "model": "gpt-5.6-sol",
         "status": "completed", "output": [reasoning, message], "usage": {
             "input_tokens": 12, "output_tokens": 8, "input_tokens_details": {"cached_tokens": 4},
             "output_tokens_details": {"reasoning_tokens": 3}}}},
    ]


def test_native_reasoning_then_assistant(tmp_path: Path) -> None:
    auth = tmp_path / "auth.json"
    credentials(auth)

    async def transport(body: bytes, headers: dict[str, str], deadline: float) -> AsyncIterator[bytes]:
        for event in reasoning_events():
            yield ("data: " + json.dumps(event) + "\n\n").encode()

    result = CodexSource(auth, transport=transport).invoke(request())
    assert result.body == " Exact text\n"
    assert result.resolved_model == "gpt-5.6-sol"
    assert result.provider_request_id == "resp_1"
    assert (result.input_tokens, result.output_tokens, result.reasoning_tokens, result.cache_read_tokens) == (12, 8, 3, 4)


@pytest.mark.parametrize("summary", [False, True])
def test_reasoning_summary_and_optional_metadata(tmp_path: Path, summary: bool) -> None:
    auth = tmp_path / "auth.json"
    credentials(auth)
    events = reasoning_events()
    if summary:
        part = {"type": "summary_text", "text": "Thinking privately."}
        events[1]["item"] = {**events[1]["item"], "summary": [part]}
        events[-1]["response"]["output"][0] = events[1]["item"]
        events[1:1] = [
            {"type": "response.reasoning_summary_part.added", "output_index": 0,
             "item_id": "rs_1", "summary_index": 0, "part": {**part, "text": ""}},
            {"type": "response.reasoning_summary_text.delta", "output_index": 0,
             "item_id": "rs_1", "summary_index": 0, "delta": "Thinking "},
            {"type": "response.reasoning_summary_text.delta", "output_index": 0,
             "item_id": "rs_1", "summary_index": 0, "delta": "privately."},
            {"type": "response.reasoning_summary_text.done", "output_index": 0,
             "item_id": "rs_1", "summary_index": 0, "text": part["text"]},
            {"type": "response.reasoning_summary_part.done", "output_index": 0,
             "item_id": "rs_1", "summary_index": 0, "part": part},
        ]
    del events[-1]["response"]["id"]
    del events[-1]["response"]["model"]

    async def transport(body: bytes, headers: dict[str, str], deadline: float) -> AsyncIterator[bytes]:
        for event in events:
            yield ("data: " + json.dumps(event) + "\n\n").encode()

    result = CodexSource(auth, transport=transport).invoke(request())
    assert result.body == " Exact text\n"
    assert result.provider_request_id is result.resolved_model is None


@pytest.mark.parametrize("invalid", ["tool", "second-message", "refusal", "incomplete", "summary-shape",
                                      "wrong-index", "wrong-id", "unknown-reasoning-event", "metadata", "bound",
                                      "reasoning-extra"])
def test_reasoning_does_not_weaken_validation(tmp_path: Path, invalid: str) -> None:
    auth = tmp_path / "auth.json"
    credentials(auth)
    events = reasoning_events()
    response = events[-1]["response"]
    if invalid == "tool":
        response["output"].append({"type": "function_call", "name": "shell", "arguments": "{}"})
    elif invalid == "second-message":
        response["output"].append(response["output"][1])
    elif invalid == "refusal":
        response["output"][1]["content"] = [{"type": "refusal", "refusal": "No"}]
    elif invalid == "incomplete":
        response["output"][0]["status"] = "incomplete"
    elif invalid == "summary-shape":
        response["output"][0]["summary"] = [{"type": "output_text", "text": "Not a summary"}]
    elif invalid == "wrong-index":
        events[3]["output_index"] = 0
    elif invalid == "wrong-id":
        events[3]["item_id"] = "other-message"
    elif invalid == "unknown-reasoning-event":
        events.insert(1, {"type": "response.reasoning_unknown.delta", "delta": "hidden"})
    elif invalid == "metadata":
        response["model"] = 42
    elif invalid == "reasoning-extra":
        response["output"][0]["content"] = [{"type": "function_call"}]
    else:
        response["output"][0]["encrypted_content"] = "x" * 524288

    async def transport(body: bytes, headers: dict[str, str], deadline: float) -> AsyncIterator[bytes]:
        for event in events:
            yield ("data: " + json.dumps(event) + "\n\n").encode()

    with pytest.raises(CodexError):
        CodexSource(auth, transport=transport).invoke(request())
