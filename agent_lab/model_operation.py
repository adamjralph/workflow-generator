"""Explicit model-operation contracts; only a source may perform model I/O."""
from collections.abc import Callable
from dataclasses import dataclass
import hashlib
import json
from typing import TYPE_CHECKING, Generic, Literal, Protocol, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

if TYPE_CHECKING:
    from .reference import TransformResult

S = TypeVar("S", bound=BaseModel)


class ModelRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    operation: str
    operation_version: str
    schema_version: str
    input_digest: str
    request_json: str

    @field_validator("request_json")
    @classmethod
    def canonical_request(cls, value: str) -> str:
        parsed = json.loads(value)
        if json.dumps(parsed, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) != value:
            raise ValueError("Request must be exact canonical JSON")
        return value

    @property
    def digest(self) -> str:
        material = json.dumps(self.model_dump(), ensure_ascii=False, sort_keys=True,
                              separators=(",", ":"), allow_nan=False)
        return hashlib.sha256(material.encode("utf-8")).hexdigest()


class ModelResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    body: str
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    reasoning_tokens: int | None = Field(default=None, ge=0)
    cache_read_tokens: int | None = Field(default=None, ge=0)
    provider_request_id: str | None = None
    resolved_model: str | None = None
    # OAuth traffic is separate from model-generation usage, including unknown usage.
    auth_requests: int = Field(default=0, ge=0, le=1)


class HeaderObservation(BaseModel):
    """Versioned shape of one rejected, bounded HTTP header section; no raw data."""
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    version: Literal[1] = 1
    section_bytes: int = Field(ge=4, le=65536)
    field_lines: int = Field(ge=0, le=32766)
    content_type: bool
    content_length: bool
    transfer_encoding: bool
    content_encoding: bool

    @field_validator("version", mode="before")
    @classmethod
    def strict_version(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("Observation version must be an integer")
        return value


class ModelFailure(BaseModel):
    """Sanitized replayable failure identity; never arbitrary exception text."""
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    status: Literal["failed", "uncertain"]
    code: Literal["credentials_unavailable", "provider_rejected", "invalid_response",
                  "response_limit", "transport_incomplete", "deadline_exceeded",
                  "source_failure", "invalid_output", "evidence_failure", "preflight_failed",
                  "invalid_request", "invalid_http_headers", "invalid_http_framing",
                  "invalid_auth_response", "invalid_response_body", "invalid_http_status",
                  "invalid_http_header", "duplicate_http_header", "unsupported_http_content_type",
                  "unsupported_http_content_encoding", "missing_http_content_type",
                  "empty_http_content_type"]
    provider_status: int | None = Field(default=None, ge=100, le=599)
    header_observation: HeaderObservation | None = Field(default=None, exclude_if=lambda value: value is None)


class ModelSource(Protocol):
    @property
    def mode(self) -> Literal["live", "fixture", "recorded"]: ...

    def invoke(self, request: ModelRequest) -> ModelResponse: ...


@dataclass(frozen=True)
class ModelOperation(Generic[S]):
    operation: str
    version: str
    schema_version: str
    state_type: type[S]
    prepare: Callable[[S], ModelRequest]
    source: ModelSource
    apply: Callable[[S, ModelResponse], "TransformResult[S]"]


def validate_request(operation: ModelOperation[S], request: ModelRequest) -> ModelRequest:
    if type(request) is not ModelRequest:
        raise ValueError("Expected ModelRequest")
    request = ModelRequest.model_validate(request.model_dump(), strict=True)
    if (request.operation, request.operation_version, request.schema_version) != (
            operation.operation, operation.version, operation.schema_version):
        raise ValueError("Request operation contract differs")
    return request


def validate_response(response: ModelResponse) -> ModelResponse:
    if type(response) is not ModelResponse:
        raise ValueError("Expected ModelResponse")
    return ModelResponse.model_validate(response.model_dump(), strict=True)
