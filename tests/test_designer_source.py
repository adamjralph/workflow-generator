"""Public controlled-source capture, execution and replay contract."""
import json
import os
from pathlib import Path

import pytest

from agent_lab.designer import Design
from agent_lab.designer.roles import RoleState, ReviewVerdict
from agent_lab.designer.source import ControlledSource
from agent_lab.generation import generate_graph
from agent_lab.reference import TransformResult

BRIEF = {"request_id": "local-1", "text": "Write the update.", "evidence_labels": ["note"]}
DESIGN = {"mode": "roles", "producer": "signal_generator", "output": "evidence_handoff", "consumer": "signal_guardian"}


def test_capture_previews_valid_brief_without_changing_source(tmp_path: Path) -> None:
    path = tmp_path / "operator-private.json"
    data = json.dumps(BRIEF).encode()
    path.write_bytes(data)
    path.chmod(0o444)
    source = ControlledSource(path, tmp_path / "evidence")
    captured = source.capture()
    assert captured["input"] == BRIEF
    assert captured["source"] == "Local writing brief"
    assert len(captured["snapshot"]) == 64
    assert str(path) not in json.dumps(captured)
    assert source.capture() == captured
    assert path.read_bytes() == data
    assert path.stat().st_mode & 0o777 == 0o444


def test_run_uses_captured_bytes_after_source_is_deleted(tmp_path: Path) -> None:
    path = tmp_path / "brief.json"
    path.write_text(json.dumps(BRIEF))
    source = ControlledSource(path, tmp_path / "evidence")
    captured = source.capture()
    path.unlink()
    result = source.run(DESIGN, captured["snapshot"])
    assert result["succeeded"] is True
    assert result["snapshot"] == captured["snapshot"]
    assert result["source"] == captured["source"]
    assert result["input"] == BRIEF
    assert result["output"] == {
        "state": {"brief": BRIEF, "handoff": BRIEF, "verdict": {
            "request_id": "local-1", "evidence_count": 1, "result": "evidence_present"}},
        "terminal": "COMPLETED", "used_steps": 2,
        "route": [["generator", "done", "guardian"], ["guardian", "done", "COMPLETED"]]}
    assert Path(result["evidence"]).is_file()


def test_check_replays_old_input_and_recapture_uses_changed_input(tmp_path: Path) -> None:
    path = tmp_path / "brief.json"
    path.write_text(json.dumps(BRIEF))
    source = ControlledSource(path, tmp_path / "evidence")
    captured = source.capture()
    changed = {**BRIEF, "evidence_labels": []}
    path.write_text(json.dumps(changed))
    report = source.check(DESIGN, captured["snapshot"])
    assert report["passed"] is True
    assert "succeeded" not in report
    assert report["cases"] == ["captured_input"]
    assert report["completed_cases"] == ["captured_input"]
    assert report["input"] == BRIEF
    assert report["snapshot"] == captured["snapshot"]
    assert report["outputs"][0]["state"]["verdict"] == {
        "request_id": "local-1", "evidence_count": 1, "result": "evidence_present"}
    evidence = report["evidence"][0]
    assert Path(evidence["reference_log"]).read_bytes() == Path(evidence["candidate_log"]).read_bytes()
    newer = source.capture()
    assert newer["snapshot"] != captured["snapshot"]
    for result in (source.run(DESIGN, newer["snapshot"])["output"],
                   source.check(DESIGN, newer["snapshot"])["outputs"][0]):
        assert result["state"] == {"brief": changed, "handoff": changed, "verdict": {
            "request_id": "local-1", "evidence_count": 0, "result": "evidence_missing"}}
    assert path.read_text() == json.dumps(changed)


@pytest.mark.parametrize("data", [
    b'{"request_id":"a","request_id":"b","text":"ok","evidence_labels":[]}',
    b'{"request_id":"a","text":"ok","evidence_labels":[]} ' + b' ' * 4096,
    b'{"request_id":"a","text":"ok","evidence_labels":[],"extra":1}',
    b'{"request_id":1,"text":"ok","evidence_labels":[]}',
    b'{"request_id":"a","text":" ","evidence_labels":[]}',
    b'{"request_id":"a","text":"ok","evidence_labels":["x","x"]}',
    b'{"request_id":"a","text":"ok","evidence_labels":["a","b","c","d"]}',
    b'{"request_id":"a","text":"ok","evidence_labels":"x"}',
    b'[]', b'{', b'\xff',
    '{"request_id":"a","text":"ok","evidence_labels":[]}'.encode("utf-16"),
])
def test_capture_rejects_invalid_input_without_evidence(tmp_path: Path, data: bytes) -> None:
    path = tmp_path / "brief.json"
    path.write_bytes(data)
    root = tmp_path / "evidence"
    with pytest.raises(ValueError):
        ControlledSource(path, root).capture()
    assert not root.exists()
    assert path.read_bytes() == data


@pytest.mark.parametrize("kind", ["directory", "fifo", "symlink", "missing"])
def test_capture_requires_regular_file(tmp_path: Path, kind: str) -> None:
    path = tmp_path / "brief.json"
    if kind == "directory":
        path.mkdir()
    elif kind == "fifo":
        os.mkfifo(path)
    elif kind == "symlink":
        real = tmp_path / "real.json"
        real.write_text(json.dumps(BRIEF))
        path.symlink_to(real)
    with pytest.raises((ValueError, OSError)):
        ControlledSource(path, tmp_path / "evidence").capture()


@pytest.mark.parametrize("operation", ["run", "check"])
@pytest.mark.parametrize("damage", ["missing", "changed", "malformed", "symlink"])
def test_bad_snapshot_fails_before_candidate(tmp_path: Path, operation: str, damage: str) -> None:
    path = tmp_path / "brief.json"
    path.write_text(json.dumps(BRIEF))
    root = tmp_path / "evidence"
    source = ControlledSource(path, root)
    captured = source.capture()
    stored = root / "snapshots" / (captured["snapshot"] + ".json")
    if damage == "missing":
        stored.unlink()
    elif damage == "changed":
        stored.write_text(json.dumps({**BRIEF, "text": "Changed"}))
    elif damage == "malformed":
        stored.write_bytes(b'{')
    else:
        stored.unlink()
        stored.symlink_to(path)
    def forbidden(design: object) -> object:
        pytest.fail("candidate must not be created for a bad snapshot")
    with pytest.raises((ValueError, OSError)):
        getattr(source, operation)(DESIGN, captured["snapshot"], candidate_factory=forbidden)
    assert path.read_text() == json.dumps(BRIEF)


@pytest.mark.parametrize("identity", ["../brief", "", "x" * 64, "A" * 64, None, 12])
def test_snapshot_identifier_is_not_a_path(tmp_path: Path, identity: object) -> None:
    source = ControlledSource(tmp_path / "brief.json", tmp_path / "evidence")
    for operation in (source.run, source.check):
        with pytest.raises(ValueError, match="snapshot"):
            operation(DESIGN, identity)  # type: ignore[arg-type]


@pytest.mark.parametrize("location", ["inside", "same", "below", "alias"])
def test_source_cannot_overlap_evidence_destination(tmp_path: Path, location: str) -> None:
    root = tmp_path / "evidence"
    root.mkdir()
    path = root / "brief.json" if location == "inside" else tmp_path / "brief.json"
    path.write_text(json.dumps(BRIEF))
    if location == "same":
        root = path
    elif location == "below":
        root = path / "nested"
    elif location == "alias":
        alias = tmp_path / "alias"
        alias.symlink_to(tmp_path, target_is_directory=True)
        root = alias
    with pytest.raises(ValueError, match="overlap"):
        ControlledSource(path, root).capture()
    assert path.read_text() == json.dumps(BRIEF)


def test_snapshots_cannot_escape_evidence_root(tmp_path: Path) -> None:
    path = tmp_path / "brief.json"
    path.write_text(json.dumps(BRIEF))
    root = tmp_path / "evidence"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "snapshots").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError):
        ControlledSource(path, root).capture()
    assert list(outside.iterdir()) == []


def test_recapture_never_hides_existing_snapshot_corruption(tmp_path: Path) -> None:
    path = tmp_path / "brief.json"
    path.write_text(json.dumps(BRIEF))
    root = tmp_path / "evidence"
    source = ControlledSource(path, root)
    captured = source.capture()
    stored = root / "snapshots" / (captured["snapshot"] + ".json")
    stored.write_bytes(b'corrupt')
    with pytest.raises(ValueError, match="snapshot"):
        source.capture()
    assert stored.read_bytes() == b'corrupt'


def test_successful_custom_run_is_not_conformance(tmp_path: Path) -> None:
    path = tmp_path / "brief.json"
    path.write_text(json.dumps(BRIEF))
    source = ControlledSource(path, tmp_path / "evidence")
    captured = source.capture()

    def altered(design: Design) -> object:
        def wrong_verdict(state: RoleState) -> TransformResult[RoleState]:
            verdict = ReviewVerdict(request_id=state.brief.request_id, evidence_count=0,
                                    result="evidence_missing")
            return TransformResult(state.model_copy(update={"verdict": verdict}), "done")
        return generate_graph(design.spec, state_type=design.state_type,
                              bindings={**design.bindings, "review_handoff": wrong_verdict}).candidate

    run = source.run(DESIGN, captured["snapshot"], candidate_factory=altered)
    assert run["succeeded"] is True
    assert run["output"]["state"]["verdict"]["result"] == "evidence_missing"
    report = source.check(DESIGN, captured["snapshot"], candidate_factory=altered)
    assert report["passed"] is False
    assert any(f["code"] == "behavioral_mismatch" for f in report["findings"])
    assert report["snapshot"] == captured["snapshot"]


@pytest.mark.parametrize("operation", ["run", "check"])
def test_generation_error_propagates(tmp_path: Path, operation: str) -> None:
    path = tmp_path / "brief.json"
    path.write_text(json.dumps(BRIEF))
    source = ControlledSource(path, tmp_path / "evidence")
    captured = source.capture()
    def failed(design: object) -> object:
        raise RuntimeError("generation unavailable")
    with pytest.raises(RuntimeError, match="generation unavailable"):
        getattr(source, operation)(DESIGN, captured["snapshot"], candidate_factory=failed)


def test_protected_root_rejected_and_read_only_source_permitted(tmp_path: Path) -> None:
    protected = tmp_path / "protected"
    protected.mkdir()
    path = protected / "brief.json"
    path.write_text(json.dumps(BRIEF))
    path.chmod(0o444)
    with pytest.raises(ValueError):
        ControlledSource(path, protected / "evidence", protected_roots=(protected,))
    source = ControlledSource(path, tmp_path / "evidence", protected_roots=(protected,))
    captured = source.capture()
    assert source.run(DESIGN, captured["snapshot"])["succeeded"] is True
    assert source.check(DESIGN, captured["snapshot"])["passed"] is True
    assert path.read_text() == json.dumps(BRIEF)
    assert path.stat().st_mode & 0o777 == 0o444
    assert list(protected.iterdir()) == [path]


def test_exact_4k_input_is_accepted_and_snapshot_is_byte_addressed(tmp_path: Path) -> None:
    path = tmp_path / "brief.json"
    data = json.dumps(BRIEF).encode()
    path.write_bytes(data + b' ' * (4096 - len(data)))
    source = ControlledSource(path, tmp_path / "evidence")
    captured = source.capture()
    assert source.check(DESIGN, captured["snapshot"])["passed"] is True
    path.write_bytes(data)
    assert source.capture()["snapshot"] != captured["snapshot"]


def test_capture_rechecks_source_parent_alias_overlap(tmp_path: Path) -> None:
    original = tmp_path / "original"
    original.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(original, target_is_directory=True)
    root = tmp_path / "evidence"
    root.mkdir()
    (root / "brief.json").write_text(json.dumps(BRIEF))
    source = ControlledSource(alias / "brief.json", root)
    alias.unlink()
    alias.symlink_to(root, target_is_directory=True)
    with pytest.raises(ValueError, match="overlap"):
        source.capture()
    assert list(root.iterdir()) == [root / "brief.json"]
