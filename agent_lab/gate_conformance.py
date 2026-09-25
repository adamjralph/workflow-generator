"""Offline conformance of a retained executable, with independent fixtures.

Random run/pause IDs are not canonical workflow events. Each driver's durable
checkpoint identities and head are checked separately; observations include the
pause prefix, so a later operation cannot hide a divergent intermediate state.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import secrets
from typing import Literal, Mapping

from .gate_bundle import GateVersion, verify_bundle
from .gate_identity import GateIdentityError, RegisteredOperation, _canonical, _parse_canonical, freeze_operations, freeze_spec
from .gate_runtime import GateResult, Record, start_gate
from .gate_store import GateArtifactStore
from .spec import WorkflowSpec


class GateExpected(Record):
    terminal: str
    value: int
    used: int
    remaining: int
    events: tuple[tuple[str, str, str, int, int], ...]

    @classmethod
    def observe(cls, result: GateResult) -> GateExpected:
        return cls(terminal=result.terminal, value=result.value, used=result.used, remaining=result.remaining,
                   events=tuple((e.node, e.outcome, e.target, e.used, e.value) for e in result.events))


class GateCase(Record):
    name: str
    reference_decision: Literal["approved", "rejected"] | None
    graph_decision: Literal["approved", "rejected"] | None
    pending: GateExpected
    expected: GateExpected


class GateObservation(Record):
    case: str
    driver: str
    run_id: str
    pending: GateResult
    result: GateResult
    audit_dir: str
    audit_head: str


class GateReport(Record):
    passed: bool
    findings: tuple[str, ...]
    results: tuple[GateObservation, ...]


def _read_audit(directory: Path, run_id: str, result: GateResult,
                version: GateVersion) -> str:
    """Compare retained canonical envelopes with the worker's observations."""
    paths = sorted(directory.glob("[0-9]*.json"))
    if not paths:
        raise GateIdentityError("Missing retained audit chain")
    previous = "0" * 64
    event_head = "0" * 64
    events: list[bytes] = []
    kinds: list[str] = []
    pending_checkpoint = None
    for index, path in enumerate(paths):
        raw = GateArtifactStore._read(path)
        row = _parse_canonical(raw)
        if (path.name != f"{index:08}.json" or row["sequence"] != index
                or row["previous"] != previous or row["run_id"] != run_id
                or type(row["version"]) is not int or row["version"] != 1):
            raise GateIdentityError("Altered retained audit continuity")
        previous = hashlib.sha256(raw).hexdigest()
        kind = row["kind"]
        kinds.append(kind)
        if kind in {"completed", "resolved"}:
            data = row["data"]
            event = data["event"]
            event_bytes = _canonical(event)
            events.append(event_bytes)
            event_head = hashlib.sha256(b"workflow-generator/gate-event/v1\0" +
                                        event_head.encode() + event_bytes).hexdigest()
            if (data["completed_head"] != event_head
                    or data["attestation"].get("spec_digest") != version.spec_digest
                    or data["attestation"].get("bundle_digest") != version.bundle_digest
                    or data["attestation"].get("unverified_origins") != []):
                raise GateIdentityError("Altered retained event evidence")
            if event["outcome"] == "pending":
                pending_checkpoint = data["checkpoint"]
                if pending_checkpoint is None or pending_checkpoint["completed_head"] != event_head:
                    raise GateIdentityError("Missing committed pause")
        elif kind not in {"claim", "decision"}:
            raise GateIdentityError("Unknown audit event kind")
    expected_events = [_canonical(e.model_dump(mode="json")) for e in result.events]
    if (events != expected_events or previous != result.head
            or (result.checkpoint is None and pending_checkpoint is not None)
            or (result.checkpoint is not None and
                _canonical(pending_checkpoint) != _canonical(result.checkpoint.model_dump(mode="json")))):
        raise GateIdentityError("Retained events differ from observed result")
    if "decision" in kinds:
        decision_index = kinds.index("decision")
        if (kinds.count("decision") != 1 or "resolved" not in kinds
                or decision_index >= kinds.index("resolved")
                or "completed" not in kinds[:decision_index]):
            raise GateIdentityError("Invalid retained decision order")
    elif "resolved" in kinds:
        raise GateIdentityError("Resolution lacks decision")
    return previous


def check_gate(spec: WorkflowSpec, operations: Mapping[str, RegisteredOperation], version: GateVersion,
               cases: tuple[GateCase, ...]) -> GateReport:
    findings: list[str] = []
    observations: list[GateObservation] = []
    try:
        manifest, _ = verify_bundle(version)
        if (freeze_spec(spec)[1] != version.spec_digest
                or freeze_operations(operations)[1] != manifest["operations_digest"]):
            raise GateIdentityError("Authored spec/operations differ from retained candidate")
        if not cases or len({case.name for case in cases}) != len(cases):
            raise GateIdentityError("Supply nonempty, uniquely named cases")
        for case in cases:
            pair = []
            for driver, decision in (("reference", case.reference_decision), ("graph", case.graph_decision)):
                run_id = "check-" + secrets.token_hex(12)
                with start_gate(version, run_id=run_id, driver=driver, mode="fixture") as run:
                    pending = run.result
                    _read_audit(run.directory, run_id, pending, version)
                    if GateExpected.observe(pending) != case.pending:
                        findings.append(f"{case.name}/{driver}: pending differs from expected")
                    if decision is not None:
                        if pending.checkpoint is None:
                            raise GateIdentityError("Decision supplied without committed pause")
                        run.submit_fixture(pending.checkpoint, decision)
                        run.continue_gate()
                    result = run.result
                    audit_head = _read_audit(run.directory, run_id, result, version)
                    if GateExpected.observe(result) != case.expected:
                        findings.append(f"{case.name}/{driver}: final differs from expected")
                    if result.checkpoint is not None:
                        cp = result.checkpoint
                        if (cp.spec_digest != version.spec_digest or cp.bundle_digest != version.bundle_digest
                                or cp.run_id != run_id or cp.value != pending.value or cp.used != pending.used):
                            raise GateIdentityError("Checkpoint identity/state mismatch")
                    observations.append(GateObservation(case=case.name, driver=driver, run_id=run_id,
                                                        pending=pending, result=result,
                                                        audit_dir=str(run.directory), audit_head=audit_head))
                    pair.append((GateExpected.observe(pending), GateExpected.observe(result)))
            if pair[0] != pair[1]:
                findings.append(f"{case.name}: independent drivers differ")
    except (ValueError, OSError, KeyError, TypeError) as exc:
        findings.append("refused: " + str(exc))
    return GateReport(passed=not findings, findings=tuple(findings), results=tuple(observations))
