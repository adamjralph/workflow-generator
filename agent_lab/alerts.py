"""One explicit, bounded webhook attempt for an unresolved offline outcome.

Ticket37 supports literal loopback HTTP endpoints only. External channels and
recipients need a separate approved policy. Trusted adapters consume the same
redacted envelope; implementing one is not send approval. No URL is saved.
"""
from dataclasses import dataclass
import hashlib
import http.client
import json
import math
import socket
import threading
import time
from pathlib import Path
from typing import Literal, Protocol
from urllib.parse import urlsplit

from pydantic import model_validator

from .reference import S
from .remedy import RemediedRun
from .spec import Declaration


class AlertReservation(Declaration):
    original_run: str
    remedy_digest: str
    payload_digest: str | None


class AlertReceipt(Declaration):
    status: Literal["suppressed", "delivered", "failed"]
    original_run: str
    remedy_digest: str
    payload_digest: str | None = None
    http_status: int | None = None
    completion: Literal["suppressed", "acknowledged", "rejected", "unknown"] = "unknown"


@dataclass(frozen=True)
class DeliveredAlert:
    receipt: AlertReceipt
    receipt_path: Path


def deliver_outcome_alert(result: RemediedRun[S], *, endpoint: str,
                          timeout: float = 2.0, private_fields: tuple[str, ...] = ()) -> DeliveredAlert:
    """Send once to an explicitly supplied local receiver, or suppress success.

    An exclusive reservation precedes the request. Re-entry raises rather than
    retries: a timeout can mean the receiver accepted it. An interrupted attempt
    has a reservation but no receipt, so delivery remains unknown. HTTP 2xx means
    receiver acknowledgement, not proof a human read it. Callers are trusted local
    code; this API is neither a sandbox nor an external-send approval mechanism.
    private_fields removes those declared string constraints from transport and
    lists the redacted field names. It never changes the local declaration.
    """
    return deliver_alert_with_adapter(result, adapter=LoopbackAlertAdapter(endpoint),
        timeout=timeout, private_fields=private_fields)


def deliver_alert_with_adapter(result: RemediedRun[S], *, adapter: "AlertAdapter",
                               timeout: float = 2.0, private_fields: tuple[str, ...] = ()) -> DeliveredAlert:
    """Reserve the concrete envelope before one trusted adapter invocation.

    The adapter must enforce timeout, perform at most one attempt, and return only
    transport acknowledgement/rejection. Unknown completion consumes the attempt.
    Implementing an adapter does not authorize a destination or external send.
    """
    _validate_timeout(timeout)
    declaration = (result.repair or result.original).verdict.declaration
    if (len(set(private_fields)) != len(private_fields)
            or not set(private_fields) <= {item.field for item in declaration.string_fields}):
        raise ValueError("Private alert fields must name distinct declared string constraints")
    saved = result.receipt_path.read_bytes()
    if json.loads(saved) != result.receipt.model_dump(mode="json"):
        raise ValueError("Saved remedy receipt changed")
    attempts = (result.original,) + ((result.repair,) if result.repair else ())
    digests = (result.receipt.original_verdict_digest, result.receipt.repair_verdict_digest)
    for attempt, digest in zip(attempts, digests):
        raw = attempt.verdict_path.read_bytes()
        if (hashlib.sha256(raw).hexdigest() != digest
                or json.loads(raw) != attempt.verdict.model_dump(mode="json")):
            raise ValueError("Saved outcome verdict changed")
    root = result.original.root
    remedy_digest = hashlib.sha256(saved).hexdigest()
    payload = None
    if not result.passed:
        latest = result.repair or result.original
        expected = latest.verdict.declaration.model_dump(mode="json")
        # Redact caller-designated attribution values only in transport. The
        # original declaration/digests remain intact in local audit evidence.
        expected["string_fields"] = [item for item in expected["string_fields"]
                                     if item["field"] not in private_fields]
        if private_fields:
            expected["redacted_string_fields"] = list(private_fields)
        payload = json.dumps({"event": "workflow.outcome.unresolved", "original_run": result.original.run_id,
            "repair_run": result.receipt.repair_run, "status": result.receipt.status,
            "reserved_steps": result.receipt.reserved_steps, "step_allowance": result.receipt.step_allowance,
            "terminal": latest.execution.terminal, "expected": expected,
            "unmet": [finding.model_dump(mode="json") for finding in latest.verdict.findings],
            "remedy_digest": remedy_digest, "action": "Inspect saved evidence; no further repair is authorized"},
            separators=(",", ":")).encode("utf-8")
        if len(payload) > 65536:
            raise ValueError("Alert payload exceeds 64 KiB")
    payload_digest = hashlib.sha256(payload).hexdigest() if payload else None
    with (root / "alert-reserved.json").open("x", encoding="utf-8") as handle:
        handle.write(AlertReservation(original_run=result.original.run_id, remedy_digest=remedy_digest,
            payload_digest=payload_digest).model_dump_json() + "\n")
    status: Literal["suppressed", "delivered", "failed"] = "suppressed"
    completion: Literal["suppressed", "acknowledged", "rejected", "unknown"] = "suppressed"
    http_status = None
    if payload is not None:
        status, completion = "failed", "unknown"
        try:
            acknowledgement = adapter.send(payload, attempt_id=result.original.run_id, timeout=timeout)
            # Validate the returned value even for trusted adapters; malformed replies
            # cannot establish an acknowledgement or permit another attempt.
            acknowledgement = TransportReceipt.model_validate(acknowledgement)
            completion = acknowledgement.completion
            http_status = acknowledgement.http_status
            if completion == "acknowledged":
                status = "delivered"
        except Exception:
            pass  # No endpoint, adapter exception or response content in audit.
    receipt = AlertReceipt(status=status, original_run=result.original.run_id,
        remedy_digest=remedy_digest, payload_digest=payload_digest, http_status=http_status, completion=completion)
    path = root / "alert.json"
    with path.open("x", encoding="utf-8") as handle:
        handle.write(receipt.model_dump_json(indent=2) + "\n")
    return DeliveredAlert(receipt, path)


class TransportReceipt(Declaration):
    """Transport acknowledgement only; never a human-read or acceptance claim."""
    completion: Literal["acknowledged", "rejected", "unknown"]
    http_status: int | None = None

    @model_validator(mode="after")
    def consistent_http_status(self) -> "TransportReceipt":
        if self.http_status is not None:
            if not 100 <= self.http_status <= 599:
                raise ValueError("Invalid HTTP acknowledgement status")
            if ((self.completion == "acknowledged" and not 200 <= self.http_status < 300)
                    or (self.completion == "rejected" and 200 <= self.http_status < 300)):
                raise ValueError("HTTP status contradicts acknowledgement")
        return self


class AlertAdapter(Protocol):
    def send(self, payload: bytes, *, attempt_id: str, timeout: float) -> TransportReceipt:
        """One bounded attempt; no retry, fallback, redirect or persisted secrets."""
        ...


def _validate_timeout(timeout: float) -> None:
    if isinstance(timeout, bool) or not math.isfinite(timeout) or not 0 < timeout <= 5:
        raise ValueError("Alert timeout must be positive and at most five seconds")


@dataclass(frozen=True)
class LoopbackAlertAdapter:
    endpoint: str

    def __post_init__(self) -> None:
        target = urlsplit(self.endpoint)
        if (target.scheme != "http" or target.hostname not in {"127.0.0.1", "::1"}
            or target.username is not None or target.password is not None
            or target.fragment or target.query or target.port is None or target.port == 0
            or any(ord(c) < 33 or ord(c) == 127 for c in self.endpoint)):
            raise ValueError("Alert endpoint must be literal loopback HTTP with an explicit port and no credentials/query")

    def send(self, payload: bytes, *, attempt_id: str, timeout: float) -> TransportReceipt:
        _validate_timeout(timeout)
        target = urlsplit(self.endpoint)
        assert target.hostname is not None
        completion: Literal["acknowledged", "rejected", "unknown"] = "unknown"
        http_status = None
        connection = http.client.HTTPConnection(target.hostname, target.port, timeout=timeout)
        deadline = time.monotonic() + timeout
        timer = None
        expired = threading.Event()
        try:
            connection.connect()
            remaining = deadline - time.monotonic()
            if remaining <= 0 or connection.sock is None:
                raise TimeoutError()
            delivery_socket = connection.sock
            def expire() -> None:
                expired.set()
                try:
                    delivery_socket.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
            timer = threading.Timer(remaining, expire)
            timer.daemon = True
            timer.start()
            connection.request("POST", target.path or "/", body=payload,
                headers={"Content-Type": "application/json", "Idempotency-Key": attempt_id})
            response = connection.getresponse()
            http_status = response.status
            if not expired.is_set() and time.monotonic() < deadline and 200 <= response.status < 300:
                completion = "acknowledged"
            elif not expired.is_set() and time.monotonic() < deadline:
                completion = "rejected"
        except (OSError, http.client.HTTPException):
            pass  # Never retain endpoint, response body or exception text.
        finally:
            if timer is not None:
                timer.cancel()
                timer.join()
            connection.close()
        return TransportReceipt(completion=completion, http_status=http_status)


@dataclass(frozen=True)
class AlertAudit:
    state: Literal["unattempted", "reserved", "completed"]
    receipt: AlertReceipt | None = None


def read_alert_audit(result: RemediedRun[S]) -> AlertAudit:
    """Read saved attempt state without invoking transport or authorizing resend.

    A reservation without a receipt means unknown completion, even after a crash.
    Saved receipts are checked against the reservation and exact remedy bytes.
    """
    root = result.original.root
    reservation_path = root / "alert-reserved.json"
    receipt_path = root / "alert.json"
    if not reservation_path.exists():
        if receipt_path.exists():
            raise ValueError("Alert receipt lacks reservation")
        return AlertAudit("unattempted")
    reservation = AlertReservation.model_validate_json(reservation_path.read_bytes())
    saved = result.receipt_path.read_bytes()
    if (json.loads(saved) != result.receipt.model_dump(mode="json")
            or reservation.original_run != result.original.run_id
            or reservation.remedy_digest != hashlib.sha256(saved).hexdigest()):
        raise ValueError("Alert reservation remedy mismatch")
    if not receipt_path.exists():
        return AlertAudit("reserved")
    receipt = AlertReceipt.model_validate_json(receipt_path.read_bytes())
    if (receipt.original_run != result.original.run_id
            or receipt.remedy_digest != reservation.remedy_digest
            or receipt.payload_digest != reservation.payload_digest
            or (receipt.status == "delivered" and receipt.completion != "acknowledged")
            or (receipt.status == "suppressed" and (receipt.completion != "suppressed" or receipt.payload_digest is not None))
            or (receipt.status == "failed" and receipt.completion not in ("rejected", "unknown"))):
        raise ValueError("Alert receipt reservation mismatch")
    if receipt.completion != "suppressed":
        TransportReceipt(completion=receipt.completion, http_status=receipt.http_status)
    return AlertAudit("completed", receipt)
