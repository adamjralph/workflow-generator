"""Bounded, tool-free Vertex OpenAI adapter with pinned read-only authorized_user ADC.

The injected transport serves BOTH OAuth and generation: (url, body, headers,
absolute monotonic deadline) -> async byte iterator. It must cooperate with
cancellation. No credential discovery, saved tokens, retries, proxies or redirects.
Local bounds do not promise remote cancellation or capped spend. Auth accounting
is invocation-local, including errors; tokens live only in the worker's memory.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
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
from urllib.parse import urlencode, urlsplit

from agent_lab.model_operation import HeaderObservation, ModelRequest, ModelResponse
from .http_response import REPEATABLE_METADATA, chunk_size, header_field, observe_headers, trailer_field

REQUEST_TIMEOUT = 180.0
RESPONSE_LIMIT = 65536
AUTH_LIMIT = 65536
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
Transport = Callable[[str, bytes, dict[str, str], float], AsyncIterator[bytes]]
_MESSAGES = {
    "credentials_unavailable": "Vertex credentials unavailable or invalid; configure an owned authorized_user file separately.",
    "provider_rejected": "Vertex request rejected; check credentials, project and model selection.",
    "invalid_response": "Vertex request or response is invalid.",
    "invalid_request": "Vertex request failed local validation.",
    "invalid_auth_response": "Vertex OAuth response failed validation.",
    "invalid_response_body": "Vertex model response failed validation.",
    "invalid_http_headers": "Vertex HTTP response headers are invalid.",
    "invalid_http_status": "Vertex HTTP response status syntax is invalid.",
    "invalid_http_header": "Vertex HTTP response header syntax is invalid.",
    "unsupported_http_content_type": "Vertex HTTP response content type is unsupported or missing.",
    "missing_http_content_type": "Vertex HTTP response content type is missing.",
    "empty_http_content_type": "Vertex HTTP response content type is empty.",
    "unsupported_http_content_encoding": "Vertex HTTP response content encoding is unsupported.",
    "duplicate_http_header": "Vertex HTTP response contains a rejected duplicate header.",
    "invalid_http_framing": "Vertex HTTP response framing is invalid.",
    "response_limit": "Vertex response exceeded the bounded envelope limit.",
    "transport_incomplete": "Vertex exchange incomplete; remote completion is unknown.",
    "deadline_exceeded": "Vertex deadline exceeded; remote completion is unknown.",
}


class VertexError(ValueError):
    """Sanitized failure: arbitrary provider/transport messages never escape."""

    def __init__(self, message: str = "", *, code: str = "invalid_response",
                 provider_status: int | None = None, auth_requests: int = 0,
                 header_observation: HeaderObservation | None = None) -> None:
        self.header_observation = header_observation
        self.code = code if code in _MESSAGES else "invalid_response"
        self.provider_status = (provider_status if type(provider_status) is int
                                and 100 <= provider_status <= 599 else None)
        self.auth_requests = 1 if auth_requests == 1 else 0
        super().__init__(_MESSAGES[self.code])


class VertexUncertain(TimeoutError):
    """Incomplete exchange; the attempt is not safe to retry automatically."""

    def __init__(self, message: str = "", *, code: str = "transport_incomplete",
                 provider_status: int | None = None, auth_requests: int = 0,
                 header_observation: HeaderObservation | None = None) -> None:
        self.header_observation = header_observation
        self.code = code if code in _MESSAGES else "transport_incomplete"
        self.provider_status = (provider_status if type(provider_status) is int
                                and 100 <= provider_status <= 599 else None)
        self.auth_requests = 1 if auth_requests == 1 else 0
        super().__init__(_MESSAGES[self.code])


def _json(raw: str | bytes) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError
            result[key] = value
        return result

    def invalid(value: str) -> None:
        raise ValueError

    text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
    return json.loads(text, object_pairs_hook=pairs, parse_constant=invalid)


def _credentials(path: Path) -> tuple[dict[str, str], tuple[str, ...]]:
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                    or info.st_mode & 0o022 or info.st_size > AUTH_LIMIT):
                raise ValueError
            raw = stream.read(AUTH_LIMIT + 1)
        if len(raw) > AUTH_LIMIT:
            raise ValueError
        data = _json(raw)
        if data["type"] != "authorized_user":
            raise ValueError
        # Never honor credential-supplied endpoints or external-account mechanisms.
        if any(key in data for key in ("token_uri", "token_url", "credential_source",
                                       "service_account_impersonation_url")):
            raise ValueError
        values = {key: data[key] for key in ("client_id", "client_secret", "refresh_token")}
        if any(not isinstance(value, str) or not value or
               any(ord(c) < 33 or ord(c) > 126 for c in value) for value in values.values()):
            raise ValueError
        # Additional saved secrets are never used, but must not escape in output.
        def strings(value: Any) -> list[str]:
            if isinstance(value, str):
                return [value] if value else []
            if isinstance(value, dict):
                return [text for item in value.values() for text in strings(item)]
            if isinstance(value, list):
                return [text for item in value for text in strings(item)]
            return []

        secrets = tuple(text for key, value in data.items() if key != "type" for text in strings(value))
        return values, secrets
    except Exception:
        raise VertexError(code="credentials_unavailable") from None


def _no_secrets(value: Any, secrets: tuple[str, ...]) -> None:
    if isinstance(value, str):
        value.encode("utf-8")  # Reject unpaired surrogates before recording.
        if any(secret in value for secret in secrets):
            raise ValueError
        # Semantic output is often JSON itself; inspect escaped credential echoes
        # without rewriting the exact replayable text.
        if value.lstrip().startswith(("{", "[", '"')):
            try:
                nested = _json(value)
            except ValueError:
                pass
            else:
                _no_secrets(nested, secrets)
    elif isinstance(value, dict):
        for key, item in value.items():
            _no_secrets(key, secrets)
            _no_secrets(item, secrets)
    elif isinstance(value, list):
        for item in value:
            _no_secrets(item, secrets)


def _parse(raw: bytes, secrets: tuple[str, ...]) -> ModelResponse:
    data = _json(raw)
    _no_secrets(data, secrets)
    if (not isinstance(data, dict) or data.get("object") != "chat.completion"
            or set(data) - {"id", "object", "created", "model", "choices", "usage",
                            "system_fingerprint", "service_tier"}):
        raise ValueError
    if "created" in data and (type(data["created"]) is not int or data["created"] < 0):
        raise ValueError
    for key in ("system_fingerprint", "service_tier"):
        if data.get(key) is not None and not isinstance(data[key], str):
            raise ValueError
    choices = data["choices"]
    if not isinstance(choices, list) or len(choices) != 1:
        raise ValueError
    choice = choices[0]
    if (not isinstance(choice, dict) or set(choice) - {"index", "finish_reason", "message", "logprobs"}
            or type(choice.get("index")) is not int or choice["index"] != 0
            or choice.get("finish_reason") != "stop" or choice.get("logprobs") is not None):
        raise ValueError
    message = choice["message"]
    if (not isinstance(message, dict) or set(message) - {"role", "content", "tool_calls", "function_call", "refusal"}
            or message.get("role") != "assistant"
            or not isinstance(message.get("content"), str) or not message["content"].strip()
            or message.get("tool_calls") not in (None, [])
            or message.get("function_call") is not None or message.get("refusal") is not None):
        raise ValueError
    for key in ("id", "model"):
        if key in data and (not isinstance(data[key], str) or not data[key].strip()):
            raise ValueError
    usage = data.get("usage")
    counts: dict[str, int | None] = {}
    if usage is not None:
        if not isinstance(usage, dict):
            raise ValueError
        for key, value in usage.items():
            if key.endswith("_details"):
                if value is None:
                    continue
                if not isinstance(value, dict):
                    raise ValueError
                for count in value.values():
                    if type(count) is not int or count < 0:
                        raise ValueError
            elif type(value) is not int or value < 0:
                raise ValueError
        for target, source in (("input_tokens", "prompt_tokens"), ("output_tokens", "completion_tokens")):
            counts[target] = usage.get(source)
        counts["reasoning_tokens"] = (usage.get("completion_tokens_details") or {}).get("reasoning_tokens")
        counts["cache_read_tokens"] = (usage.get("prompt_tokens_details") or {}).get("cached_tokens")
        if all(key in usage for key in ("prompt_tokens", "completion_tokens", "total_tokens")):
            if usage["total_tokens"] != usage["prompt_tokens"] + usage["completion_tokens"]:
                raise ValueError
        for child, parent in (("reasoning_tokens", "output_tokens"), ("cache_read_tokens", "input_tokens")):
            sub, total = counts.get(child), counts.get(parent)
            if sub is not None and total is not None and sub > total:
                raise ValueError
    return ModelResponse(body=message["content"], provider_request_id=data.get("id"),
                         resolved_model=data.get("model"), auth_requests=1, **counts)


async def _https(url: str, body: bytes, headers: dict[str, str], deadline: float) -> AsyncIterator[bytes]:
    """Direct TLS only; bounded HTTP framing, one POST, no redirect/retry logic."""
    target = urlsplit(url)
    host = target.hostname
    if target.scheme != "https" or not host or target.port or target.username or target.query or target.fragment:
        raise ValueError
    reader, writer = await asyncio.open_connection(host, 443, ssl=ssl.create_default_context(),
                                                   server_hostname=host, limit=RESPONSE_LIMIT)
    failure_code = "invalid_http_status"
    status = None
    observation = None
    try:
        if time.monotonic() >= deadline:
            raise VertexUncertain(code="deadline_exceeded")
        head = {**headers, "Host": host, "Content-Length": str(len(body)), "Connection": "close"}
        wire = f"POST {target.path} HTTP/1.1\r\n" + "".join(f"{k}: {v}\r\n" for k, v in head.items()) + "\r\n"
        writer.write(wire.encode("ascii") + body)
        await writer.drain()
        raw = await reader.readuntil(b"\r\n\r\n")
        if len(raw) > RESPONSE_LIMIT:
            raise VertexError(code="response_limit")
        observation = observe_headers(raw)
        lines = raw.split(b"\r\n")
        status_line = lines[0].decode("ascii").split(" ", 2)
        if status_line[0] not in ("HTTP/1.0", "HTTP/1.1") or not re.fullmatch(r"[1-5][0-9]{2}", status_line[1]):
            raise ValueError
        status = int(status_line[1])
        if status in (408, 504):
            raise VertexUncertain(code="deadline_exceeded", provider_status=status)
        if status != 200:
            raise VertexError(code="provider_rejected", provider_status=status)
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
        failure_code = "missing_http_content_type"
        if "content-type" not in response_headers:
            raise ValueError
        failure_code = "empty_http_content_type"
        if not response_headers["content-type"]:
            raise ValueError
        failure_code = "unsupported_http_content_type"
        if response_headers["content-type"].split(";")[0].strip().lower() != "application/json":
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
                if framing > RESPONSE_LIMIT:
                    raise VertexError(code="response_limit")
                size = chunk_size(line_bytes)
                if size > RESPONSE_LIMIT:
                    raise VertexError(code="response_limit")
                if not size:
                    seen_trailers: set[str] = set()
                    while True:
                        trailer = await reader.readuntil(b"\r\n")
                        framing += len(trailer)
                        if framing > RESPONSE_LIMIT:
                            raise VertexError(code="response_limit")
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
            if remaining > RESPONSE_LIMIT:
                raise VertexError(code="response_limit")
            while remaining:
                chunk = await reader.readexactly(min(4096, remaining))
                remaining -= len(chunk)
                yield chunk
        else:
            while chunk := await reader.read(4096):
                yield chunk
    except (VertexError, VertexUncertain) as exc:
        exc.header_observation = observation
        raise
    except (ValueError, IndexError):
        raise VertexError(code=failure_code, provider_status=status,
                          header_observation=observation) from None
    finally:
        writer.close()


class VertexSource:
    mode: Literal["live"] = "live"

    def __init__(self, auth_file: Path, project: str, region: str = "global", *,
                 transport: Transport | None = None) -> None:
        if (not isinstance(project, str) or re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9-]{0,62}", project) is None
                or not isinstance(region, str) or re.fullmatch(r"[a-z][a-z0-9-]{0,62}", region) is None):
            raise VertexError
        host = "aiplatform.googleapis.com" if region == "global" else region + "-aiplatform.googleapis.com"
        self._url = f"https://{host}/v1beta1/projects/{project}/locations/{region}/endpoints/openapi/chat/completions"
        self._auth_file = Path(auth_file).expanduser().absolute()
        self._project, self._region = project, region
        self._transport = transport or _https

    @property
    def execution_options(self) -> dict[str, object]:
        """Non-secret routing/authority identity, without reading credentials."""
        return {"project": self._project, "region": self._region,
                "credential_kind": "pinned-authorized-user",
                "credential_source_digest": hashlib.sha256(str(self._auth_file).encode()).hexdigest(),
                "auth_max_requests": 1, "auth_persistence": False}

    def invoke(self, request: ModelRequest) -> ModelResponse:
        deadline = time.monotonic() + REQUEST_TIMEOUT
        try:
            body = _json(request.request_json)
            if (set(body) != {"model", "messages", "tools", "stream"} or body["tools"] != []
                    or body["stream"] is not False or not isinstance(body["model"], str)
                    or not body["model"].strip()):
                raise ValueError
            messages = body["messages"]
            if not isinstance(messages, list) or len(messages) != 2:
                raise ValueError
            for message, role in zip(messages, ("system", "user"), strict=True):
                if (set(message) != {"role", "content"} or message["role"] != role
                        or not isinstance(message["content"], str) or not message["content"].strip()):
                    raise ValueError
        except Exception:
            raise VertexError(code="invalid_request") from None
        results: queue.Queue[ModelResponse | VertexError | VertexUncertain] = queue.Queue(maxsize=1)
        lock = threading.Lock()
        stopped = False
        auth_requests = 0

        def check_deadline() -> None:
            if stopped or time.monotonic() >= deadline:
                raise VertexUncertain(code="deadline_exceeded")

        async def collect(url: str, payload: bytes, headers: dict[str, str], *, auth: bool = False) -> bytes:
            nonlocal auth_requests
            with lock:
                check_deadline()
                if auth:
                    auth_requests = 1
            data = bytearray()
            async for chunk in self._transport(url, payload, headers, deadline):
                check_deadline()
                if not isinstance(chunk, bytes):
                    raise ValueError
                if len(data) + len(chunk) > RESPONSE_LIMIT:
                    raise VertexError(code="response_limit")
                data.extend(chunk)
            check_deadline()
            return bytes(data)

        async def run() -> ModelResponse:
            values, secrets = _credentials(self._auth_file)
            with lock:
                check_deadline()
            async with asyncio.timeout(max(0, deadline - time.monotonic())):
                headers = {"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json",
                           "Accept-Encoding": "identity"}
                raw = await collect(TOKEN_ENDPOINT, urlencode({"grant_type": "refresh_token", **values}).encode(),
                                    headers, auth=True)
                try:
                    token_data = _json(raw)
                    token = token_data["access_token"]
                    if ("error" in token_data or not isinstance(token, str) or not token
                            or any(ord(c) < 33 or ord(c) > 126 for c in token)
                            or token_data.get("token_type", "").lower() != "bearer"
                            or type(token_data.get("expires_in")) is not int or token_data["expires_in"] <= 0):
                        raise ValueError
                except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
                    raise VertexError(code="invalid_auth_response") from None
                headers = {"Content-Type": "application/json", "Accept": "application/json",
                           "Accept-Encoding": "identity", "Authorization": "Bearer " + token}
                raw = await collect(self._url, request.request_json.encode("utf-8"), headers)
                returned_secrets = tuple(value for key, value in token_data.items()
                                         if key in {"access_token", "refresh_token", "id_token", "client_secret"}
                                         and isinstance(value, str) and value)
                try:
                    response = _parse(raw, (*secrets, *returned_secrets))
                except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
                    raise VertexError(code="invalid_response_body") from None
                check_deadline()
                return response

        def worker() -> None:
            try:
                result: ModelResponse | VertexError | VertexUncertain = asyncio.run(run())
            except (VertexError, VertexUncertain) as exc:
                kind = VertexUncertain if isinstance(exc, VertexUncertain) else VertexError
                result = kind(code=exc.code, provider_status=exc.provider_status, auth_requests=auth_requests,
                              header_observation=exc.header_observation)
            except asyncio.LimitOverrunError:
                result = VertexError(code="response_limit", auth_requests=auth_requests)
            except TimeoutError:
                result = VertexUncertain(code="deadline_exceeded", auth_requests=auth_requests)
            except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
                result = VertexError(auth_requests=auth_requests)
            except Exception:
                result = VertexUncertain(auth_requests=auth_requests)
            results.put(result)

        threading.Thread(target=worker, daemon=True).start()
        try:
            result = results.get(timeout=max(0, deadline - time.monotonic()))
        except queue.Empty:
            with lock:
                stopped = True
                count = auth_requests
            raise VertexUncertain(code="deadline_exceeded", auth_requests=count) from None
        if isinstance(result, (VertexError, VertexUncertain)):
            raise result from None
        if time.monotonic() >= deadline:
            raise VertexUncertain(code="deadline_exceeded", auth_requests=auth_requests)
        return result
