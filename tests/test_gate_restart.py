"""Ticket 30: fresh-process committed-pause recovery through the public Gate seam."""
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import threading

import pytest

from agent_lab.gate_identity import GateIdentityError, RegisteredOperation
from agent_lab.gate_runtime import emit_gate, recover_gate, start_gate
from agent_lab.gate_cli import main as decision_cli
from agent_lab.spec import Route, TransformNode
from test_gate_identity import specimen


def _pause(tmp_path: Path, driver: str = "graph"):
    store = tmp_path / "store"
    version = emit_gate(specimen(), {"add": RegisteredOperation("add_int_v1", 1)}, store=store)
    with start_gate(version, run_id="restart", driver=driver) as run:
        checkpoint = run.result.checkpoint
        assert checkpoint is not None
        assert (run.result.value, run.result.used, run.result.remaining) == (1, 2, 1)
    return store, version, checkpoint


def _decide(store, checkpoint, action="approve"):
    return decision_cli(["--store", str(store), "--run-id", "restart", "--gate", checkpoint.gate,
                         "--pause", checkpoint.pause, "--spec", checkpoint.spec_digest,
                         "--bundle", checkpoint.bundle_digest, action])


@pytest.mark.parametrize("driver", ["reference", "graph"])
@pytest.mark.parametrize("prefix_length", [2, 3])
def test_admitted_longer_prefix_restarts_without_recharging_gate(tmp_path, driver, prefix_length):
    base = specimen()
    extra = tuple(TransformNode(id=f"before_{i}", operation="add") for i in range(1, prefix_length))
    nodes = (base.nodes[0], *extra, *base.nodes[1:])
    edges = (Route(source="before", outcome="done", target=extra[0].id),
             *(Route(source=left.id, outcome="done", target=right.id)
               for left, right in zip(extra, extra[1:])),
             Route(source=extra[-1].id, outcome="done", target="review"),
             *base.edges[1:])
    spec = base.model_copy(update={"nodes": nodes, "edges": edges, "budget": prefix_length + 2})
    store = tmp_path / "store"
    version = emit_gate(spec, {"add": RegisteredOperation("add_int_v1", 1)}, store=store)
    with start_gate(version, run_id="long-prefix", driver=driver) as run:
        checkpoint = run.result.checkpoint
        assert checkpoint is not None
        assert (checkpoint.value, checkpoint.used, checkpoint.remaining) == (prefix_length, prefix_length + 1, 1)
    directory = store / "runs" / "long-prefix"
    assert len(list(directory.glob("[0-9]*.json"))) == 2 * (prefix_length + 1)
    args = ["--store", str(store), "--run-id", "long-prefix", "--gate", checkpoint.gate,
            "--pause", checkpoint.pause, "--spec", checkpoint.spec_digest,
            "--bundle", checkpoint.bundle_digest, "approve"]
    assert decision_cli(args) == 0
    with recover_gate(store, run_id="long-prefix") as run:
        result = run.result
        assert (result.terminal, result.value, result.used, result.remaining) == (
            "DONE", prefix_length + 1, prefix_length + 2, 0)
        assert [(e.node, e.outcome) for e in result.events] == [
            ("before", "done"), *((node.id, "done") for node in extra),
            ("review", "pending"), ("review", "approved"), ("after", "done")]


@pytest.mark.parametrize("driver", ["reference", "graph"])
@pytest.mark.parametrize("action,terminal,value,used", [("approve", "DONE", 2, 3), ("reject", "REJECTED", 1, 2)])
def test_fresh_process_reconstructs_and_continues_once(tmp_path, driver, action, terminal, value, used):
    store, _, checkpoint = _pause(tmp_path, driver)
    assert _decide(store, checkpoint, action) == 0
    script = ("import json,sys; from pathlib import Path; from agent_lab.gate_runtime import recover_gate; "
              "\nwith recover_gate(Path(sys.argv[1]), run_id='restart') as run:\n"
              " print(run.result.model_dump_json())")
    result = subprocess.run([sys.executable, "-c", script, str(store)], text=True, capture_output=True, check=True)
    response = json.loads(result.stdout.strip())
    assert (response["terminal"], response["value"], response["used"], response["remaining"]) == (
        terminal, value, used, 3-used)
    events = [(e["node"], e["outcome"], e["used"]) for e in response["events"]]
    expected = [("before", "done", 1), ("review", "pending", 2),
                ("review", "approved" if action == "approve" else "rejected", 2)]
    if action == "approve":
        expected.append(("after", "done", 3))
    assert events == expected
    directory = store / "runs" / "restart"
    before = {p.name: p.read_bytes() for p in directory.iterdir() if p.is_file()}
    with pytest.raises(GateIdentityError):
        recover_gate(store, run_id="restart")
    assert {p.name: p.read_bytes() for p in directory.iterdir() if p.is_file()} == before


def test_recovery_requires_exclusive_claim(tmp_path):
    store, _, checkpoint = _pause(tmp_path)
    assert _decide(store, checkpoint) == 0
    with recover_gate(store, run_id="restart") as run:
        with pytest.raises(GateIdentityError, match="claim"):
            recover_gate(store, run_id="restart")
        contender = subprocess.run([sys.executable, "-c",
                                    "from pathlib import Path; from agent_lab.gate_runtime import recover_gate; "
                                    "import sys; recover_gate(Path(sys.argv[1]), run_id='restart')",
                                    str(store)], text=True, capture_output=True)
        assert contender.returncode != 0
        assert "exclusive continuation claim" in contender.stderr
        assert run.result.terminal == "DONE"


@pytest.mark.parametrize("corruption", ["missing", "truncated", "extra-claim", "wrong-decision", "pending-file", "bundle", "missing-lock", "wrong-run"])
def test_corrupt_or_ambiguous_pause_refuses_before_downstream(tmp_path, corruption):
    store, version, checkpoint = _pause(tmp_path)
    assert _decide(store, checkpoint) == 0
    directory = store / "runs" / "restart"
    if corruption == "missing":
        (directory / "00000003.json").unlink()
    elif corruption == "truncated":
        (directory / "00000003.json").unlink()
        path = directory / "00000003.json"
        path.write_bytes(b"{")
        path.chmod(0o600)
    elif corruption == "extra-claim":
        path = directory / "00000004.json"
        path.write_bytes(b"{")
        path.chmod(0o600)
    elif corruption == "wrong-decision":
        (directory / "decision.json").unlink()
        path = directory / "decision.json"
        path.write_bytes(b"{}")
        path.chmod(0o600)
    elif corruption == "pending-file":
        path = directory / ".pending-00000004"
        path.write_bytes(b"{")
        path.chmod(0o600)
    elif corruption == "missing-lock":
        (directory / "claim.lock").unlink()
    elif corruption == "wrong-run":
        (directory / "run.json").unlink()
        path = directory / "run.json"
        path.write_bytes(b'{"bundle_digest":"wrong","driver":"graph","mode":"operator","run_id":"restart","spec_digest":"wrong","version":1}')
        path.chmod(0o600)
    else:
        (version.directory / "manifest.json").unlink()
        path = version.directory / "manifest.json"
        path.write_bytes(b"{}")
        path.chmod(0o600)
    with pytest.raises(GateIdentityError) as refusal:
        recover_gate(store, run_id="restart")
    expected_reason = {"truncated": "Malformed canonical identity", "bundle": "Bundle identity mismatch",
                       "pending-file": "Unexpected or incomplete run publication"}
    if corruption in expected_reason:
        assert expected_reason[corruption] in str(refusal.value)
    assert not (directory / "00000004.json").exists() or corruption == "extra-claim"


def test_no_decision_is_not_recovery_authority(tmp_path):
    store, _, _ = _pause(tmp_path)
    with pytest.raises(GateIdentityError):
        recover_gate(store, run_id="restart")


def test_decision_commit_failure_never_unlocks_downstream(tmp_path, monkeypatch):
    from agent_lab.gate_store import GateArtifactStore
    store, _, checkpoint = _pause(tmp_path)
    original = GateArtifactStore._publish

    def fail_decision(path, raw):
        if path.name == "decision.json":
            raise OSError("injected decision publication failure")
        return original(path, raw)

    monkeypatch.setattr(GateArtifactStore, "_publish", fail_decision)
    assert _decide(store, checkpoint) == 1
    with pytest.raises(GateIdentityError):
        recover_gate(store, run_id="restart")
    assert not (store / "runs" / "restart" / "00000004.json").exists()


def test_decision_directory_sync_failure_leaves_ambiguity_marker(tmp_path, monkeypatch):
    from agent_lab import gate_store
    store, _, checkpoint = _pause(tmp_path)
    directory = store / "runs" / "restart"
    real_fsync = gate_store.os.fsync

    def fail_directory_sync(fd):
        if stat.S_ISDIR(os.fstat(fd).st_mode):
            raise OSError("injected directory fsync failure after decision link")
        return real_fsync(fd)

    monkeypatch.setattr(gate_store.os, "fsync", fail_directory_sync)
    assert _decide(store, checkpoint) == 1
    assert (directory / "decision.json").exists()
    assert list(directory.glob(".pending-*")), "linked but unsynced decision needs a refusal marker"
    with pytest.raises(GateIdentityError, match="incomplete|Unexpected"):
        recover_gate(store, run_id="restart")
    assert not (directory / "00000004.json").exists()


@pytest.mark.parametrize("driver", ["reference", "graph"])
def test_open_worker_refuses_failed_decision_publication(tmp_path, monkeypatch, driver):
    from agent_lab import gate_store
    store = tmp_path / "store"
    version = emit_gate(specimen(), {"add": RegisteredOperation("add_int_v1", 1)}, store=store)
    with start_gate(version, run_id="restart", driver=driver) as run:
        checkpoint = run.result.checkpoint
        assert checkpoint is not None
        real_fsync = gate_store.os.fsync

        def fail_directory_sync(fd):
            if stat.S_ISDIR(os.fstat(fd).st_mode):
                raise OSError("injected decision fsync failure")
            return real_fsync(fd)

        monkeypatch.setattr(gate_store.os, "fsync", fail_directory_sync)
        assert _decide(store, checkpoint) == 1
        monkeypatch.setattr(gate_store.os, "fsync", real_fsync)
        with pytest.raises(GateIdentityError):
            run.continue_gate()
        directory = store / "runs" / "restart"
        assert not (directory / "00000004.json").exists()


def test_recovery_refuses_decision_failed_after_initial_inspection(tmp_path, monkeypatch):
    from agent_lab import gate_cli, gate_store
    store, _, checkpoint = _pause(tmp_path)
    inspected = threading.Event()
    released = threading.Event()
    original_inspect = gate_cli.inspect_pause
    real_fsync = gate_store.os.fsync
    errors = []

    def pause_recovery_inspection(root, run_id):
        result = original_inspect(root, run_id)
        if threading.current_thread().name == "recovery":
            inspected.set()
            if not released.wait(30):
                raise RuntimeError("test recovery inspection barrier timed out")
        return result

    def fail_directory_sync(fd):
        if stat.S_ISDIR(os.fstat(fd).st_mode):
            raise OSError("injected decision fsync failure")
        return real_fsync(fd)

    def recover_in_thread():
        try:
            with recover_gate(store, run_id="restart") as run:
                errors.append(("continued", run.result.terminal))
        except GateIdentityError:
            errors.append(("refused",))

    monkeypatch.setattr(gate_cli, "inspect_pause", pause_recovery_inspection)
    thread = threading.Thread(target=recover_in_thread, name="recovery")
    thread.start()
    try:
        assert inspected.wait(30)
        monkeypatch.setattr(gate_store.os, "fsync", fail_directory_sync)
        assert _decide(store, checkpoint) == 1
        monkeypatch.setattr(gate_store.os, "fsync", real_fsync)
    finally:
        released.set()
        thread.join(timeout=60)
        monkeypatch.setattr(gate_store.os, "fsync", real_fsync)
    assert not thread.is_alive()
    assert errors == [("refused",)]
    assert not (store / "runs" / "restart" / "00000004.json").exists()


def test_restart_checker_compares_independent_drivers_and_authored_events(tmp_path):
    from agent_lab.gate_conformance import GateCase, GateExpected, check_gate_restart
    spec = specimen()
    ops = {"add": RegisteredOperation("add_int_v1", 1)}
    version = emit_gate(spec, ops, store=tmp_path / "store")
    prefix = (("before", "done", "review", 1, 1), ("review", "pending", "PENDING", 2, 1))
    pending = GateExpected(terminal="PENDING", value=1, used=2, remaining=1, events=prefix)
    expected = GateExpected(terminal="DONE", value=2, used=3, remaining=0,
                            events=prefix + (("review", "approved", "after", 2, 1),
                                             ("after", "done", "DONE", 3, 2)))
    case = GateCase(name="restart", reference_decision="approved", graph_decision="approved",
                    pending=pending, expected=expected)
    report = check_gate_restart(spec, ops, version, (case,))
    assert report.passed, report.findings
    assert len(report.results) == 2
    wrong = case.model_copy(update={"name": "wrong", "expected": expected.model_copy(update={"value": 99})})
    assert not check_gate_restart(spec, ops, version, (wrong,)).passed
    split = case.model_copy(update={"name": "split", "graph_decision": "rejected"})
    assert not check_gate_restart(spec, ops, version, (split,)).passed


@pytest.mark.parametrize("sequence", [0, 1, 2, 3])
@pytest.mark.parametrize("boundary", ["before_file", "after_file", "after_link", "after_dirsync", "after_unlink"])
def test_initial_publication_crash_never_claims_a_pause(tmp_path, sequence, boundary):
    store = tmp_path / "store"
    version = emit_gate(specimen(), {"add": RegisteredOperation("add_int_v1", 1)}, store=store)
    with pytest.raises(GateIdentityError):
        start_gate(version, run_id="restart", crash_at=(sequence, boundary))
    with pytest.raises(GateIdentityError):
        recover_gate(store, run_id="restart")


def test_committed_pause_survives_lost_acknowledgement(tmp_path):
    store = tmp_path / "store"
    version = emit_gate(specimen(), {"add": RegisteredOperation("add_int_v1", 1)}, store=store)
    with pytest.raises(GateIdentityError):
        start_gate(version, run_id="restart", crash_at=(3, "after_unlink"))
    from agent_lab.gate_cli import inspect_pause
    _, checkpoint = inspect_pause(store, "restart")
    assert (checkpoint.used, checkpoint.remaining, checkpoint.value) == (2, 1, 1)
    assert _decide(store, checkpoint) == 0
    with recover_gate(store, run_id="restart") as run:
        assert (run.result.terminal, run.result.value, run.result.used) == ("DONE", 2, 3)


@pytest.mark.parametrize("sequence", [4, 5, 6, 7])
@pytest.mark.parametrize("boundary", ["before_file", "after_file", "after_link", "after_dirsync", "after_unlink"])
def test_recovery_crash_requires_unambiguous_committed_pause(tmp_path, sequence, boundary):
    store, _, checkpoint = _pause(tmp_path)
    assert _decide(store, checkpoint) == 0
    with pytest.raises(GateIdentityError):
        recover_gate(store, run_id="restart", crash_at=(sequence, boundary))
    directory = store / "runs" / "restart"
    if (sequence, boundary) == (4, "before_file"):
        with recover_gate(store, run_id="restart") as run:
            assert run.result.terminal == "DONE"
    else:
        with pytest.raises(GateIdentityError):
            recover_gate(store, run_id="restart")
        assert not (directory / "00000007.json").exists() or sequence == 7
