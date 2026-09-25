"""Local CLI authority is OS-account trust, not a supplied approver label."""
import importlib.util
import hashlib
import json
import os
import subprocess
import sys

import pytest

from agent_lab import gate_runtime as gate
from agent_lab.gate_identity import RegisteredOperation
from agent_lab.gate_identity import _canonical
from test_gate_identity import specimen


def cli(run, decision, **changes):
    cp = run.result.checkpoint
    values = {"run-id": cp.run_id, "gate": cp.gate, "pause": cp.pause,
              "spec": cp.spec_digest, "bundle": cp.bundle_digest}
    values.update(changes)
    args = [sys.executable, "-m", "agent_lab.gate_cli", "--store", str(run.version.directory.parent)]
    for key, value in values.items():
        args.extend(["--" + key, value])
    return subprocess.run(args + [decision], capture_output=True, text=True, timeout=30)


@pytest.mark.parametrize("driver", ["reference", "graph"])
@pytest.mark.parametrize("decision,terminal,value,used", [("approve", "DONE", 2, 3), ("reject", "REJECTED", 1, 2)])
def test_owner_cli_rederives_and_records_exact_pause(tmp_path, driver, decision, terminal, value, used):
    assert importlib.util.find_spec("agent_lab.gate_cli") is not None, "Local CLI seam missing"
    version = gate.emit_gate(specimen(), {"add": RegisteredOperation("add_int_v1", 1)}, store=tmp_path / "store")
    with gate.start_gate(version, run_id="operator", driver=driver) as run:
        result = cli(run, decision)
        assert result.returncode == 0, result.stderr
        record = json.loads(result.stdout)
        assert record["uid"] == os.getuid()
        assert record["checkpoint"] == run.result.checkpoint.model_dump(mode="json")
        assert record["authority"] == "local-os-account"
        assert record["recorded_ns"] > 0
        assert (run.directory / "decision.json").stat().st_mode & 0o077 == 0
        assert json.loads((run.directory / "decision.json").read_bytes())["record"] == record
        duplicate = cli(run, decision)
        assert duplicate.returncode == 0
        assert json.loads(duplicate.stdout) == record
        end = run.continue_gate()
        assert (end.terminal, end.value, end.used) == (terminal, value, used)
        assert cli(run, decision).returncode != 0


@pytest.mark.parametrize("corruption", ["event", "head", "gate", "budget", "event_bool", "event_float", "claim_bool",
                                        "version_bool", "version_float", "sequence_float", "extra_envelope",
                                        "metadata_version_bool", "attestation_extra", "completed_extra",
                                        "erased_origins", "deleted_module", "missing_proof", "forged_proof"])
def test_operator_refuses_malformed_committed_pause_before_recording(tmp_path, corruption):
    version = gate.emit_gate(specimen(), {"add": RegisteredOperation("add_int_v1", 1)}, store=tmp_path / "store")
    with gate.start_gate(version, run_id="operator", mode="operator") as run:
        path = run.directory / "00000003.json"
        row = json.loads(path.read_bytes())
        if corruption == "event":
            row["data"]["event"]["value"] = 99
        elif corruption == "event_bool":
            row["data"]["event"]["value"] = True
        elif corruption == "event_float":
            row["data"]["event"]["value"] = 1.0
        elif corruption == "claim_bool":
            path = run.directory / "00000002.json"
            row = json.loads(path.read_bytes())
            row["data"]["value_before"] = True
        elif corruption == "head":
            row["data"]["checkpoint"]["completed_head"] = "a" * 64
        elif corruption == "gate":
            row["data"]["checkpoint"]["gate"] = "nonexistent-gate"
        elif corruption == "version_bool":
            row["version"] = True
        elif corruption == "version_float":
            row["version"] = 1.0
        elif corruption == "sequence_float":
            row["sequence"] = 3.0
        elif corruption == "extra_envelope":
            row["unused"] = "altered"
        elif corruption == "attestation_extra":
            row["data"]["attestation"]["unused"] = "altered"
        elif corruption == "completed_extra":
            row["data"]["unused"] = "altered"
        elif corruption == "erased_origins":
            row["data"]["attestation"]["modules"] = {}
            row["data"]["attestation"]["native"] = {}
        elif corruption == "deleted_module":
            modules = row["data"]["attestation"]["modules"]
            del modules[next(iter(modules))]
        elif corruption == "missing_proof":
            del row["data"]["pause_proof"]
        elif corruption == "forged_proof":
            row["data"]["pause_proof"] = "0" * 64
        elif corruption == "metadata_version_bool":
            path = run.directory / "run.json"
            row = json.loads(path.read_bytes())
            row["version"] = True
        else:
            row["data"]["checkpoint"]["remaining"] = 999
        path.chmod(0o600)
        path.write_bytes(_canonical(row))
        if corruption == "claim_bool":
            pending = run.directory / "00000003.json"
            pending_row = json.loads(pending.read_bytes())
            pending_row["previous"] = hashlib.sha256(_canonical(row)).hexdigest()
            pending_row["data"]["checkpoint"]["prior_head"] = pending_row["previous"]
            pending.chmod(0o600)
            pending.write_bytes(_canonical(pending_row))
        result = cli(run, "approve", gate="nonexistent-gate") if corruption == "gate" else cli(run, "approve")
        assert result.returncode != 0
        assert not (run.directory / "decision.json").exists()
