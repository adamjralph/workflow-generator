"""Ticket 29: exact private spec and closed registered-operation admission."""
import json

import pytest

from agent_lab.gate_identity import (GateIdentityError, RegisteredOperation,
                                     freeze_spec, read_spec, freeze_operations)
from agent_lab.spec import GateNode, Route, TransformNode, WorkflowSpec


def specimen(budget=3):
    return WorkflowSpec(
        entry="before", budget=budget,
        nodes=(TransformNode(id="before", operation="add"), GateNode(id="review"),
               TransformNode(id="after", operation="add")),
        edges=(Route(source="before", outcome="done", target="review"),
               Route(source="review", outcome="approved", target="after"),
               Route(source="review", outcome="rejected", target="REJECTED"),
               Route(source="review", outcome="pending", target="PENDING"),
               Route(source="review", outcome="invalid", target="FAILED_VALIDATION"),
               Route(source="after", outcome="done", target="DONE")),
        terminals=("DONE", "REJECTED", "PENDING", "FAILED_VALIDATION", "FAILED_BUDGET"),
    )


def test_spec_bytes_roundtrip_and_budget_changes_identity():
    raw, digest = freeze_spec(specimen())
    assert read_spec(raw) == specimen()
    assert freeze_spec(read_spec(raw)) == (raw, digest)
    assert freeze_spec(specimen(budget=2))[1] != digest


@pytest.mark.parametrize("mutation", [
    lambda row: row.update(version=2),
    lambda row: row.update(extra="unrecognized"),
    lambda row: row["spec"].update(budget=0),
    lambda row: row["spec"]["edges"].reverse(),
])
def test_unknown_invalid_or_changed_spec_bytes_cannot_be_reused(mutation):
    raw, digest = freeze_spec(specimen())
    row = json.loads(raw)
    mutation(row)
    altered = json.dumps(row, sort_keys=True, separators=(",", ":")).encode()
    with pytest.raises(GateIdentityError):
        read_spec(altered, expected_digest=digest)


def test_noncanonical_spec_bytes_are_rejected():
    raw, _ = freeze_spec(specimen())
    with pytest.raises(GateIdentityError, match="canonical"):
        read_spec(json.dumps(json.loads(raw), indent=2).encode())


def test_closed_operation_records_reject_callables_and_unknown_configuration():
    raw, digest = freeze_operations({"add": RegisteredOperation("add_int_v1", delta=1)})
    assert json.loads(raw)["operations"] == {"add": {"opcode": "add_int_v1", "delta": 1}}
    assert len(digest) == 64
    with pytest.raises(GateIdentityError):
        freeze_operations({"add": lambda state: state})
    with pytest.raises(GateIdentityError):
        freeze_operations({"add": {"opcode": "add_int_v1", "delta": 1, "dynamic": "x"}})
    with pytest.raises(GateIdentityError):
        freeze_operations({"add": RegisteredOperation("add_int_v1", delta=True)})
