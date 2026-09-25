"""Ticket 29: real retained workers, independently expected public outcomes."""
import hashlib
import importlib.util
import json

import pytest

from agent_lab.gate_identity import RegisteredOperation
from test_gate_identity import specimen


@pytest.mark.parametrize("driver", ["reference", "graph"])
def test_registered_bundle_pauses_with_retained_executable_closure(tmp_path, driver):
    assert importlib.util.find_spec("agent_lab.gate_runtime") is not None, "Gate runtime public seam is missing"
    from agent_lab import gate_runtime
    from agent_lab.gate_bundle import verify_bundle

    version = gate_runtime.emit_gate(
        specimen(), {"add": RegisteredOperation("add_int_v1", 1)}, store=tmp_path / "store",
    )
    with gate_runtime.start_gate(version, run_id="pending", driver=driver, mode="fixture") as run:
        result = run.result
        assert (result.terminal, result.value, result.used, result.remaining) == ("PENDING", 1, 2, 1)
        assert [(e.node, e.outcome, e.used) for e in result.events] == [
            ("before", "done", 1), ("review", "pending", 2),
        ]
        assert result.checkpoint is not None
        assert result.checkpoint.bundle_digest == version.bundle_digest
        assert result.checkpoint.spec_digest == version.spec_digest
        manifest, files = verify_bundle(version)
        assert not any("tkinter" in path for path in files)
        attestation = run.attestation
        assert attestation["retained_runtime"] is True
        assert attestation["unverified_origins"] == []
        assert attestation["modules"]
        assert attestation["native"]
        assert "/runtime-python" in attestation["native"]
        assert any("pydantic_graph" in path for path in attestation["modules"])
        for section in ("modules", "native"):
            for path, digest in attestation[section].items():
                assert digest == hashlib.sha256(files[path]).hexdigest()
        rows = [json.loads(p.read_bytes()) for p in sorted(run.directory.glob("[0-9]*.json"))]
        assert [r["kind"] for r in rows] == ["claim", "completed", "claim", "completed"]
        assert rows[-1]["data"]["checkpoint"]["used"] == 2


@pytest.mark.parametrize("driver", ["reference", "graph"])
@pytest.mark.parametrize("decision,terminal,value,used", [("approved", "DONE", 2, 3), ("rejected", "REJECTED", 1, 2)])
def test_one_scoped_fixture_decision_continues_once(tmp_path, driver, decision, terminal, value, used):
    from agent_lab import gate_runtime as gate
    version = gate.emit_gate(specimen(), {"add": RegisteredOperation("add_int_v1", 1)}, store=tmp_path / "store")
    with gate.start_gate(version, run_id="fixture", driver=driver, mode="fixture") as run:
        assert hasattr(run, "submit_fixture"), "Scoped decision seam is missing"
        pause = run.result.checkpoint
        run.submit_fixture(pause, decision)
        assert run.result.terminal == "PENDING"
        result = run.continue_gate()
        assert (result.terminal, result.value, result.used, result.remaining) == (terminal, value, used, 3-used)
        events = [(e.node, e.outcome, e.used) for e in result.events]
        expected = [("before", "done", 1), ("review", "pending", 2), ("review", decision, 2)]
        if decision == "approved":
            expected.append(("after", "done", 3))
        assert events == expected
        before = {p.name: p.read_bytes() for p in run.directory.glob("*.json")}
        assert run.continue_gate() == result
        assert {p.name: p.read_bytes() for p in run.directory.glob("*.json")} == before
