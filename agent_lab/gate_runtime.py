"""Public restricted Gate emission/run seam; no arbitrary Python bindings."""
from __future__ import annotations

import json
import fcntl
import os
from pathlib import Path
import re
import select
import subprocess
import stat
from typing import Any, Literal, Mapping

from pydantic import BaseModel, ConfigDict

from .gate_bundle import GateVersion, emit_bundle, launch_worker, verify_bundle
from .gate_identity import GateIdentityError, RegisteredOperation, _canonical, _parse_canonical
from .gate_store import GateArtifactStore
from .spec import GateNode, Route, TransformNode, WorkflowSpec, validate_spec


class Record(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class GateEvent(Record):
    node: str
    outcome: str
    target: str
    used: int
    value: int


class GateCheckpoint(Record):
    version: Literal[1]
    run_id: str
    gate: str
    pause: str
    value: int
    used: int
    remaining: int
    spec_digest: str
    bundle_digest: str
    prior_head: str
    completed_head: str


class GateResult(Record):
    terminal: str
    value: int
    used: int
    remaining: int
    events: tuple[GateEvent, ...]
    checkpoint: GateCheckpoint | None
    head: str


def emit_gate(spec: WorkflowSpec, operations: Mapping[str, RegisteredOperation], *, store: Path) -> GateVersion:
    admitted = validate_spec(spec)
    if admitted.spec is None or type(spec) is not WorkflowSpec:
        raise GateIdentityError("Invalid workflow")
    if sum(type(node) is GateNode for node in spec.nodes) != 1:
        raise GateIdentityError("Exactly one Gate is supported")
    if any(type(node) not in {GateNode, TransformNode} for node in spec.nodes):
        raise GateIdentityError("Only registered Transform and Gate nodes are supported")
    if any(type(edge) is not Route for edge in spec.edges):
        raise GateIdentityError("Only non-parallel Routes are supported")
    expected = {"rejected": "REJECTED", "pending": "PENDING", "invalid": "FAILED_VALIDATION"}
    for node in spec.nodes:
        if isinstance(node, TransformNode) and (node.model_operation or node.operation_version or node.schema_version
                                               or node.outcomes != ("done",)):
            raise GateIdentityError("Only closed add operations are supported")
        if isinstance(node, GateNode):
            for edge in spec.edges:
                if isinstance(edge, Route) and edge.source == node.id and edge.outcome in expected and edge.target != expected[edge.outcome]:
                    raise GateIdentityError("Gate nonapproval routes must terminate")
    if not set(expected.values()) | {"FAILED_BUDGET"} <= set(spec.terminals):
        raise GateIdentityError("Missing safety terminals")
    keys = {node.operation for node in spec.nodes if isinstance(node, TransformNode)}
    if keys != set(operations):
        raise GateIdentityError("Operation set must exactly match the admitted graph")
    return emit_bundle(spec, operations, store=store)


class GateRun:
    def __init__(self, version: GateVersion, *, run_id: str, driver: str, mode: str,
                 recovery: bool = False, crash_at: tuple[int, str] | None = None) -> None:
        if driver not in {"reference", "graph"} or mode not in {"fixture", "operator"}:
            raise GateIdentityError("Unknown driver or decision mode")
        if type(run_id) is not str or not re.fullmatch("[A-Za-z0-9_-]{1,64}", run_id):
            raise GateIdentityError("Invalid run ID")
        if crash_at is not None and (type(crash_at) is not tuple or len(crash_at) != 2
                or type(crash_at[0]) is not int or not 0 <= crash_at[0] <= 8
                or crash_at[1] not in {"before_file", "after_file", "after_link", "after_dirsync", "after_unlink"}):
            raise GateIdentityError("Invalid crash injection boundary")
        verify_bundle(version)
        root = GateArtifactStore(version.directory.parent).root
        runs = root / "runs"
        runs.mkdir(mode=0o700, exist_ok=True)
        info = runs.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise GateIdentityError("Unsafe runs directory or symlink")
        directory = runs / run_id
        if not recovery:
            directory.mkdir(mode=0o700)  # Never adopt an existing run, including a failed launch.
            GateArtifactStore._publish(directory / "run.json", _canonical({
                "version": 1, "run_id": run_id, "mode": mode, "driver": driver,
                "spec_digest": version.spec_digest, "bundle_digest": version.bundle_digest,
            }))
        info = directory.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise GateIdentityError("Unsafe run directory")
        self.version = version
        self.directory = directory
        # The lock spans host validation, worker launch and every continuation.
        # A closed/crashed controller releases it; a completed run remains ineligible.
        try:
            self._claim = os.open(directory / "claim.lock", os.O_RDWR | os.O_NOFOLLOW |
                                  (0 if recovery else os.O_CREAT | os.O_EXCL), 0o600)
        except OSError as exc:
            raise GateIdentityError("Missing or unsafe continuation claim") from exc
        try:
            info = os.fstat(self._claim)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
                raise GateIdentityError("Unsafe continuation claim")
            try:
                fcntl.flock(self._claim, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise GateIdentityError("Run already has an exclusive continuation claim") from exc
            if recovery:
                from .gate_cli import inspect_pause
                if mode != "operator":
                    raise GateIdentityError("Only operator pauses can restart")
                metadata = _parse_canonical(GateArtifactStore._read(directory / "run.json"))
                if metadata != {"version": 1, "run_id": run_id, "mode": mode, "driver": driver,
                                "spec_digest": version.spec_digest, "bundle_digest": version.bundle_digest}:
                    raise GateIdentityError("Recovery metadata changed")
                _, checkpoint = inspect_pause(root, run_id)
                if checkpoint.spec_digest != version.spec_digest or checkpoint.bundle_digest != version.bundle_digest:
                    raise GateIdentityError("Recovery identity changed")
                if not (directory / "decision.json").exists():
                    raise GateIdentityError("Committed operator decision required")
            self.process = launch_worker(version, directory, driver)
            assert self.process.stdin is not None and self.process.stdout is not None
            self.process.stdin.write(json.dumps({"run_id": run_id, "mode": mode, "spec_digest": version.spec_digest,
                                                "bundle_digest": version.bundle_digest,
                                                "recovery": recovery, "crash_at": crash_at}) + "\n")
            self.process.stdin.flush()
            if not select.select([self.process.stdout], [], [], 60)[0]:
                raise GateIdentityError("Worker timed out before attestation")
            line = self.process.stdout.readline()
            if not line:
                assert self.process.stderr is not None
                raise GateIdentityError("Worker refused executable closure: " + self.process.stderr.read())
            response = json.loads(line)
            self.result = GateResult.model_validate_json(json.dumps(response["result"]))
            self.attestation: dict[str, Any] = response["attestation"]
        except BaseException:
            if hasattr(self, "process"):
                self.close()
            else:
                os.close(self._claim)
            raise

    def _exchange(self, command: dict[str, Any]) -> GateResult:
        verify_bundle(self.version)
        if self.process.poll() is not None:
            raise GateIdentityError("Worker is closed; restart is not supported")
        assert self.process.stdin is not None and self.process.stdout is not None
        self.process.stdin.write(json.dumps(command) + "\n")
        self.process.stdin.flush()
        if not select.select([self.process.stdout], [], [], 60)[0]:
            self.close()
            raise GateIdentityError("Worker command timed out")
        line = self.process.stdout.readline()
        if not line:
            raise GateIdentityError("Worker failed before durable completion")
        response = json.loads(line)
        if "error" in response:
            raise GateIdentityError(response["error"])
        self.result = GateResult.model_validate_json(json.dumps(response["result"]))
        self.attestation = response["attestation"]
        return self.result

    def submit_fixture(self, checkpoint: GateCheckpoint, decision: str) -> None:
        try:
            checked = GateCheckpoint.model_validate(dict(checkpoint))
        except (ValueError, TypeError) as exc:
            raise GateIdentityError("Invalid typed checkpoint") from exc
        self._exchange({"command": "fixture", "checkpoint": checked.model_dump(mode="json"), "decision": decision})

    def continue_gate(self) -> GateResult:
        return self._exchange({"command": "continue"})

    def close(self) -> None:
        if self.process.poll() is None:
            try:
                assert self.process.stdin is not None
                self.process.stdin.write('{"command":"close"}\n')
                self.process.stdin.flush()
                self.process.wait(timeout=5)
            except (OSError, TimeoutError, subprocess.TimeoutExpired):
                self.process.kill()
                self.process.wait()
        for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
            if stream is not None:
                try:
                    stream.close()
                except OSError:
                    # A crashed worker can leave a buffered stdin flush broken.
                    pass
        if self._claim >= 0:
            os.close(self._claim)
            self._claim = -1

    def __enter__(self) -> GateRun:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


def start_gate(version: GateVersion, *, run_id: str, driver: str = "graph", mode: str = "operator",
               crash_at: tuple[int, str] | None = None) -> GateRun:
    return GateRun(version, run_id=run_id, driver=driver, mode=mode, crash_at=crash_at)


def recover_gate(store: Path, *, run_id: str, crash_at: tuple[int, str] | None = None) -> GateRun:
    """Resume only an untouched committed operator pause, from retained bytes."""
    if type(run_id) is not str or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", run_id):
        raise GateIdentityError("Invalid run ID")
    root = GateArtifactStore(store).root
    # Metadata is verified again under the exclusive claim in GateRun.
    directory = root / "runs" / run_id
    for path in (root / "runs", directory):
        info = path.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise GateIdentityError("Unsafe run directory")
    metadata = _parse_canonical(GateArtifactStore._read(directory / "run.json"))
    if (type(metadata) is not dict or set(metadata) != {"version", "run_id", "mode", "driver", "spec_digest", "bundle_digest"}
            or metadata["run_id"] != run_id or metadata["mode"] != "operator"
            or metadata["driver"] not in {"reference", "graph"} or metadata["version"] != 1):
        raise GateIdentityError("Invalid recovery metadata")
    version = GateVersion(root / metadata["bundle_digest"], metadata["spec_digest"], metadata["bundle_digest"])
    try:
        verify_bundle(version)
    except OSError as exc:
        raise GateIdentityError("Missing retained executable version") from exc
    return GateRun(version, run_id=run_id, driver=metadata["driver"], mode="operator",
                   recovery=True, crash_at=crash_at)
