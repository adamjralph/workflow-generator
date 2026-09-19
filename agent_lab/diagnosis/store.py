"""Immutable diagnosis versions, addressed by the SHA-256 of their exact bytes."""
import hashlib
import json
import os
import tempfile
from pathlib import Path

from typing import Annotated

from pydantic import Field, TypeAdapter

from . import DiagnosisError, DiagnosisRecord, LegacyDiagnosisRecord, StoredDiagnosis


RECORD_READER: TypeAdapter[DiagnosisRecord | LegacyDiagnosisRecord] = TypeAdapter(Annotated[
    DiagnosisRecord | LegacyDiagnosisRecord, Field(discriminator="schema_version"),
])


class DiagnosisStore:
    def __init__(self, root: Path, *, protected_roots: tuple[Path, ...] = ()):
        self.root = root.resolve()
        protected = (Path.home() / ".hermes", Path(__file__).resolve().parents[2], *protected_roots)
        if configured := os.environ.get("HERMES_HOME"):
            protected += (Path(configured),)
        self.protected_roots = tuple(path.resolve() for path in protected)
        self._check_outside_hermes(self.root)

    def _check_outside_hermes(self, path: Path) -> None:
        if any(path.is_relative_to(root) for root in self.protected_roots):
            raise DiagnosisError("Artifact store must be outside Hermes")

    def save(self, record: DiagnosisRecord) -> StoredDiagnosis:
        identity = json.dumps([record.attribution.runtime, record.attribution.workflow_identity])
        workflow = hashlib.sha256(identity.encode()).hexdigest()
        path = self.save_bytes(workflow, "diagnoses", record.model_dump_json().encode("utf-8"))
        return StoredDiagnosis(record=record, path=path)

    def save_bytes(self, workflow: str, kind: str, raw: bytes) -> Path:
        if kind not in {"diagnoses", "reports"} or len(workflow) != 64 or any(
            c not in "0123456789abcdef" for c in workflow
        ):
            raise DiagnosisError("Invalid artifact address")
        directory = self.root / workflow / kind
        resolved = directory.resolve()
        if not resolved.is_relative_to(self.root):
            raise DiagnosisError("Artifact directory resolves outside this store")
        self._check_outside_hermes(resolved)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / (hashlib.sha256(raw).hexdigest() + ".json")
        # Publish complete bytes with an exclusive link, never replace a version.
        fd, temporary = tempfile.mkstemp(dir=directory)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
                os.fchmod(stream.fileno(), 0o444)
            try:
                os.link(temporary, path)
            except FileExistsError:
                if path.read_bytes() != raw:
                    raise DiagnosisError("Existing artifact does not match its digest")
        finally:
            os.unlink(temporary)
        return path

    def load(self, path: Path) -> DiagnosisRecord | LegacyDiagnosisRecord:
        return RECORD_READER.validate_json(self.load_bytes(path))

    def load_bytes(self, path: Path) -> bytes:
        resolved = path.resolve()
        if not resolved.is_relative_to(self.root):
            raise DiagnosisError("Artifact is outside this store")
        raw = resolved.read_bytes()
        if resolved.stem != hashlib.sha256(raw).hexdigest():
            raise DiagnosisError("Artifact digest mismatch")
        return raw
