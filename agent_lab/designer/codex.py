"""Tool-free Codex subscription adapter; no Hermes imports or credential mutation.

Explicit auth_file is Hermes auth.json (normally ~/.hermes/auth.json), with
providers.openai-codex.tokens.access_token. Expiry is the JWT exp epoch seconds;
account identity is JWT https://api.openai.com/auth.chatgpt_account_id (not a
standalone tokens.account_id). Refresh/id tokens are never used for auth.

Transport is an async byte iterator over the *complete SSE envelope*, called
once with (canonical_body, headers, absolute_monotonic_deadline). It must be
cooperative with asyncio cancellation. The default uses direct TLS, no proxies,
redirects or retries. A local timeout does not promise remote cancellation.
ModelResponse.body preserves the exact semantic output text for replay, not the
raw provider SSE envelope; credentials and raw provider failures never escape.
"""
from __future__ import annotations

import asyncio
import base64
import json
import math
import os
import queue
import re
import ssl
import stat
import threading
import time
from collections.abc import AsyncIterator, Callable
from pathlib import Path
from typing import Any, Literal

from agent_lab.model_operation import HeaderObservation, ModelRequest, ModelResponse
from .http_response import REPEATABLE_METADATA, chunk_size, header_field, observe_headers, trailer_field

ENDPOINT = "https://chatgpt.com/backend-api/codex/responses"
REQUEST_TIMEOUT = 180.0
HEADER_LIMIT = 65536
STREAM_LIMIT = 524288  # Bounded SSE envelope, including repeated deltas and reasoning items.
RESPONSE_LIMIT = 65536  # Parsed assistant text remains separately bounded.
AUTH_LIMIT = 1048576
Transport = Callable[[bytes, dict[str, str], float], AsyncIterator[bytes]]


_FAILURE_MESSAGES = {
    "credentials_unavailable": "Codex credentials unavailable or invalid; run hermes auth separately and select a valid auth file.",
    "provider_rejected": "Codex request rejected; check subscription login and model selection.",
    "invalid_response": "Codex request failed or returned invalid output; check login/model and retry explicitly.",
    "invalid_request": "Codex request failed local validation.",
    "invalid_response_body": "Codex model response failed validation.",
    "invalid_http_headers": "Codex HTTP response headers are invalid.",
    "invalid_http_status": "Codex HTTP response status syntax is invalid.",
    "invalid_http_header": "Codex HTTP response header syntax is invalid.",
    "unsupported_http_content_type": "Codex HTTP response content type is unsupported or missing.",
    "missing_http_content_type": "Codex HTTP response content type is missing.",
    "empty_http_content_type": "Codex HTTP response content type is empty.",
    "unsupported_http_content_encoding": "Codex HTTP response content encoding is unsupported.",
    "duplicate_http_header": "Codex HTTP response contains a rejected duplicate header.",
    "invalid_http_framing": "Codex HTTP response framing is invalid.",
    "response_limit": "Codex response exceeded the bounded envelope limit.",
    "transport_incomplete": "Codex exchange incomplete; remote completion is unknown. Retry only explicitly.",
    "deadline_exceeded": "Codex deadline exceeded; remote completion is unknown. Retry only explicitly.",
}


class CodexError(ValueError):
    """Sanitized operator-facing failure, never provider text or credentials."""

    def __init__(self, message: str = "Codex returned invalid output.", *,
                 code: str = "invalid_response", provider_status: int | None = None,
                 header_observation: HeaderObservation | None = None) -> None:
        self.header_observation = header_observation
        super().__init__(message)
        self.code = code if code in _FAILURE_MESSAGES else "invalid_response"
        self.provider_status = provider_status if type(provider_status) is int else None


class _CredentialError(CodexError):
    pass


class CodexUncertain(TimeoutError):
    """The remote exchange did not finish; cancellation is not guaranteed."""

    def __init__(self, message: str = "Codex exchange incomplete.", *,
                 code: str = "transport_incomplete", provider_status: int | None = None,
                 header_observation: HeaderObservation | None = None) -> None:
        self.header_observation = header_observation
        super().__init__(message)
        self.code = code if code in _FAILURE_MESSAGES else "transport_incomplete"
        self.provider_status = provider_status if type(provider_status) is int else None


def _unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError
        result[key] = value
    return result


def _json(data: str | bytes) -> Any:
    def invalid(value: str) -> None:
        raise ValueError
    return json.loads(data, object_pairs_hook=_unique, parse_constant=invalid)


def _credentials(path: Path) -> tuple[str, str, tuple[str, ...]]:
    try:
        # Nonblocking open plus fstat avoids FIFO hangs and path-swap races.
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                    or info.st_size > AUTH_LIMIT):
                raise ValueError
            raw = stream.read(AUTH_LIMIT + 1)
            if len(raw) > AUTH_LIMIT:
                raise ValueError
        data = _json(raw)
        tokens = data["providers"]["openai-codex"]["tokens"]
        token = tokens["access_token"]
        if not isinstance(token, str) or len(token.split(".")) != 3:
            raise ValueError
        payload = token.split(".")[1]
        claims = _json(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        exp = claims["exp"]
        account = claims["https://api.openai.com/auth"]["chatgpt_account_id"]
        if (type(exp) not in (int, float) or not math.isfinite(exp) or exp <= time.time()
                or not isinstance(account, str) or not account
                or any(ord(c) < 33 or ord(c) > 126 for c in token + account)):
            raise ValueError
        secrets = tuple(value for key, value in tokens.items()
                        if key in ("access_token", "refresh_token", "id_token")
                        and isinstance(value, str) and value)
        return token, account, secrets
    except Exception:
        pass
    raise _CredentialError(_FAILURE_MESSAGES["credentials_unavailable"], code="credentials_unavailable")


async def _https(body: bytes, headers: dict[str, str], deadline: float) -> AsyncIterator[bytes]:
    reader, writer = await asyncio.open_connection("chatgpt.com", 443, ssl=ssl.create_default_context(),
                                                   server_hostname="chatgpt.com", limit=HEADER_LIMIT)
    failure_code = "invalid_http_status"
    status = None
    observation = None
    try:
        head = {**headers, "Host": "chatgpt.com", "Content-Length": str(len(body)), "Connection": "close"}
        wire = "POST /backend-api/codex/responses HTTP/1.1\r\n" + "".join(f"{k}: {v}\r\n" for k, v in head.items()) + "\r\n"
        writer.write(wire.encode("ascii") + body)
        await writer.drain()
        raw = await reader.readuntil(b"\r\n\r\n")
        if len(raw) > HEADER_LIMIT:
            raise CodexError(code="response_limit")
        observation = observe_headers(raw)
        lines = raw.split(b"\r\n")
        status_line = lines[0].decode("ascii").split(" ", 2)
        if status_line[0] not in ("HTTP/1.0", "HTTP/1.1") or not re.fullmatch(r"[1-5][0-9]{2}", status_line[1]):
            raise ValueError
        status = int(status_line[1])
        if status in (408, 504):
            raise CodexUncertain(code="deadline_exceeded", provider_status=status)
        if status != 200:
            raise CodexError(code="provider_rejected", provider_status=status)
        response_headers: dict[str, str] = {}
        for line in lines[1:]:
            if line:
                failure_code = "invalid_http_header"
                key, value = header_field(line.decode("ascii"))
                if key in REPEATABLE_METADATA:
                    continue  # Repeatable metadata is unused and never retained.
                if key in response_headers:
                    failure_code = "duplicate_http_header"
                    raise ValueError
                response_headers[key] = value.strip()
        # This pinned Codex endpoint can omit MIME on valid SSE responses.
        # Only absence is exempt: explicit values still have to declare SSE,
        # and the bounded body must pass the same strict completed-stream parser.
        if "content-type" in response_headers:
            failure_code = "empty_http_content_type"
            if not response_headers["content-type"]:
                raise ValueError
            failure_code = "unsupported_http_content_type"
            if response_headers["content-type"].split(";")[0].strip().lower() != "text/event-stream":
                raise ValueError
        failure_code = "unsupported_http_content_encoding"
        if response_headers.get("content-encoding", "identity") != "identity":
            raise ValueError
        observation = None  # Header acceptance ends this observation boundary.
        failure_code = "invalid_http_framing"
        encoding = response_headers.get("transfer-encoding")
        length = response_headers.get("content-length")
        if encoding is not None:
            if encoding != "chunked" or length is not None:
                raise ValueError
            framing = 0
            while True:
                line_bytes = await reader.readuntil(b"\r\n")
                framing += len(line_bytes)
                if framing > STREAM_LIMIT:
                    raise CodexError(code="response_limit")
                size = chunk_size(line_bytes)
                if size > STREAM_LIMIT:
                    raise CodexError(code="response_limit")
                if not size:
                    # Trailer fields are unused, but must be validated and bounded.
                    seen_trailers: set[str] = set()
                    while True:
                        trailer = await reader.readuntil(b"\r\n")
                        framing += len(trailer)
                        if framing > STREAM_LIMIT:
                            raise CodexError(code="response_limit")
                        if trailer == b"\r\n":
                            return
                        trailer_field(trailer, seen_trailers)
                yield await reader.readexactly(size)
                if await reader.readexactly(2) != b"\r\n":
                    raise ValueError
        elif length is not None:
            if not re.fullmatch(r"[0-9]+", length):
                raise ValueError
            remaining = int(length)
            if remaining > STREAM_LIMIT:
                raise CodexError(code="response_limit")
            while remaining:
                chunk = await reader.readexactly(min(4096, remaining))
                remaining -= len(chunk)
                yield chunk
        else:
            while chunk := await reader.read(4096):
                yield chunk
    except (CodexError, CodexUncertain) as exc:
        exc.header_observation = observation
        raise
    except (ValueError, IndexError):
        raise CodexError(code=failure_code, provider_status=status,
                         header_observation=observation) from None
    finally:
        writer.close()
        # Do not wait for a remote TLS close acknowledgement after the deadline.


def _reasoning_item(item: dict[str, Any], *, final: bool) -> None:
    """Accept native reasoning, never treating it as assistant output or a tool."""
    if (set(item) - {"id", "type", "status", "summary", "encrypted_content", "content"}
            or ("content" in item and item["content"] != [])
            or item.get("type") != "reasoning"
            or not isinstance(item.get("id"), str) or not item["id"]
            or item.get("status", "completed" if final else "in_progress")
            not in (("completed",) if final else ("in_progress", "completed"))
            or not isinstance(item.get("summary"), list)
            or any(not isinstance(part, dict) or part.get("type") != "summary_text"
                   or not isinstance(part.get("text"), str) for part in item["summary"])
            or (item.get("encrypted_content") is not None
                and not isinstance(item["encrypted_content"], str))):
        raise ValueError


def _parse(data: bytes, secrets: tuple[str, ...]) -> ModelResponse:
    text = data.decode("utf-8").replace("\r\n", "\n")
    if not text.endswith("\n\n"):
        raise CodexUncertain
    final: dict[str, Any] | None = None
    response_id: str | None = None
    created_response_id: str | None = None
    deltas: list[str] = []
    done_text: str | None = None
    terminal_texts: list[str] = []
    seen: set[tuple[Any, ...]] = set()
    item_events: list[dict[str, Any]] = []
    completed_items: dict[int, dict[str, Any]] = {}
    event_response_ids: set[str] = set()
    message_indices: set[int] = set()
    summary_deltas: dict[tuple[int, int], list[str]] = {}
    summary_done: set[tuple[int, int]] = set()
    for block in text.split("\n\n"):
        if not block:
            continue
        event = None
        payload = []
        for line in block.split("\n"):
            if line.startswith(":"):
                continue
            key, sep, value = line.partition(":")
            if not sep:
                raise ValueError
            value = value.removeprefix(" ")
            if key == "event" and event is None:
                event = value
            elif key == "data":
                payload.append(value)
            else:
                raise ValueError
        if not payload:
            continue
        obj = _json("\n".join(payload))
        kind = obj["type"]
        if event is not None and event != kind:
            raise ValueError
        if final is not None:
            raise ValueError
        for index_field in ("output_index", "content_index", "summary_index"):
            if index_field in obj and (type(obj[index_field]) is not int or obj[index_field] < 0):
                raise ValueError
        if "response_id" in obj:
            if not isinstance(obj["response_id"], str) or not obj["response_id"]:
                raise ValueError
            event_response_ids.add(obj["response_id"])
        if obj.get("output_index") in completed_items:
            raise ValueError  # No item/content event can follow that item's completion.
        if kind not in ("response.output_text.delta", "response.reasoning_summary_text.delta", "response.in_progress"):
            event_key = (kind, obj.get("output_index"), obj.get("content_index"), obj.get("summary_index"))
            if event_key in seen:
                raise ValueError
            seen.add(event_key)
        if kind == "response.completed":
            final = obj["response"]
        elif kind in ("response.created", "response.in_progress"):
            response = obj["response"]
            if response["status"] != "in_progress":
                raise ValueError
            if "id" in response:
                if not isinstance(response["id"], str) or not response["id"]:
                    raise ValueError
                if response_id is not None and response_id != response["id"]:
                    raise ValueError
                response_id = response["id"]
            if kind == "response.created":
                # Empty-output assembly needs the identity the creation event itself
                # carried; a later in-progress event must not supply it retroactively.
                created_response_id = response.get("id")
        elif kind in ("response.output_item.added", "response.output_item.done"):
            item = obj["item"]
            item_events.append(obj)
            if kind.endswith("done"):
                completed_items[obj["output_index"]] = item
            if item["type"] == "reasoning":
                _reasoning_item(item, final=kind.endswith("done"))
                continue
            message_indices.add(obj["output_index"])
            status = "in_progress" if kind.endswith("added") else "completed"
            if (item["type"] != "message"
                    or item["role"] != "assistant" or item["status"] != status
                    or not isinstance(item["content"], list) or len(item["content"]) > 1
                    or any(part["type"] != "output_text" for part in item["content"])):
                raise ValueError
            if kind.endswith("done"):
                if len(item["content"]) != 1:
                    raise ValueError
                terminal_texts.append(item["content"][0]["text"])
        elif kind in ("response.reasoning_summary_part.added", "response.reasoning_summary_part.done",
                      "response.reasoning_summary_text.delta", "response.reasoning_summary_text.done"):
            key_pair = (obj["output_index"], obj["summary_index"])
            item_events.append(obj)
            if "_part." in kind:
                part = obj["part"]
                if part["type"] != "summary_text" or not isinstance(part["text"], str):
                    raise ValueError
            elif kind.endswith("delta"):
                if key_pair in summary_done or not isinstance(obj["delta"], str):
                    raise ValueError
                summary_deltas.setdefault(key_pair, []).append(obj["delta"])
            elif not isinstance(obj["text"], str):
                raise ValueError
            if kind.endswith("done"):
                summary_done.add(key_pair)
        elif kind in ("response.content_part.added", "response.content_part.done",
                      "response.output_text.delta", "response.output_text.done"):
            message_indices.add(obj["output_index"])
            item_events.append(obj)
            if obj["content_index"] != 0:
                raise ValueError
            if kind.startswith("response.content_part"):
                if obj["part"]["type"] != "output_text":
                    raise ValueError
                if kind.endswith("done"):
                    terminal_texts.append(obj["part"]["text"])
            elif kind.endswith("delta"):
                if done_text is not None or not isinstance(obj["delta"], str):
                    raise ValueError
                deltas.append(obj["delta"])
            else:
                if done_text is not None or not isinstance(obj["text"], str):
                    raise ValueError
                done_text = obj["text"]
        else:
            raise ValueError
    if final is None:
        raise CodexUncertain
    if final["status"] != "completed":
        raise ValueError
    output = final["output"]
    if not isinstance(output, list):
        raise ValueError
    if not output:
        # Assemble only terminal items, never deltas or added/in-progress items.
        # Comparing sorted keys avoids allocation from an untrusted large index.
        if (not isinstance(created_response_id, str) or final.get("id") != created_response_id
                or not completed_items
                or sorted(completed_items) != list(range(len(completed_items)))):
            raise ValueError
        output = [completed_items[index] for index in range(len(completed_items))]
        if any(not isinstance(item.get("id"), str) or not item["id"] for item in output):
            raise ValueError
    if event_response_ids and event_response_ids != {final.get("id", response_id)}:
        raise ValueError
    messages = []
    item_ids: set[str] = set()
    for index, item in enumerate(output):
        if "id" in item:
            if not isinstance(item["id"], str) or not item["id"] or item["id"] in item_ids:
                raise ValueError
            item_ids.add(item["id"])
        if item["type"] == "reasoning":
            _reasoning_item(item, final=True)
        elif item["type"] == "message":
            messages.append((index, item))
        else:
            raise ValueError
    if len(messages) != 1:
        raise ValueError
    message_index, message = messages[0]
    if message_indices - {message_index}:
        raise ValueError
    for observed in item_events:
        item = output[observed["output_index"]]
        if "item" in observed:
            streamed = observed["item"]
            if item["type"] != streamed["type"] or (
                    "id" in item and "id" in streamed and item["id"] != streamed["id"]):
                raise ValueError
            if observed["type"].endswith("done") and streamed != item:
                raise ValueError
            if streamed["type"] == "message" and observed["type"].endswith("added"):
                for part in streamed["content"]:
                    if (not isinstance(part.get("text"), str)
                            or not item["content"][0]["text"].startswith(part["text"])):
                        raise ValueError
            if streamed["type"] == "reasoning" and observed["type"].endswith("added"):
                # Initial reasoning text must be a prefix of the completed summary,
                # exactly as message text is; a contradictory start is not filled in.
                for summary_index, part in enumerate(streamed["summary"]):
                    if (summary_index >= len(item["summary"])
                            or not item["summary"][summary_index]["text"].startswith(part["text"])):
                        raise ValueError
        if "item_id" in observed and observed["item_id"] != item.get("id"):
            raise ValueError
        if observed["type"] == "response.content_part.added":
            initial_text = observed["part"].get("text")
            if (not isinstance(initial_text, str)
                    or not item["content"][0]["text"].startswith(initial_text)):
                raise ValueError
        if observed["type"].startswith("response.reasoning_summary_"):
            if item["type"] != "reasoning":
                raise ValueError
            summary_text = item["summary"][observed["summary_index"]]["text"]
            if observed["type"].endswith("done"):
                observed_text = observed["part"]["text"] if "part" in observed else observed["text"]
                if observed_text != summary_text:
                    raise ValueError
            elif observed["type"] == "response.reasoning_summary_part.added":
                # The announced summary part must be a prefix of the completed text.
                if not summary_text.startswith(observed["part"]["text"]):
                    raise ValueError
    for (index, summary_index), chunks in summary_deltas.items():
        if "".join(chunks) != output[index]["summary"][summary_index]["text"]:
            raise ValueError
    content = message["content"]
    if (message["type"] != "message" or message["role"] != "assistant"
            or message["status"] != "completed" or len(content) != 1
            or content[0]["type"] != "output_text"):
        raise ValueError
    body = content[0]["text"]
    if len(body.encode("utf-8")) > RESPONSE_LIMIT:
        raise CodexError(code="response_limit")
    if ((response_id is not None and "id" in final and response_id != final["id"])
            or (deltas and "".join(deltas) != body)
            or (done_text is not None and done_text != body)
            or any(value != body for value in terminal_texts)):
        raise ValueError
    usage = final.get("usage")
    if usage is None:
        usage = {}
    if not isinstance(usage, dict):
        raise ValueError
    for key in ("input_tokens_details", "output_tokens_details"):
        if usage.get(key) is not None and not isinstance(usage[key], dict):
            raise ValueError
    for field in ("id", "model"):
        if field in final and (not isinstance(final[field], str) or not final[field]):
            raise ValueError
    result = ModelResponse(body=body, provider_request_id=final.get("id", response_id), resolved_model=final.get("model"),
                           input_tokens=usage.get("input_tokens"), output_tokens=usage.get("output_tokens"),
                           reasoning_tokens=(usage.get("output_tokens_details") or {}).get("reasoning_tokens"),
                           cache_read_tokens=(usage.get("input_tokens_details") or {}).get("cached_tokens"))
    if any(secret in value for secret in secrets for value in
           (result.body, result.provider_request_id or "", result.resolved_model or "")):
        raise ValueError
    return result


class CodexSource:
    mode: Literal["live"] = "live"

    def __init__(self, auth_file: Path, *, transport: Transport | None = None) -> None:
        self._auth_file = auth_file
        self._transport = transport or _https

    def invoke(self, request: ModelRequest) -> ModelResponse:
        deadline = time.monotonic() + REQUEST_TIMEOUT
        try:
            body = _json(request.request_json)
            text_input = body["input"]
            # Codex's native request uses a list of user input-text messages.
            # Retain the semantic string form for injected transports.
            if isinstance(text_input, list):
                if len(text_input) != 1:
                    raise ValueError
                message = text_input[0]
                if set(message) != {"role", "content"} or message["role"] != "user":
                    raise ValueError
                parts = message["content"]
                if (not isinstance(parts, list) or len(parts) != 1
                        or set(parts[0]) != {"type", "text"} or parts[0]["type"] != "input_text"):
                    raise ValueError
                text_input = parts[0]["text"]
            if not isinstance(text_input, str) or not text_input:
                raise ValueError
            if (set(body) != {"model", "instructions", "input", "tools", "store", "stream"}
                    or body["tools"] != [] or body["store"] is not False or body["stream"] is not True
                    or any(not isinstance(body[key], str) or not body[key] for key in ("model", "instructions"))):
                raise ValueError
        except Exception:
            raise CodexError(_FAILURE_MESSAGES["invalid_request"], code="invalid_request") from None
        results: queue.Queue[ModelResponse | CodexError | CodexUncertain] = queue.Queue(maxsize=1)

        async def run() -> ModelResponse:
            token, account, secrets = _credentials(self._auth_file)
            # Reading a regular file can still be slow (for example on NFS).
            # The caller's queue deadline bounds that wait; never send late.
            if time.monotonic() >= deadline:
                raise CodexUncertain(code="deadline_exceeded")
            headers = {"Authorization": "Bearer " + token, "ChatGPT-Account-ID": account,
                       "Content-Type": "application/json", "Accept": "text/event-stream",
                       "Accept-Encoding": "identity", "User-Agent": "WorkflowGenerator/1",
                       "originator": "workflow-generator"}
            async with asyncio.timeout(max(0, deadline - time.monotonic())):
                data = bytearray()
                async for chunk in self._transport(request.request_json.encode("utf-8"), headers, deadline):
                    if time.monotonic() >= deadline:
                        raise CodexUncertain(code="deadline_exceeded")
                    if len(data) + len(chunk) > STREAM_LIMIT:
                        raise CodexError(code="response_limit")
                    data.extend(chunk)
                try:
                    return _parse(bytes(data), secrets)
                except (CodexError, CodexUncertain):
                    raise
                except Exception:
                    raise CodexError(code="invalid_response_body") from None

        def worker() -> None:
            try:
                result = asyncio.run(run())
            except (CodexError, CodexUncertain) as exc:
                # Only safe classification data crosses the thread boundary, never
                # provider text, traceback, or chained exceptions.
                kind = CodexUncertain if isinstance(exc, CodexUncertain) else CodexError
                results.put(kind(_FAILURE_MESSAGES[exc.code], code=exc.code,
                                 provider_status=exc.provider_status,
                                 header_observation=exc.header_observation))
            except asyncio.LimitOverrunError:
                results.put(CodexError(_FAILURE_MESSAGES["response_limit"], code="response_limit"))
            except TimeoutError:
                results.put(CodexUncertain(_FAILURE_MESSAGES["deadline_exceeded"], code="deadline_exceeded"))
            except ValueError:
                results.put(CodexError(_FAILURE_MESSAGES["invalid_response"]))
            except Exception:
                results.put(CodexUncertain(_FAILURE_MESSAGES["transport_incomplete"]))
            else:
                results.put(result)

        # invoke is synchronous and also works when called by an async graph.
        threading.Thread(target=worker, daemon=True).start()
        try:
            result = results.get(timeout=max(0, deadline - time.monotonic()))
        except queue.Empty:
            result = CodexUncertain(_FAILURE_MESSAGES["deadline_exceeded"], code="deadline_exceeded")
        if isinstance(result, (CodexError, CodexUncertain)):
            raise result from None
        return result
