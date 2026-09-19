"""Immutable diagnosis versions, addressed by the SHA-256 of their exact bytes."""
import hashlib
import json
import os
import tempfile
from pathlib import Path

from . import DiagnosisError, DiagnosisRecord, StoredDiagnosis


class DiagnosisStore:
    def __init__(self, root: Path, *, protected_roots: tuple[Path, ...] = ()):
        self.root = root.resolve()
        protected = (Path.home() / ".hermes", *protected_roots)
        if configured := os.environ.get("HERMES_HOME"):
            protected += (Path(configured),)
        if any(self.root.is_relative_to(path.resolve()) for path in protected):
            raise DiagnosisError("Artifact store must be outside Hermes")

    def save(self, record: DiagnosisRecord) -> StoredDiagnosis:
        identity = json.dumps([record.attribution.runtime, record.attribution.workflow_identity])
        workflow = hashlib.sha256(identity.encode()).hexdigest()
        directory = self.root / workflow / "diagnoses"
        if not directory.resolve().is_relative_to(self.root):
            raise DiagnosisError("Artifact directory resolves outside this store")
        directory.mkdir(parents=True, exist_ok=True)
        raw = record.model_dump_json().encode("utf-8")
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
        return StoredDiagnosis(record=record, path=path)

    def load(self, path: Path) -> DiagnosisRecord:
        resolved = path.resolve()
        if not resolved.is_relative_to(self.root):
            raise DiagnosisError("Artifact is outside this store")
        raw = resolved.read_bytes()
        if resolved.stem != hashlib.sha256(raw).hexdigest():
            raise DiagnosisError("Artifact digest mismatch")
        return DiagnosisRecord.model_validate_json(raw)
