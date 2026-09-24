"""Synthetic regressions for the approved Codex protocol exception; no live calls."""
import copy
import json

import pytest

from agent_lab.designer.codex import CodexError, CodexUncertain
from tests.test_designer_response_headers import http_responses, provider


def events(*, empty=True, reasoning=False):
    message = {"id": "msg_1", "type": "message", "role": "assistant", "status": "completed",
               "content": [{"type": "output_text", "text": " Exact text\n"}]}
    index = int(reasoning)
    items = ([{"id": "rs_1", "type": "reasoning", "summary": []}] if reasoning else []) + [message]
    stream = [{"type": "response.created", "response": {"id": "resp_1", "status": "in_progress"}}]
    if reasoning:
        stream += [{"type": "response.output_item.added", "output_index": 0, "item": copy.deepcopy(items[0])},
                   {"type": "response.output_item.done", "output_index": 0, "item": copy.deepcopy(items[0])}]
    stream += [
        {"type": "response.output_item.added", "output_index": index,
         "item": {**message, "status": "in_progress", "content": []}},
        {"type": "response.content_part.added", "output_index": index, "content_index": 0,
         "item_id": "msg_1", "part": {"type": "output_text", "text": ""}},
        {"type": "response.output_text.delta", "output_index": index, "content_index": 0,
         "item_id": "msg_1", "delta": " Exact text\n"},
        {"type": "response.output_text.done", "output_index": index, "content_index": 0,
         "item_id": "msg_1", "text": " Exact text\n"},
        {"type": "response.content_part.done", "output_index": index, "content_index": 0,
         "item_id": "msg_1", "part": copy.deepcopy(message["content"][0])},
        {"type": "response.output_item.done", "output_index": index, "item": copy.deepcopy(message)},
        {"type": "response.completed", "response": {"id": "resp_1", "model": "gpt-5.6-sol",
         "status": "completed", "output": [] if empty else copy.deepcopy(items),
         "usage": {"input_tokens": 32, "output_tokens": 5}}},
    ]
    return stream


def wire(stream):
    return b"".join(("event: " + event["type"] + "\ndata: " + json.dumps(event) + "\n\n").encode()
                    for event in stream)


@pytest.mark.parametrize("empty", [False, True])
@pytest.mark.parametrize("reasoning", [False, True])
@pytest.mark.parametrize("mime", [False, True])
@pytest.mark.parametrize("framing", ["close", "length", "chunked"])
def test_completed_items_and_missing_mime(tmp_path, monkeypatch, empty, reasoning, mime, framing):
    source, request = provider(tmp_path, "codex")
    before = (tmp_path / "auth.json").read_bytes()
    body = wire(events(empty=empty, reasoning=reasoning))
    headers = b"Content-Type: text/event-stream\r\n" if mime else b""
    if framing == "length":
        headers += f"Content-Length: {len(body)}\r\n".encode()
    elif framing == "chunked":
        headers += b"Transfer-Encoding: chunked\r\n"
        body = f"{len(body):x}\r\n".encode() + body + b"\r\n0\r\n\r\n"
    calls = http_responses(monkeypatch, "codex", body=body,
                           response_head=b"HTTP/1.1 200 OK\r\n" + headers + b"\r\n")
    result = source.invoke(request)
    assert result.body == " Exact text\n"
    assert result.provider_request_id == "resp_1"
    assert result.resolved_model == "gpt-5.6-sol"
    assert (result.input_tokens, result.output_tokens) == (32, 5)
    assert (tmp_path / "auth.json").read_bytes() == before
    assert calls == ["chatgpt.com"]


@pytest.mark.parametrize("empty,location", [(True, "added"), (True, "done"),
                                              (False, "added"), (False, "final")])
@pytest.mark.parametrize("content", [[], ["hidden"], {}, None])
def test_reasoning_content_only_accepts_literal_empty_list(tmp_path, monkeypatch, empty, location, content):
    source, request = provider(tmp_path, "codex")
    stream = events(empty=empty, reasoning=True)
    if location == "final":
        # Nonempty final output is authoritative; it needs no streamed reasoning
        # item. Removing those events isolates final-item validation from equality.
        stream = [event for event in stream if event.get("output_index") != 0]
        stream[-1]["response"]["output"][0]["content"] = copy.deepcopy(content)
    else:
        kind = "response.output_item." + location
        next(event for event in stream if event["type"] == kind and event["output_index"] == 0)["item"]["content"] = copy.deepcopy(content)
        if not empty:  # Make valid controls agree with completed streamed item.
            stream[-1]["response"]["output"][0]["content"] = []
            next(event for event in stream if event["type"] == "response.output_item.done" and event["output_index"] == 0)["item"]["content"] = ([] if location == "added" else copy.deepcopy(content))
    calls = http_responses(monkeypatch, "codex", body=wire(stream))
    if content == []:
        assert source.invoke(request).body == " Exact text\n"
    else:
        with pytest.raises(CodexError) as caught:
            source.invoke(request)
        assert caught.value.code == "invalid_response_body"
    assert calls == ["chatgpt.com"]


def test_large_sse_envelope_does_not_raise_parsed_response_limit(tmp_path, monkeypatch):
    source, request = provider(tmp_path, "codex")
    body = b":" + b" " * 70000 + b"\n\n" + wire(events(empty=True, reasoning=True))
    calls = http_responses(monkeypatch, "codex", body=body)
    assert source.invoke(request).body == " Exact text\n"
    assert calls == ["chatgpt.com"]


@pytest.mark.parametrize("empty", [False, True])
@pytest.mark.parametrize("overflow", [False, True])
def test_parsed_text_remains_bounded_independent_of_sse_limit(tmp_path, monkeypatch, empty, overflow):
    source, request = provider(tmp_path, "codex")
    stream = events(empty=empty)
    text = "x" * 65534 + "é" + ("x" if overflow else "")  # 65536/65537 UTF-8 bytes.
    for event in stream:
        kind = event["type"]
        if kind == "response.output_text.delta":
            event["delta"] = text
        elif kind == "response.output_text.done":
            event["text"] = text
        elif kind == "response.content_part.done":
            event["part"]["text"] = text
        elif kind == "response.output_item.done":
            event["item"]["content"][0]["text"] = text
    if not empty:
        stream[-1]["response"]["output"][0]["content"][0]["text"] = text
    calls = http_responses(monkeypatch, "codex", body=wire(stream))
    if overflow:
        with pytest.raises(CodexError) as caught:
            source.invoke(request)
        assert caught.value.code == "response_limit"
    else:
        assert source.invoke(request).body == text
    assert calls == ["chatgpt.com"]


@pytest.mark.parametrize("framing", ["length", "chunked", "close"])
@pytest.mark.parametrize("overflow", [False, True])
def test_raw_sse_http_framing_limit(tmp_path, monkeypatch, framing, overflow):
    source, request = provider(tmp_path, "codex")
    final = wire(events())
    payload = b":" + b" " * (524288 - len(final) - 3 + int(overflow)) + b"\n\n" + final
    assert len(payload) == 524288 + int(overflow)
    headers = b"Content-Type: text/event-stream\r\n"
    if framing == "length":
        headers += f"Content-Length: {len(payload)}\r\n".encode()
    elif framing == "chunked":
        headers += b"Transfer-Encoding: chunked\r\n"
        payload = f"{len(payload):x}\r\n".encode() + payload + b"\r\n0\r\nServer-Timing: bounded\r\n\r\n"
    calls = http_responses(monkeypatch, "codex", body=payload,
                           response_head=b"HTTP/1.1 200 OK\r\n" + headers + b"\r\n")
    if overflow:
        with pytest.raises(CodexError) as caught:
            source.invoke(request)
        assert caught.value.code == "response_limit"
    else:
        assert source.invoke(request).body == " Exact text\n"
    assert calls == ["chatgpt.com"]


@pytest.mark.parametrize("empty", [False, True])
@pytest.mark.parametrize("invalid", [
    "duplicate-done", "duplicate-added", "wrong-item-id", "wrong-added-id", "wrong-response-id",
    "event-response-id", "gap", "negative-index", "bool-index", "wrong-content-index",
    "delta-conflict", "text-done-conflict", "part-done-conflict", "incomplete-item",
    "tool", "refusal", "failed", "interrupted", "late-item-event", "late-item-content-event",
    "late-response-event",
    "malformed-sse", "duplicate-item-id", "second-message", "secret-text",
    "final-conflict", "added-text-conflict", "added-part-conflict",
])
def test_invalid_streams_fail_closed(tmp_path, monkeypatch, empty, invalid):
    source, request = provider(tmp_path, "codex")
    stream = events(empty=empty)
    added, part, delta, text_done, part_done, done, final = stream[1:]
    expected = CodexError
    if invalid == "duplicate-done":
        stream.insert(-1, copy.deepcopy(done))
    elif invalid == "duplicate-added":
        stream.insert(2, copy.deepcopy(added))
    elif invalid == "wrong-item-id":
        delta["item_id"] = "other"
    elif invalid == "wrong-added-id":
        added["item"]["id"] = "other"
    elif invalid == "wrong-response-id":
        final["response"]["id"] = "other"
    elif invalid == "event-response-id":
        delta["response_id"] = "other"
    elif invalid in ("gap", "negative-index", "bool-index"):
        for event in stream[1:-1]:
            event["output_index"] = {"gap": 2, "negative-index": -1, "bool-index": True}[invalid]
    elif invalid == "wrong-content-index":
        delta["content_index"] = 1
    elif invalid == "delta-conflict":
        delta["delta"] = "PRIVATE_CONTRADICTION"
    elif invalid == "text-done-conflict":
        text_done["text"] = "PRIVATE_CONTRADICTION"
    elif invalid == "part-done-conflict":
        part_done["part"]["text"] = "PRIVATE_CONTRADICTION"
    elif invalid == "incomplete-item":
        done["item"]["status"] = "in_progress"
    elif invalid == "tool":
        done["item"]["type"] = "function_call"
    elif invalid == "refusal":
        done["item"]["content"] = [{"type": "refusal", "refusal": "PRIVATE_REFUSAL"}]
    elif invalid == "failed":
        final["type"] = "response.failed"
    elif invalid == "interrupted":
        stream.pop()
        expected = CodexUncertain
    elif invalid == "late-item-event":
        stream.insert(-1, stream.pop(3))
    elif invalid == "late-item-content-event":
        # The part text is consistent, so only item completion can reject this.
        stream.insert(-1, stream.pop(2))
    elif invalid == "late-response-event":
        stream.append(copy.deepcopy(delta))
    elif invalid == "duplicate-item-id":
        reason = {"type": "response.output_item.done", "output_index": 1,
                  "item": {"type": "reasoning", "id": "msg_1", "summary": []}}
        stream.insert(-1, reason)
        if not empty:
            final["response"]["output"].append(copy.deepcopy(reason["item"]))
    elif invalid == "second-message":
        other = copy.deepcopy(done)
        other["output_index"] = 1
        other["item"]["id"] = "msg_2"
        stream.insert(-1, other)
        if not empty:
            final["response"]["output"].append(copy.deepcopy(other["item"]))
    elif invalid == "secret-text":
        # Agreement must not let an echoed credential escape the public seam.
        delta["delta"] = text_done["text"] = part_done["part"]["text"] = "fixture-refresh"
        done["item"]["content"][0]["text"] = "fixture-refresh"
        if not empty:
            final["response"]["output"][0]["content"][0]["text"] = "fixture-refresh"
    elif invalid == "final-conflict":
        final["response"]["output"] = [copy.deepcopy(done["item"])]
        final["response"]["output"][0]["content"][0]["text"] = "PRIVATE_CONTRADICTION"
    elif invalid == "added-text-conflict":
        added["item"]["content"] = [{"type": "output_text", "text": "PRIVATE_CONTRADICTION"}]
    elif invalid == "added-part-conflict":
        part["part"]["text"] = "PRIVATE_CONTRADICTION"
    body = wire(stream)
    if invalid == "malformed-sse":
        body = body.replace(b"event: response.created", b"event: wrong", 1)
    calls = http_responses(monkeypatch, "codex", body=body)
    with pytest.raises(expected) as caught:
        source.invoke(request)
    assert caught.value.code == ("transport_incomplete" if expected is CodexUncertain else "invalid_response_body")
    assert "PRIVATE_" not in str(caught.value)
    assert "fixture-refresh" not in str(caught.value)
    assert caught.value.__context__ is None
    assert calls == ["chatgpt.com"]


@pytest.mark.parametrize("invalid", ["missing-done", "unfinished-reasoning", "missing-created-id",
                                      "missing-final-id", "missing-item-id", "empty-item-id", "no-items",
                                      "created-id-via-in-progress", "created-without-id"])
def test_empty_output_needs_complete_identified_items(tmp_path, monkeypatch, invalid):
    source, request = provider(tmp_path, "codex")
    stream = events()
    if invalid == "missing-done":
        stream.pop(-2)
    elif invalid == "unfinished-reasoning":
        stream.insert(-1, {"type": "response.output_item.added", "output_index": 1,
                           "item": {"type": "reasoning", "id": "rs_1", "summary": []}})
    elif invalid == "missing-created-id":
        del stream[0]["response"]["id"]
    elif invalid == "missing-final-id":
        del stream[-1]["response"]["id"]
    elif invalid == "missing-item-id":
        del stream[-2]["item"]["id"]
    elif invalid == "empty-item-id":
        stream[-2]["item"]["id"] = ""
    elif invalid == "created-id-via-in-progress":
        # No response.created at all: an in-progress event must not stand in for it.
        stream[0] = {"type": "response.in_progress",
                     "response": {"id": "resp_1", "status": "in_progress"}}
    elif invalid == "created-without-id":
        # A created event without an id cannot have its identity supplied later.
        del stream[0]["response"]["id"]
        stream.insert(1, {"type": "response.in_progress",
                          "response": {"id": "resp_1", "status": "in_progress"}})
    else:
        stream = [stream[0], stream[-1]]
    calls = http_responses(monkeypatch, "codex", body=wire(stream))
    with pytest.raises(CodexError) as caught:
        source.invoke(request)
    assert caught.value.code == "invalid_response_body"
    assert calls == ["chatgpt.com"]


def _reasoning_events(*, empty, added_text, part_text):
    """A reasoning stream whose initial added/summary-part text is caller-controlled.

    The completed summary is always ``Final reasoning``, so any valid initial text
    is a prefix of it. ``empty`` selects which final-output form is under test.
    """
    stream = events(empty=empty, reasoning=True)
    item_added, item_done = stream[1], stream[2]
    item_added["item"]["summary"] = [{"type": "summary_text", "text": added_text}]
    item_done["item"]["summary"] = [{"type": "summary_text", "text": "Final reasoning"}]
    if not empty:
        stream[-1]["response"]["output"][0]["summary"] = [{"type": "summary_text", "text": "Final reasoning"}]
    stream.insert(2, {"type": "response.reasoning_summary_part.added", "output_index": 0, "summary_index": 0,
                      "item_id": "rs_1", "part": {"type": "summary_text", "text": part_text}})
    return stream


@pytest.mark.parametrize("empty", [False, True])
@pytest.mark.parametrize("contradiction", ["added", "part"])
def test_contradictory_initial_reasoning_text_fails_closed(tmp_path, monkeypatch, empty, contradiction):
    source, request = provider(tmp_path, "codex")
    contradictory = {"added": ("CONTRADICTORY_INITIAL", ""), "part": ("", "CONTRADICTORY_INITIAL")}
    added_text, part_text = contradictory[contradiction]
    stream = _reasoning_events(empty=empty, added_text=added_text, part_text=part_text)
    calls = http_responses(monkeypatch, "codex", body=wire(stream))
    with pytest.raises(CodexError) as caught:
        source.invoke(request)
    assert caught.value.code == "invalid_response_body"
    assert "CONTRADICTORY" not in str(caught.value)
    assert calls == ["chatgpt.com"]


@pytest.mark.parametrize("empty", [False, True])
def test_prefix_initial_reasoning_text_is_accepted(tmp_path, monkeypatch, empty):
    source, request = provider(tmp_path, "codex")
    stream = _reasoning_events(empty=empty, added_text="Final", part_text="Final")
    calls = http_responses(monkeypatch, "codex", body=wire(stream))
    result = source.invoke(request)
    assert result.body == " Exact text\n"
    assert calls == ["chatgpt.com"]
