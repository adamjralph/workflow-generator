"""Public restricted Gate emission/run seam; no arbitrary Python bindings."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import select
import subprocess
import stat
from typing import Any, Literal, Mapping

from pydantic import BaseModel, ConfigDict

from .gate_bundle import GateVersion, emit_bundle, launch_worker, verify_bundle
from .gate_identity import GateIdentityError, RegisteredOperation, _canonical
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
    def __init__(self, version: GateVersion, *, run_id: str, driver: str, mode: str) -> None:
        if driver not in {"reference", "graph"} or mode not in {"fixture", "operator"}:
            raise GateIdentityError("Unknown driver or decision mode")
        if type(run_id) is not str or not re.fullmatch("[A-Za-z0-9_-]{1,64}", run_id):
            raise GateIdentityError("Invalid run ID")
        verify_bundle(version)
        root = GateArtifactStore(version.directory.parent).root
        runs = root / "runs"
        runs.mkdir(mode=0o700, exist_ok=True)
        info = runs.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise GateIdentityError("Unsafe runs directory or symlink")
        directory = runs / run_id
        directory.mkdir(mode=0o700)  # Never adopt an existing run, including a failed launch.
        GateArtifactStore._publish(directory / "run.json", _canonical({
            "version": 1, "run_id": run_id, "mode": mode, "driver": driver,
            "spec_digest": version.spec_digest, "bundle_digest": version.bundle_digest,
        }))
        self.version = version
        self.directory = directory
        self.process = launch_worker(version, directory, driver)
        try:
            assert self.process.stdin is not None and self.process.stdout is not None
            self.process.stdin.write(json.dumps({"run_id": run_id, "mode": mode, "spec_digest": version.spec_digest,
                                                "bundle_digest": version.bundle_digest}) + "\n")
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
            self.close()
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
                stream.close()

    def __enter__(self) -> GateRun:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


def start_gate(version: GateVersion, *, run_id: str, driver: str = "graph", mode: str = "operator") -> GateRun:
    return GateRun(version, run_id=run_id, driver=driver, mode=mode)
