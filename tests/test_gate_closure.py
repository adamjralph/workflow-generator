"""Attested dependency origins, immutable emission and audit ordering."""
import hashlib
import json
import os
from dataclasses import replace

import pytest

from agent_lab import gate_runtime as gate
from agent_lab.gate_bundle import verify_bundle
from agent_lab.gate_identity import GateIdentityError, _canonical
from test_gate_failures import emit, assert_no_successor, journal


@pytest.mark.parametrize("field,value", [("target", "arbitrary"), ("emitter", "v999"), ("unknown", True)])
def test_manifest_unknown_semantics_refused_even_if_rehashed(tmp_path, field, value):
    version = emit(tmp_path)
    manifest, _ = verify_bundle(version)
    manifest[field] = value
    raw = _canonical(manifest)
    digest = hashlib.sha256(b"workflow-generator/gate-bundle/v1\0" + raw).hexdigest()
    directory = version.directory.parent / digest
    directory.mkdir(mode=0o700)
    (directory / "blobs").mkdir(mode=0o700)
    for path in (version.directory / "blobs").iterdir():
        os.link(path, directory / "blobs" / path.name)
    (directory / "manifest.json").write_bytes(raw)
    (directory / "manifest.json").chmod(0o400)
    with pytest.raises(GateIdentityError, match="Invalid executable manifest"):
        verify_bundle(replace(version, directory=directory, bundle_digest=digest))


def test_reemission_rejects_symlinked_blob_directory_before_any_write(tmp_path):
    version = emit(tmp_path)
    blobs = version.directory / "blobs"
    blobs.rename(tmp_path / "original-blobs")
    outside = tmp_path / "outside"
    outside.mkdir(mode=0o700)
    blobs.symlink_to(outside, target_is_directory=True)
    with pytest.raises(GateIdentityError, match="bundle directory|symlink"):
        emit(tmp_path)
    assert list(outside.iterdir()) == []


@pytest.mark.parametrize("sequence,expected_kinds", [
    (5, ["claim", "completed", "claim", "completed", "decision"]),
    (6, ["claim", "completed", "claim", "completed", "decision", "resolved"]),
])
def test_failed_atomic_audit_publish_never_starts_successor(tmp_path, sequence, expected_kinds):
    with gate.start_gate(emit(tmp_path), run_id="write-failure", mode="fixture") as run:
        run.submit_fixture(run.result.checkpoint, "approved")
        # Real filesystem failure at the next exclusive temporary publication.
        (run.directory / f".pending-{sequence:08}").mkdir()
        with pytest.raises(GateIdentityError):
            run.continue_gate()
        assert [r["kind"] for r in journal(run)] == expected_kinds
        assert_no_successor(run)


def test_runtime_excludes_optional_imports_and_persists_origin_evidence(tmp_path):
    with gate.start_gate(emit(tmp_path), run_id="closure", mode="fixture") as run:
        assert run.attestation.get("excluded_imports") == ["_tkinter", "tkinter"], "Excluded import guard is missing"
        rows = journal(run)
        evidence = rows[-1]["data"]["attestation"]
        assert evidence == run.attestation
        assert evidence["modules"]["/app/gate_worker.py"]
        assert evidence["native"]["/runtime-python"]
        assert evidence["unverified_origins"] == []
        head = "0" * 64
        for event in run.result.events:
            head = hashlib.sha256(b"workflow-generator/gate-event/v1\0" + head.encode() +
                                  _canonical(event.model_dump(mode="json"))).hexdigest()
        assert getattr(run.result.checkpoint, "completed_head", None) == head
