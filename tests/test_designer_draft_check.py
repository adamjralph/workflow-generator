"""Completed-pair Check at the captured evidence and actual candidate seams."""
import json
from dataclasses import replace
from pathlib import Path

import pytest

from agent_lab.designer.draft_checks import DraftChecks, generate_recorded_candidate
from agent_lab.designer.draft_runs import DraftRuns, digest
from agent_lab.designer.linkedin import canonical
from agent_lab.designer.drafts import DraftSource
from tests.test_designer_drafts import draft, operator  # noqa: F401
from tests.test_designer_review_server import FixtureSource, GuardianSource, RESULT


def completed(operator, verdict="Approved"):
    config, folder, evidence = operator
    draft(folder, "old.md")
    source = DraftSource(config, evidence)
    snapshot = source.capture()["snapshot"]
    generator, guardian = FixtureSource(), GuardianSource(verdict)
    runs = DraftRuns(source, evidence, generator, guardian_source=guardian)
    request = runs.create_request(snapshot)["run_request"]
    result = runs.run(snapshot, request)
    assert result["status"] == "completed"
    return DraftChecks(source, evidence), snapshot, request, result


def test_completed_pair_replays_fresh_independent_logs_without_new_usage(operator):
    checks, snapshot, request, saved = completed(operator)
    result = checks.check(snapshot, request)
    assert result["passed"] and result["completed_cases"] == ["completed_pair"]
    assert result["snapshot"] == snapshot and result["run_request"] == request
    assert result["model_calls"] == result["auth_requests"] == 0
    assert result["historical_usage"] == saved["role_usage"]
    assert result["outputs"][0]["state"]["result"] == RESULT
    assert result["outputs"][0]["state"]["review"] == saved["review"]
    assert result["outputs"][0]["terminal"] == "COMPLETED"
    assert result["outputs"][0]["route"] == [["generator", "draft", "guardian"], ["guardian", "done", "COMPLETED"]]
    evidence = result["evidence"][0]
    reference, candidate = Path(evidence["reference_log"]), Path(evidence["candidate_log"])
    assert reference != candidate and reference.read_bytes() == candidate.read_bytes()
    assert len([json.loads(row) for row in reference.read_text().splitlines()]) == 2
    assert checks.check(snapshot, request)["evidence"] != result["evidence"]


@pytest.mark.parametrize("change", ["missing", "corrupt", "reordered", "duplicate", "unused",
                                    "partial", "wrong_snapshot", "version", "omitted_digest",
                                    "wrong_request", "wrong_response", "wrong_log", "wrong_review"])
def test_incomplete_or_inconsistent_recording_never_passes(operator, change):
    checks, snapshot, request, _ = completed(operator)
    directory = operator[2] / "draft-runs" / request
    receipt_path = directory / "receipt.json"
    receipt = json.loads(receipt_path.read_bytes())
    if change in ("missing", "corrupt"):
        exchange = directory / receipt["exchanges"][0]
        if change == "missing":
            exchange.unlink()
        else:
            exchange.write_bytes(b'{}')
    elif change == "reordered":
        receipt["exchanges"].reverse()
    elif change == "duplicate":
        receipt["exchanges"][1] = receipt["exchanges"][0]
    elif change == "unused":
        receipt["exchanges"].append(receipt["exchanges"][0])
    elif change == "partial":
        receipt["view"]["status"] = "uncertain"
    elif change == "wrong_snapshot":
        receipt["snapshot"] = "0" * 64
    elif change == "version":
        receipt["format_version"] = 1
    elif change == "omitted_digest":
        receipt["digests"].pop("claimed.json")
    elif change == "wrong_review":
        receipt["view"]["review"]["optional_preferences"] = ["Invented review"]
        receipt["review_digest"] = digest(canonical(receipt["view"]["review"]).encode())
    elif change in ("wrong_request", "wrong_response"):
        name = receipt["exchanges"][0]
        exchange = json.loads((directory / name).read_bytes())
        if change == "wrong_request":
            payload = json.loads(exchange["request"]["request_json"])
            payload["model"] = "different-model"
            exchange["request"]["request_json"] = canonical(payload)
        else:
            exchange["response"]["body"] = "{}"
        data = canonical(exchange).encode()
        new_name = digest(data) + ".json"
        (directory / new_name).write_bytes(data)
        (directory / new_name).chmod(0o600)
        receipt["exchanges"][0] = new_name
        receipt["digests"].pop(name)
        receipt["digests"][new_name] = digest(data)
    elif change == "wrong_log":
        name = next(name for name in receipt["digests"] if name.endswith(".jsonl"))
        events = [json.loads(row) for row in (directory / name).read_bytes().splitlines()]
        events[-1]["detail"]["used_steps"] = 1
        data = b"".join((canonical(event) + "\n").encode() for event in events)
        new_name = digest(data) + ".jsonl"
        (directory / new_name).write_bytes(data)
        (directory / new_name).chmod(0o600)
        receipt["digests"].pop(name)
        receipt["digests"][new_name] = digest(data)
    receipt_path.write_text(canonical(receipt))
    result = checks.check(snapshot, request)
    assert not result["passed"] and result["findings"]
    assert not result["completed_cases"]
    assert Path(result["check_receipt"]).is_file()
    assert result["model_calls"] == result["auth_requests"] == 0


@pytest.mark.parametrize("change", ["prepare", "apply", "structure", "unused", "exhausted", "caught_extra"])
def test_actual_candidate_drift_is_rejected_even_with_valid_recordings(operator, change):
    checks, snapshot, request, _ = completed(operator)

    def candidate_factory(operations):
        operations = dict(operations)
        key = "review_linkedin"
        original = operations[key]
        if change == "prepare":
            def altered_prepare(state):
                request = original.prepare(state)
                payload = json.loads(request.request_json)
                payload["model"] = "altered-model"
                return request.model_copy(update={"request_json": canonical(payload)})
            operations[key] = replace(original, prepare=altered_prepare)
        elif change == "apply":
            def altered_apply(state, response):
                result = original.apply(state, response)
                review = result.state.review.model_copy(update={"optional_preferences": ("Altered advice",)})
                return replace(result, state=result.state.model_copy(update={"review": review}))
            operations[key] = replace(original, apply=altered_apply)
        elif change == "caught_extra":
            def extra_response(state, response):
                try:
                    original.source.invoke(original.prepare(state))
                except ValueError:
                    pass
                return original.apply(state, response)
            operations[key] = replace(original, apply=extra_response)
        elif change == "unused":
            # Identical responses from a different source cannot attest to consuming this recording.
            operations["draft_linkedin"] = replace(operations["draft_linkedin"], source=FixtureSource())
            operations[key] = replace(original, source=GuardianSource())
        elif change == "exhausted":
            def consumes_twice(state):
                request = original.prepare(state)
                original.source.invoke(request)
                return request
            operations[key] = replace(original, prepare=consumes_twice)
        if change == "structure":
            from agent_lab.designer.linkedin_review import SPEC, ReviewState
            from agent_lab.generation import generate_graph
            return generate_graph(SPEC.model_copy(update={"budget": 3}), state_type=ReviewState,
                                  bindings={}, model_operations=operations).candidate
        return generate_recorded_candidate(operations)

    result = checks.check(snapshot, request, candidate_factory=candidate_factory)
    assert not result["passed"] and result["findings"]
    assert Path(result["check_receipt"]).is_file()


@pytest.mark.parametrize("verdict", ["Approved", "Changes requested", "Blocked"])
def test_check_has_no_network_credentials_or_original_source_dependency(operator, monkeypatch, verdict):
    import os
    import shutil
    import socket
    checks, snapshot, request, saved = completed(operator, verdict)
    root = operator[2]
    before = {path: (path.read_bytes(), path.stat().st_mode, path.stat().st_mtime_ns)
              for path in root.rglob("*") if path.is_file()}
    shutil.rmtree(operator[0].parent)
    attempted = []
    original_open, path_open = os.open, Path.open

    def deny_network(*args, **kwargs):
        attempted.append("network")
        raise AssertionError("Replay attempted network")

    def only_evidence(path, *args, **kwargs):
        if not Path(path).is_relative_to(root):
            attempted.append(str(path))
            raise AssertionError("Replay read outside immutable evidence")
        return original_open(path, *args, **kwargs)

    def only_evidence_path(path, *args, **kwargs):
        if not path.is_relative_to(root):
            attempted.append(str(path))
            raise AssertionError("Replay read outside immutable evidence")
        return path_open(path, *args, **kwargs)

    monkeypatch.setattr(socket.socket, "connect", deny_network)
    monkeypatch.setattr(socket, "getaddrinfo", deny_network)
    monkeypatch.setattr(os, "open", only_evidence)
    monkeypatch.setattr(Path, "open", only_evidence_path)
    result = checks.check(snapshot, request)
    assert result["passed"] and not attempted
    assert result["outputs"][0]["state"]["review"]["verdict"] == verdict
    assert result["historical_usage"] == saved["role_usage"]
    assert {path: (path.read_bytes(), path.stat().st_mode, path.stat().st_mtime_ns)
            for path in before} == before


@pytest.mark.parametrize("outcome", ["legacy", "blocked", "invalid", "timeout", "ready"])
def test_only_a_completed_pair_is_eligible_for_check(operator, outcome):
    config, folder, evidence = operator
    draft(folder, "old.md")
    source = DraftSource(config, evidence)
    snapshot = source.capture()["snapshot"]
    runs = DraftRuns(source, evidence, FixtureSource("blocked" if outcome == "blocked" else "draft"),
                     guardian_source=None if outcome == "legacy" else
                     GuardianSource(outcome=outcome if outcome in ("invalid", "timeout") else None))
    request = runs.create_request(snapshot)["run_request"]
    if outcome != "ready":
        runs.run(snapshot, request)
    result = DraftChecks(source, evidence).check(snapshot, request)
    assert not result["passed"] and result["findings"][0]["code"] == "invalid_recording"
    assert result["evidence"] == [] and result["historical_usage"] is None


def test_changed_evidence_root_is_rejected_before_any_write(operator, tmp_path):
    checks, snapshot, request, _ = completed(operator)
    root = operator[2]
    original = root.with_name("original-evidence")
    root.rename(original)
    other = tmp_path / "other"
    other.mkdir()
    root.symlink_to(other, target_is_directory=True)
    with pytest.raises(ValueError):
        checks.check(snapshot, request)
    assert list(other.iterdir()) == []


@pytest.mark.parametrize("part", ["receipt", "snapshot", "request", "claim", "attempt", "exchange", "log"])
@pytest.mark.parametrize("defect", ["symlink", "public", "missing"])
def test_unsafe_or_missing_evidence_cannot_pass(operator, part, defect):
    checks, snapshot, request, _ = completed(operator)
    root = operator[2]
    directory = root / "draft-runs" / request
    receipt = json.loads((directory / "receipt.json").read_bytes())
    paths = {"receipt": directory / "receipt.json", "snapshot": root / "draft-snapshots" / f"{snapshot}.json",
             "request": directory / "request.json", "claim": directory / "claimed.json",
             "attempt": directory / "guardian-attempt.json", "exchange": directory / receipt["exchanges"][1],
             "log": directory / next(name for name in receipt["digests"] if name.endswith(".jsonl"))}
    path = paths[part]
    if defect == "symlink":
        target = path.with_suffix(".original")
        path.rename(target)
        path.symlink_to(target)
    elif defect == "public":
        path.chmod(0o644)
    else:
        path.unlink()
    result = checks.check(snapshot, request)
    assert not result["passed"] and result["findings"][0]["code"] == "invalid_recording"
    assert result["completed_cases"] == []


@pytest.mark.parametrize("failure", ["lost_events", "receipt_write"])
def test_replay_storage_failures_never_establish_conformance(operator, monkeypatch, failure):
    import os
    checks, snapshot, request, _ = completed(operator)
    original_open, original_link = Path.open, os.link

    def reject_receipt(src, dst, *args, **kwargs):
        if Path(dst).name == "check.json":
            raise OSError("PRIVATE_STORAGE_FAILURE")
        return original_link(src, dst, *args, **kwargs)

    if failure == "lost_events":
        # The driver uses a+ for append_next, which requires fileno for its lock.
        # Dropping writes through a real file wrapper retains the public I/O seam.
        class LostWrites:
            def __init__(self, handle):
                self.handle = handle
            def __enter__(self):
                self.handle.__enter__()
                return self
            def __exit__(self, *args):
                return self.handle.__exit__(*args)
            def __getattr__(self, key):
                return getattr(self.handle, key)
            def write(self, value):
                return len(value)
        def lost_append(path, mode="r", *args, **kwargs):
            handle = original_open(path, mode, *args, **kwargs)
            return LostWrites(handle) if path.name.endswith(("-reference.jsonl", "-candidate.jsonl")) and mode == "a+" else handle
        monkeypatch.setattr(Path, "open", lost_append)
        result = checks.check(snapshot, request)
        assert not result["passed"] and result["findings"]
    else:
        monkeypatch.setattr(os, "link", reject_receipt)
        with pytest.raises(OSError):
            checks.check(snapshot, request)
        assert not list(operator[2].glob("draft-check-*/check.json"))
