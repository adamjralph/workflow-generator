"""Fail closed before successors; no arbitrary code or remote authority."""
from dataclasses import replace
import json
import os

import pytest

from agent_lab import gate_runtime as gate
from agent_lab.gate_bundle import verify_bundle
from agent_lab.gate_identity import GateIdentityError, RegisteredOperation
from agent_lab.gate_identity import _canonical
from test_gate_identity import specimen
from test_gate_operator import cli


def emit(tmp_path):
    return gate.emit_gate(specimen(), {"add": RegisteredOperation("add_int_v1", 1)}, store=tmp_path / "store")


def journal(run):
    return [json.loads(p.read_bytes()) for p in sorted(run.directory.glob("[0-9]*.json")) if p.is_file()]


def assert_no_successor(run):
    assert not any(row.get("data", {}).get("node") == "after" or row.get("data", {}).get("event", {}).get("node") == "after"
                   for row in journal(run))


def test_reemission_is_byte_reproducible(tmp_path):
    assert emit(tmp_path) == emit(tmp_path)


@pytest.mark.parametrize("driver", ["reference", "graph"])
@pytest.mark.parametrize("field", ["run_id", "gate", "pause", "spec_digest", "bundle_digest", "value", "used"])
def test_wrong_fixture_scope_is_refused_before_successor(tmp_path, driver, field):
    with gate.start_gate(emit(tmp_path), run_id="scope", driver=driver, mode="fixture") as run:
        cp = run.result.checkpoint
        wrong = cp.model_copy(update={field: 99 if field in {"value", "used"} else "wrong"})
        with pytest.raises(GateIdentityError):
            run.submit_fixture(wrong, "approved")
        assert_no_successor(run)


@pytest.mark.parametrize("driver", ["reference", "graph"])
@pytest.mark.parametrize("mode", ["fixture", "operator"])
def test_missing_decision_never_resumes(tmp_path, driver, mode):
    with gate.start_gate(emit(tmp_path), run_id="missing", driver=driver, mode=mode) as run:
        with pytest.raises(GateIdentityError):
            run.continue_gate()
        assert_no_successor(run)


@pytest.mark.parametrize("attack", ["fixture", "forged", "conflict", "wrong-pause", "business"])
def test_operator_authority_cannot_be_substituted(tmp_path, attack):
    with gate.start_gate(emit(tmp_path), run_id="operator") as run:
        if attack == "fixture":
            with pytest.raises(GateIdentityError):
                run.submit_fixture(run.result.checkpoint, "approved")
        elif attack == "wrong-pause":
            assert cli(run, "approve", pause="wrong").returncode != 0
        elif attack == "conflict":
            assert cli(run, "reject").returncode == 0
            assert cli(run, "approve").returncode != 0
            assert run.continue_gate().terminal == "REJECTED"
        elif attack == "forged":
            cp = run.result.checkpoint
            record = {"version": 1, "checkpoint": cp.model_dump(mode="json"),
                      "decision": "approved", "authority": "local-os-account",
                      "uid": os.getuid(), "recorded_ns": 1}
            path = run.directory / "decision.json"
            path.write_bytes(_canonical({"record": record, "mac": "0" * 64}))
            path.chmod(0o400)
            with pytest.raises(GateIdentityError, match="Forged operator decision"):
                run.continue_gate()
        else:
            (run.directory / "decision.json").write_text(json.dumps({"approved": True, "approver": "human"}))
            if attack == "business":
                (run.directory / "draft-approval.json").write_text('{"approved":true}')
            with pytest.raises(GateIdentityError):
                run.continue_gate()
        assert_no_successor(run)


@pytest.mark.parametrize("artifact", ["spec", "worker", "native", "dependency", "operations", "manifest"])
def test_retained_artifact_mutation_cannot_inherit_decision(tmp_path, artifact):
    version = emit(tmp_path)
    manifest, _ = verify_bundle(version)
    with gate.start_gate(version, run_id="mutated", mode="fixture") as run:
        run.submit_fixture(run.result.checkpoint, "approved")
        names = {"spec": "/app/spec.json", "worker": "/app/gate_worker.py", "native": "/runtime-python",
                 "operations": "/app/operations.json",
                 "dependency": next(n for n in manifest["files"] if "pydantic_graph" in n and n.endswith(".py"))}
        path = version.directory / "manifest.json" if artifact == "manifest" else (
            version.directory / "blobs" / manifest["files"][names[artifact]]["sha256"])
        path.chmod(0o600)
        path.write_bytes(path.read_bytes() + b"altered")
        with pytest.raises(GateIdentityError):
            run.continue_gate()
        assert_no_successor(run)


@pytest.mark.parametrize("attack", ["checkpoint", "event", "missing", "extra"])
def test_corrupt_journal_refuses_continuation(tmp_path, attack):
    with gate.start_gate(emit(tmp_path), run_id="evidence", mode="fixture") as run:
        run.submit_fixture(run.result.checkpoint, "approved")
        path = run.directory / ("00000003.json" if attack == "checkpoint" else "00000001.json")
        if attack == "missing":
            path.unlink()
        elif attack == "extra":
            (run.directory / "00000099.json").write_text('{}')
        else:
            row = json.loads(path.read_bytes())
            row["data"]["checkpoint" if attack == "checkpoint" else "event"]["value"] = 99
            path.chmod(0o600)
            path.write_text(json.dumps(row))
        with pytest.raises(GateIdentityError):
            run.continue_gate()
        assert_no_successor(run)


def test_audit_write_failure_blocks_successor(tmp_path):
    with gate.start_gate(emit(tmp_path), run_id="audit", mode="fixture") as run:
        run.submit_fixture(run.result.checkpoint, "approved")
        run.directory.chmod(0o500)
        try:
            with pytest.raises(GateIdentityError):
                run.continue_gate()
        finally:
            run.directory.chmod(0o700)
        assert_no_successor(run)


def test_noncanonical_bool_checkpoint_cannot_authorize(tmp_path):
    with gate.start_gate(emit(tmp_path), run_id="bool-scope", mode="fixture") as run:
        cp = run.result.checkpoint.model_copy(update={"value": True})
        with pytest.raises(GateIdentityError):
            run.submit_fixture(cp, "approved")
        assert_no_successor(run)


def test_symlinked_run_parent_is_rejected(tmp_path):
    version = emit(tmp_path)
    other = tmp_path / "other"
    other.mkdir(mode=0o700)
    (version.directory.parent / "runs").symlink_to(other, target_is_directory=True)
    with pytest.raises(GateIdentityError, match="directory|symlink"):
        with gate.start_gate(version, run_id="escape", mode="fixture"):
            pass
    assert list(other.iterdir()) == []


@pytest.mark.parametrize("attack", ["callable", "mutable", "dynamic", "extra", "config"])
def test_unregistered_behavior_is_refused_before_emission(tmp_path, attack):
    options = {
        "callable": {"add": lambda value: value},
        "mutable": {"add": {"opcode": "add_int_v1", "delta": 1}},
        "dynamic": {"add": RegisteredOperation("import:os", 1)},
        "extra": {"add": RegisteredOperation("add_int_v1", 1), "unused": RegisteredOperation("add_int_v1", 2)},
        "config": {"add": RegisteredOperation("add_int_v1", True)},
    }
    with pytest.raises(GateIdentityError):
        gate.emit_gate(specimen(), options[attack], store=tmp_path / "store")
    assert not (tmp_path / "store" / "runs").exists()


def test_conflicting_and_late_fixture_submissions_refused(tmp_path):
    version = emit(tmp_path)
    with gate.start_gate(version, run_id="conflict", mode="fixture") as run:
        run.submit_fixture(run.result.checkpoint, "rejected")
        before = journal(run)
        run.submit_fixture(run.result.checkpoint, "rejected")
        assert journal(run) == before
        with pytest.raises(GateIdentityError):
            run.submit_fixture(run.result.checkpoint, "approved")
        assert_no_successor(run)
    with gate.start_gate(version, run_id="late", mode="fixture") as run:
        run.submit_fixture(run.result.checkpoint, "rejected")
        run.continue_gate()
        with pytest.raises(GateIdentityError):
            run.submit_fixture(run.result.checkpoint, "rejected")
        assert_no_successor(run)


def test_retained_worker_does_not_use_ambient_emitter_or_pythonpath(tmp_path, monkeypatch):
    from agent_lab import gate_bundle
    version = emit(tmp_path)
    monkeypatch.setenv("PYTHONPATH", str(tmp_path / "untrusted"))
    monkeypatch.setenv("PYTHONHOME", str(tmp_path / "untrusted"))
    monkeypatch.setattr(gate_bundle.sys, "executable", "/missing-python")
    with gate.start_gate(version, run_id="retained", mode="fixture") as run:
        run.submit_fixture(run.result.checkpoint, "approved")
        assert run.continue_gate().value == 2
