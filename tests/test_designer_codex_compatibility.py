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


@pytest.mark.parametrize("empty", [False, True])
@pytest.mark.parametrize("invalid", [
    "duplicate-done", "duplicate-added", "wrong-item-id", "wrong-added-id", "wrong-response-id",
    "event-response-id", "gap", "negative-index", "bool-index", "wrong-content-index",
    "delta-conflict", "text-done-conflict", "part-done-conflict", "incomplete-item",
    "tool", "refusal", "failed", "interrupted", "late-item-event", "late-response-event",
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
                                      "missing-final-id", "missing-item-id", "empty-item-id", "no-items"])
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
    else:
        stream = [stream[0], stream[-1]]
    calls = http_responses(monkeypatch, "codex", body=wire(stream))
    with pytest.raises(CodexError) as caught:
        source.invoke(request)
    assert caught.value.code == "invalid_response_body"
    assert calls == ["chatgpt.com"]
