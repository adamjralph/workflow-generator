"""Ticket 29: retain exact identity inputs before any Gate execution."""
from pathlib import Path

import pytest

from agent_lab.gate_identity import GateIdentityError, RegisteredOperation
from agent_lab.gate_store import GateArtifactStore
from test_gate_identity import specimen


def test_freeze_and_rederive_spec_and_registered_operation_bytes(tmp_path):
    store = GateArtifactStore(tmp_path / "owner-store")
    frozen = store.freeze_inputs(specimen(), {"add": RegisteredOperation("add_int_v1", 1)})
    assert frozen.spec_digest and frozen.operations_digest
    assert store.verify_inputs(frozen) == (specimen(), {"add": RegisteredOperation("add_int_v1", 1)})
    assert store.freeze_inputs(specimen(), {"add": RegisteredOperation("add_int_v1", 1)}) == frozen
    assert frozen.directory.is_relative_to(store.root)


@pytest.mark.parametrize("name", ["spec.json", "operations.json"])
def test_changed_artifact_bytes_fail_closed(tmp_path, name):
    store = GateArtifactStore(tmp_path / "owner-store")
    frozen = store.freeze_inputs(specimen(), {"add": RegisteredOperation("add_int_v1", 1)})
    path = frozen.directory / name
    path.chmod(0o600)
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(GateIdentityError):
        store.verify_inputs(frozen)


def test_caller_store_inside_source_is_refused():
    with pytest.raises(GateIdentityError):
        GateArtifactStore(Path(__file__).resolve().parents[1] / "unwanted")
