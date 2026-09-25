"""Owner-only immutable storage for Gate identity *inputs*, not an executable bundle.

No Gate may be approved from these records alone. The emitter/runtime closure,
checkpoint and audit journal remain separate requirements of ticket 29.
"""
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
from typing import Mapping

from .gate_identity import (GateIdentityError, RegisteredOperation, freeze_operations,
                            freeze_spec, read_spec)
from .spec import WorkflowSpec


@dataclass(frozen=True)
class FrozenInputs:
    directory: Path
    spec_digest: str
    operations_digest: str


class GateArtifactStore:
    """Retain canonical inputs in an owner-only external directory."""

    def __init__(self, root: Path) -> None:
        path = Path(root).expanduser()
        if path.is_symlink():
            raise GateIdentityError("Store root cannot be a symlink")
        destination = path.resolve()
        protected: tuple[Path, ...] = (Path.home() / ".hermes", Path(__file__).resolve().parents[1])
        if configured := os.environ.get("HERMES_HOME"):
            protected += (Path(configured).expanduser(),)
        if any(destination.is_relative_to(item.resolve()) for item in protected):
            raise GateIdentityError("Gate store must be outside Hermes and project source")
        destination.mkdir(mode=0o700, parents=True, exist_ok=True)
        info = destination.stat()
        if info.st_uid != os.getuid() or info.st_mode & 0o077 or not stat.S_ISDIR(info.st_mode):
            raise GateIdentityError("Gate store must be owner-only")
        self.root = destination

    def _directory(self, name: str) -> Path:
        if len(name) != 64 or any(c not in "0123456789abcdef" for c in name):
            raise GateIdentityError("Invalid artifact version")
        path = self.root / name
        if path.is_symlink():
            raise GateIdentityError("Artifact directory cannot be a symlink")
        path.mkdir(mode=0o700, exist_ok=True)
        info = path.stat()
        if info.st_uid != os.getuid() or info.st_mode & 0o077 or not stat.S_ISDIR(info.st_mode):
            raise GateIdentityError("Artifact directory must be owner-only")
        return path

    @staticmethod
    def _publish(path: Path, raw: bytes) -> None:
        fd, name = tempfile.mkstemp(prefix=".pending-", dir=path.parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
                os.fchmod(stream.fileno(), 0o400)
            try:
                os.link(name, path, follow_symlinks=False)
            except FileExistsError:
                if GateArtifactStore._read(path, bound=len(raw)) != raw:
                    raise GateIdentityError("Existing artifact has changed")
            directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            os.unlink(name)

    @staticmethod
    def _read(path: Path, *, bound: int = 65536) -> bytes:
        try:
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            with os.fdopen(fd, "rb") as stream:
                info = os.fstat(stream.fileno())
                if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                        or info.st_mode & 0o077 or info.st_size > bound):
                    raise GateIdentityError("Unsafe artifact file")
                raw = stream.read(bound + 1)
                if len(raw) > bound:
                    raise GateIdentityError("Oversized artifact file")
                return raw
        except OSError as exc:
            raise GateIdentityError("Cannot read artifact file") from exc

    def freeze_inputs(self, spec: WorkflowSpec,
                      operations: Mapping[str, RegisteredOperation]) -> FrozenInputs:
        spec_raw, spec_digest = freeze_spec(spec)
        ops_raw, ops_digest = freeze_operations(operations)
        name = hashlib.sha256(("gate-inputs/v1\0" + spec_digest + ops_digest).encode()).hexdigest()
        directory = self._directory(name)
        self._publish(directory / "spec.json", spec_raw)
        self._publish(directory / "operations.json", ops_raw)
        version = FrozenInputs(directory, spec_digest, ops_digest)
        self.verify_inputs(version)
        return version

    def verify_inputs(self, version: FrozenInputs) -> tuple[WorkflowSpec, dict[str, RegisteredOperation]]:
        if type(version) is not FrozenInputs or type(version.spec_digest) is not str or type(version.operations_digest) is not str:
            raise GateIdentityError("Invalid version identity")
        name = hashlib.sha256(("gate-inputs/v1\0" + version.spec_digest + version.operations_digest).encode()).hexdigest()
        if version.directory != self.root / name:
            raise GateIdentityError("Wrong artifact version path")
        directory = self._directory(name)
        spec = read_spec(self._read(directory / "spec.json"), expected_digest=version.spec_digest)
        raw = self._read(directory / "operations.json")
        try:
            data = json.loads(raw)
            if (type(data) is not dict or set(data) != {"version", "operations"}
                    or type(data["version"]) is not int or data["version"] != 1
                    or type(data["operations"]) is not dict):
                raise GateIdentityError("Invalid operation manifest")
            operations: dict[str, RegisteredOperation] = {}
            for key, row in data["operations"].items():
                if type(row) is not dict or set(row) != {"opcode", "delta"}:
                    raise GateIdentityError("Invalid operation record")
                operations[key] = RegisteredOperation(row["opcode"], row["delta"])
            if freeze_operations(operations) != (raw, version.operations_digest):
                raise GateIdentityError("Operation identity mismatch")
            return spec, operations
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            raise GateIdentityError("Invalid operation identity") from exc
