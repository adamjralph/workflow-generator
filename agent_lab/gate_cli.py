"""Owner-only, explicitly invoked local Gate decision CLI.

Not a remote API or person-authentication mechanism: every process with this
OS account's access can read the signing key and submit a decision.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import stat
import sys
import time
from typing import Any

from .gate_bundle import GateVersion, verify_bundle
from .gate_identity import GateIdentityError, _canonical, _parse_canonical, read_spec
from .gate_runtime import GateCheckpoint
from .gate_store import GateArtifactStore
from .spec import GateNode, Route, TransformNode


def _operator_key(directory: Path) -> bytes:
    fd = os.open(directory / "operator.key", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if info.st_uid != os.getuid() or info.st_mode & 0o077 or not stat.S_ISREG(info.st_mode):
            raise GateIdentityError("Unsafe operator authority file")
        key = stream.read(33)
    if len(key) != 32:
        raise GateIdentityError("Invalid operator authority key")
    return key


def _check_pause_history(rows: list[dict[str, Any]], files: dict[str, bytes],
                         checkpoint: GateCheckpoint, run_id: str,
                         spec_digest: str, bundle_digest: str, key: bytes) -> None:
    """Validate the completed route/Gate prefix before recording authority.

    This is deliberately independent of the worker's in-memory journal: the
    operator must not sign an altered event merely because its link is intact.
    """
    spec = read_spec(files["/app/spec.json"], expected_digest=spec_digest)
    operations = _parse_canonical(files["/app/operations.json"])["operations"]
    nodes = {node.id: node for node in spec.nodes}
    routes = {(edge.source, edge.outcome): edge.target for edge in spec.edges
              if isinstance(edge, Route)}
    if not rows or len(rows) % 2:
        raise GateIdentityError("Incomplete pause event chain")
    current, value, used, event_head = spec.entry, 0, 0, "0" * 64
    for index in range(0, len(rows), 2):
        claim, completed = rows[index:index + 2]
        if current not in nodes or used >= spec.budget:
            raise GateIdentityError("Invalid paused route or budget")
        if (claim["kind"] != "claim" or _canonical(claim["data"]) != _canonical({
                "node": current, "used_before": used, "value_before": value})
                or completed["kind"] != "completed"):
            raise GateIdentityError("Invalid pre-dispatch claim")
        node = nodes[current]
        used += 1
        if isinstance(node, GateNode):
            outcome = "pending"
        elif isinstance(node, TransformNode):
            operation = operations[node.operation]
            if operation["opcode"] != "add_int_v1" or type(operation["delta"]) is not int:
                raise GateIdentityError("Unregistered paused operation")
            value += operation["delta"]
            outcome = "done"
        else:
            raise GateIdentityError("Unsupported paused node")
        target = routes[(current, outcome)]
        event = {"node": current, "outcome": outcome, "target": target,
                 "used": used, "value": value}
        event_head = hashlib.sha256(b"workflow-generator/gate-event/v1\0" +
                                    event_head.encode() + _canonical(event)).hexdigest()
        data = completed["data"]
        attestation = data["attestation"]
        expected_data = {"event", "completed_head", "checkpoint", "attestation"}
        if isinstance(node, GateNode):
            expected_data.add("pause_proof")
            unsigned = {field: value for field, value in data.items() if field != "pause_proof"}
            signed = b"workflow-generator/gate-pause/v1\0" + _canonical({
                "previous": completed["previous"], "data": unsigned})
            if (type(data["pause_proof"]) is not str or not hmac.compare_digest(
                    data["pause_proof"], hmac.digest(key, signed, "sha256").hex())):
                raise GateIdentityError("Altered committed pause proof")
        if (set(data) != expected_data
                or set(attestation) != {"retained_runtime", "unverified_origins", "pid",
                                        "modules", "native", "excluded_imports", "spec_digest", "bundle_digest"}
                or type(attestation["pid"]) is not int or attestation["pid"] <= 0
                or attestation["excluded_imports"] != ["_tkinter", "tkinter"]
                or any(type(origins) is not dict or any(
                    path not in files or type(digest) is not str
                    or hashlib.sha256(files[path]).hexdigest() != digest
                    for path, digest in origins.items())
                    for origins in (attestation["modules"], attestation["native"]))
                or _canonical(data["event"]) != _canonical(event) or data["completed_head"] != event_head
                or attestation["spec_digest"] != spec_digest
                or attestation["bundle_digest"] != bundle_digest
                or attestation["retained_runtime"] is not True
                or attestation["unverified_origins"] != []):
            raise GateIdentityError("Altered completed event evidence")
        if isinstance(node, GateNode):
            if index != len(rows) - 2 or target != "PENDING" or data["checkpoint"] is None:
                raise GateIdentityError("Invalid pending Gate endpoint")
            if (checkpoint.run_id != run_id or checkpoint.gate != current
                    or checkpoint.version != 1 or not re.fullmatch(r"[0-9a-f]{32}", checkpoint.pause)
                    or checkpoint.spec_digest != spec_digest or checkpoint.bundle_digest != bundle_digest
                    or checkpoint.value != value or checkpoint.used != used
                    or checkpoint.remaining != spec.budget - used
                    or checkpoint.prior_head != completed["previous"]
                    or checkpoint.completed_head != event_head
                    or _canonical(data["checkpoint"]) != _canonical(checkpoint.model_dump(mode="json"))):
                raise GateIdentityError("Altered Gate checkpoint")
        elif data["checkpoint"] is not None:
            raise GateIdentityError("Unexpected pre-Gate checkpoint")
        current = target
    if not isinstance(nodes.get(checkpoint.gate), GateNode):
        raise GateIdentityError("Unknown paused Gate")


def inspect_pause(store: Path, run_id: str) -> tuple[Path, GateCheckpoint]:
    root = GateArtifactStore(store).root
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", run_id):
        raise GateIdentityError("Invalid run ID")
    directory = root / "runs" / run_id
    for path in (root / "runs", directory):
        info = path.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise GateIdentityError("Run directory must be owner-only, not a symlink")
    names = {path.name for path in directory.iterdir()}
    numbered = {name for name in names if re.fullmatch(r"[0-9]{8}\.json", name)}
    if names - ({"run.json", "operator.key", "claim.lock", "decision.json"} | numbered):
        raise GateIdentityError("Unexpected or incomplete run publication")
    metadata = _parse_canonical(GateArtifactStore._read(directory / "run.json"))
    if (set(metadata) != {"version", "run_id", "mode", "driver", "spec_digest", "bundle_digest"}
            or type(metadata["version"]) is not int or metadata["version"] != 1
            or metadata["mode"] != "operator" or metadata["run_id"] != run_id
            or metadata["driver"] not in {"reference", "graph"}):
        raise GateIdentityError("CLI cannot authorize fixtures or another run")
    bundle = metadata["bundle_digest"]
    _, files = verify_bundle(GateVersion(root / bundle, metadata["spec_digest"], bundle))
    previous = "0" * 64
    checkpoint = None
    decided = False
    rows: list[dict[str, Any]] = []
    for sequence, path in enumerate(sorted(directory.glob("[0-9]*.json"))):
        raw = GateArtifactStore._read(path)
        row = _parse_canonical(raw)
        if (set(row) != {"version", "sequence", "previous", "kind", "run_id", "data"}
                or path.name != f"{sequence:08}.json"
                or type(row["sequence"]) is not int or row["sequence"] != sequence
                or type(row["version"]) is not int or row["version"] != 1
                or row["previous"] != previous or row["run_id"] != run_id):
            raise GateIdentityError("Invalid journal continuity")
        previous = hashlib.sha256(raw).hexdigest()
        rows.append(row)
        if row["kind"] == "completed" and row["data"]["checkpoint"] is not None:
            checkpoint = GateCheckpoint.model_validate_json(_canonical(row["data"]["checkpoint"]))
            if checkpoint.prior_head != row["previous"]:
                raise GateIdentityError("Invalid checkpoint head")
        elif row["kind"] in {"resolved", "decision"}:
            decided = True
    if checkpoint is None or decided:
        raise GateIdentityError("No unconsumed committed pause")
    if len(rows) < 2 or len(rows) % 2:
        raise GateIdentityError("Only an untouched committed Gate pause can resume")
    if (checkpoint.run_id != run_id or checkpoint.spec_digest != metadata["spec_digest"]
            or checkpoint.bundle_digest != bundle):
        raise GateIdentityError("Checkpoint identity mismatch")
    _check_pause_history(rows, files, checkpoint, run_id, metadata["spec_digest"], bundle,
                         _operator_key(directory))
    return directory, checkpoint


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    for field in ("gate", "pause", "spec", "bundle"):
        parser.add_argument("--" + field)
    parser.add_argument("action", choices=("inspect", "approve", "reject"))
    args = parser.parse_args(argv)
    try:
        directory, checkpoint = inspect_pause(args.store, args.run_id)
        if args.action == "inspect":
            print(json.dumps(checkpoint.model_dump(mode="json"), sort_keys=True))
            return 0
        if (args.gate, args.pause, args.spec, args.bundle) != (
                checkpoint.gate, checkpoint.pause, checkpoint.spec_digest, checkpoint.bundle_digest):
            raise GateIdentityError("Explicit run/Gate/pause/spec/bundle scope does not match")
        # The key is local OS-account authority, never a caller-supplied identity.
        fd = os.open(directory / "operator.key", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            if info.st_uid != os.getuid() or info.st_mode & 0o077 or not stat.S_ISREG(info.st_mode):
                raise GateIdentityError("Unsafe operator authority file")
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            key = stream.read(33)
            if len(key) != 32:
                raise GateIdentityError("Invalid operator authority key")
            # Recheck the live durable state under the submission lock.
            _, current = inspect_pause(args.store, args.run_id)
            if current != checkpoint:
                raise GateIdentityError("Pause changed")
            record: dict[str, Any] = {
                "version": 1, "checkpoint": checkpoint.model_dump(mode="json"),
                "decision": "approved" if args.action == "approve" else "rejected",
                "authority": "local-os-account", "uid": os.getuid(), "recorded_ns": time.time_ns(),
            }
            path = directory / "decision.json"
            if path.exists() or path.is_symlink():
                envelope = _parse_canonical(GateArtifactStore._read(path))
                original = envelope["record"]
                if not hmac.compare_digest(envelope["mac"], hmac.digest(key, _canonical(original), "sha256").hex()):
                    raise GateIdentityError("Forged decision")
                if {k: v for k, v in original.items() if k != "recorded_ns"} != {
                        k: v for k, v in record.items() if k != "recorded_ns"}:
                    raise GateIdentityError("Conflicting decision")
                record = original
            else:
                envelope = {"record": record, "mac": hmac.digest(key, _canonical(record), "sha256").hex()}
                GateArtifactStore._publish(path, _canonical(envelope))
                if GateArtifactStore._read(path) != _canonical(envelope):
                    raise GateIdentityError("Decision read-back failed")
        print(json.dumps(record, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print("Gate decision refused: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
