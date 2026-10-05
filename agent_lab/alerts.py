"""One explicit, bounded webhook attempt for an unresolved offline outcome.

Ticket37 supports literal loopback HTTP endpoints only. External channels and
recipients need a separate approved policy. No artifact content or URL is saved.
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
from typing import Literal
from urllib.parse import urlsplit

from .reference import S
from .remedy import RemediedRun
from .spec import Declaration


class AlertReceipt(Declaration):
    status: Literal["suppressed", "delivered", "failed"]
    original_run: str
    remedy_digest: str
    payload_digest: str | None = None
    http_status: int | None = None


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
    target = urlsplit(endpoint)
    if (target.scheme != "http" or target.hostname not in {"127.0.0.1", "::1"}
            or target.username is not None or target.password is not None
            or target.fragment or target.query or target.port is None or target.port == 0
            or any(ord(c) < 33 or ord(c) == 127 for c in endpoint)):
        raise ValueError("Alert endpoint must be literal loopback HTTP with an explicit port and no credentials/query")
    if isinstance(timeout, bool) or not math.isfinite(timeout) or not 0 < timeout <= 5:
        raise ValueError("Alert timeout must be positive and at most five seconds")
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
        handle.write(json.dumps({"remedy_digest": remedy_digest, "payload_digest": payload_digest}) + "\n")
    status: Literal["suppressed", "delivered", "failed"] = "suppressed"
    http_status = None
    if payload is not None:
        status = "failed"
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
                headers={"Content-Type": "application/json", "Idempotency-Key": result.original.run_id})
            response = connection.getresponse()
            http_status = response.status
            if not expired.is_set() and time.monotonic() < deadline and 200 <= response.status < 300:
                status = "delivered"
        except (OSError, http.client.HTTPException):
            pass  # Never retain endpoint, response body or exception text.
        finally:
            if timer is not None:
                timer.cancel()
                timer.join()
            connection.close()
    receipt = AlertReceipt(status=status, original_run=result.original.run_id,
        remedy_digest=remedy_digest, payload_digest=payload_digest, http_status=http_status)
    path = root / "alert.json"
    with path.open("x", encoding="utf-8") as handle:
        handle.write(receipt.model_dump_json(indent=2) + "\n")
    return DeliveredAlert(receipt, path)
