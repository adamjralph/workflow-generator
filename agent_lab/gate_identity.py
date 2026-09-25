"""Private Gate identity encoding and restricted operation declarations.

This module does not authorize execution. Bundle closure and durable Gate
receipts are separate admission steps; a spec digest alone is insufficient.
"""
from dataclasses import dataclass
import hashlib
import json
from typing import Any, Mapping

from pydantic import ValidationError

from .spec import WorkflowSpec, validate_spec


class GateIdentityError(ValueError):
    """Unverifiable or noncanonical Gate identity."""


_SPEC_DOMAIN = b"workflow-generator/gate-spec/v1\0"
_OPS_DOMAIN = b"workflow-generator/gate-operations/v1\0"


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _digest(domain: bytes, raw: bytes) -> str:
    return hashlib.sha256(domain + raw).hexdigest()


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise GateIdentityError("Duplicate canonical field")
        result[key] = value
    return result


def _parse_canonical(raw: bytes) -> Any:
    if type(raw) is not bytes:
        raise GateIdentityError("Identity must be exact bytes")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(GateIdentityError("Nonfinite value")))
        if raw != _canonical(value):
            raise GateIdentityError("Noncanonical identity bytes")
        return value
    except (UnicodeError, json.JSONDecodeError, TypeError, OverflowError) as exc:
        raise GateIdentityError("Malformed canonical identity") from exc


def freeze_spec(spec: WorkflowSpec) -> tuple[bytes, str]:
    admitted = validate_spec(spec)
    if admitted.spec is None:
        raise GateIdentityError("Invalid workflow declaration")
    raw = _canonical({"version": 1, "spec": admitted.spec.model_dump(mode="json", warnings="error")})
    return raw, _digest(_SPEC_DOMAIN, raw)


def read_spec(raw: bytes, *, expected_digest: str | None = None) -> WorkflowSpec:
    value = _parse_canonical(raw)
    if type(value) is not dict or set(value) != {"version", "spec"} or type(value["version"]) is not int or value["version"] != 1:
        raise GateIdentityError("Unknown spec identity version or fields")
    if expected_digest is not None and _digest(_SPEC_DOMAIN, raw) != expected_digest:
        raise GateIdentityError("Spec identity mismatch")
    try:
        spec = WorkflowSpec.model_validate_json(_canonical(value["spec"]), strict=True)
        if validate_spec(spec).spec is None or freeze_spec(spec)[0] != raw:
            raise GateIdentityError("Invalid or noncanonical spec declaration")
    except (ValidationError, ValueError, TypeError) as exc:
        raise GateIdentityError("Invalid spec declaration") from exc
    return spec


@dataclass(frozen=True)
class RegisteredOperation:
    """Closed data-only opcode, not an arbitrary Python binding."""

    opcode: str
    delta: int


def freeze_operations(operations: Mapping[str, RegisteredOperation]) -> tuple[bytes, str]:
    if (not isinstance(operations, Mapping) or not operations
            or any(type(key) is not str or not key or type(value) is not RegisteredOperation
                   or value.opcode != "add_int_v1" or type(value.delta) is not int
                   or not -1000 <= value.delta <= 1000 for key, value in operations.items())):
        raise GateIdentityError("Only registered bounded add_int_v1 data is admitted")
    raw = _canonical({"version": 1, "operations": {
        key: {"opcode": value.opcode, "delta": value.delta} for key, value in operations.items()}})
    return raw, _digest(_OPS_DOMAIN, raw)
