"""Useful recorded LinkedIn pairs joined to declared outcome/remedy/local alert."""
import json
from pathlib import Path
import socket
import sys

import pytest

from agent_lab.designer import review_outcome
from agent_lab.designer.draft_runs import digest
from agent_lab.designer.linkedin import canonical
from tests.test_designer_draft_check import completed
from tests.test_designer_drafts import operator  # noqa: F401
from tests.test_outcome_alerts import receiver


def run(operator, *, verdict="Approved", driver="reference", allowance=2, accepted=("Approved",),
        endpoint=None):
    checks, snapshot, request, saved = completed(operator, verdict)
    result = review_outcome.check_review_outcome(checks.source, operator[2], snapshot, request,
        evidence_dir=operator[2].parent / "outcomes", accepted_verdicts=accepted,
        step_allowance=allowance, driver=driver, endpoint=endpoint)
    return result, saved


@pytest.mark.parametrize("driver", ["reference", "graph"])
@pytest.mark.parametrize("verdict", ["Approved", "Changes requested", "Blocked"])
def test_completed_review_packet_exact_provenance_and_explicit_policy(operator, receiver, driver, verdict):
    _, received, endpoint = receiver
    result, saved = run(operator, verdict=verdict, driver=driver, accepted=(verdict,), endpoint=endpoint)
    assert result.remedy.receipt.status == "passed"
    assert result.remedy.receipt.reserved_steps == 1 and result.remedy.repair is None
    assert result.alert.receipt.status == "suppressed" and received == []
    packet = json.loads(result.packet_path.read_bytes())
    assert packet["result"] == saved["result"] and packet["review"] == saved["review"]
    assert packet["verdict"] == verdict and packet["human_decision"] == "required"
    assert packet["scope"] == "copy-only"
    assert packet["snapshot"] == saved["snapshot"] and packet["run_request"] == saved["run_request"]
    original = Path(saved["evidence"][-1]).read_bytes()
    assert packet["receipt_digest"] == digest(original)
    assert packet["check_digest"] == digest(Path(result.check["check_receipt"]).read_bytes())
    assert packet["draft_digest"] == saved["draft_digest"]
    assert packet["review_digest"] == digest(canonical(saved["review"]).encode())
    assert packet["historical_usage"] == saved["role_usage"]
    assert packet["model_calls"] == packet["auth_requests"] == 0
    assert result.check["completed_cases"] == ["completed_pair"]
    assert result.check["evidence"][0]["reference_log"] != result.check["evidence"][0]["candidate_log"]


@pytest.mark.parametrize("driver", ["reference", "graph"])
@pytest.mark.parametrize("allowance, expected", [(1, "exhausted"), (2, "repaired")])
def test_missing_packet_one_reserved_local_repair(operator, monkeypatch, driver, allowance, expected):
    original = review_outcome._write_packet
    calls = []

    def miss_once(output, state):
        calls.append(output)
        if len(calls) == 1:
            return review_outcome.TransformResult(state, "done")
        return original(output, state)

    monkeypatch.setattr(review_outcome, "_write_packet", miss_once)
    result, _ = run(operator, driver=driver, allowance=allowance)
    assert result.remedy.receipt.status == expected
    assert result.remedy.receipt.reserved_steps == allowance == len(calls)
    assert result.remedy.original.verdict.findings[0].code == "missing_file"
    if allowance == 2:
        assert result.remedy.repair.verdict.passed
        assert calls[0] != calls[1]
        assert json.loads(result.packet_path.read_bytes())["human_decision"] == "required"
    assert result.alert is None


@pytest.mark.parametrize("driver", ["reference", "graph"])
@pytest.mark.parametrize("verdict", ["Changes requested", "Blocked"])
def test_rejected_verdict_never_rewritten_and_alert_excludes_private_copy(operator, receiver, driver, verdict):
    _, received, endpoint = receiver
    result, saved = run(operator, verdict=verdict, driver=driver, endpoint=endpoint)
    assert result.remedy.receipt.status == "exhausted" and result.remedy.receipt.reserved_steps == 2
    assert result.alert.receipt.status == "delivered" and len(received) == 1
    for attempt in (result.remedy.original, result.remedy.repair):
        assert [(f.code, f.requirement) for f in attempt.verdict.findings] == [("unexpected_value", "verdict")]
        packet = json.loads((attempt.root / "output" / "review-packet.json").read_bytes())
        assert packet["verdict"] == verdict and packet["review"] == saved["review"]
    payload = json.loads(received[0][2])
    assert saved["result"]["post"] not in json.dumps(payload)
    assert "result" not in payload and "review" not in payload and "historical_usage" not in payload
    assert payload["unmet"] == [{"code": "unexpected_value", "requirement": "verdict"}]


@pytest.mark.parametrize("defect", ["missing", "corrupt", "incomplete"])
def test_invalid_recording_stops_before_output_or_repair(operator, defect):
    checks, snapshot, request, _ = completed(operator)
    path = operator[2] / "draft-runs" / request / "receipt.json"
    if defect == "missing":
        path.unlink()
    elif defect == "corrupt":
        path.write_bytes(b'{}')
    else:
        value = json.loads(path.read_bytes())
        value["view"]["status"] = "uncertain"
        path.write_text(canonical(value))
    destination = operator[2].parent / "outcomes"
    with pytest.raises(ValueError, match="replay failed"):
        review_outcome.check_review_outcome(checks.source, operator[2], snapshot, request,
            evidence_dir=destination, accepted_verdicts=("Approved",), step_allowance=2)
    assert not destination.exists()


@pytest.mark.parametrize("target", ["config", "draft", "guidance", "profile", "recordings", "ancestor"])
def test_output_cannot_overlap_private_sources_or_recordings(operator, target):
    checks, snapshot, request, _ = completed(operator)
    config, folder, evidence = operator
    manifest = json.loads(config.read_bytes())
    paths = {"config": config, "draft": folder, "guidance": config.parent / next(iter(manifest["guidance"].values())),
             "profile": config.parent / manifest["profiles"]["generator"], "recordings": evidence,
             "ancestor": evidence.parent}
    with pytest.raises(ValueError):
        review_outcome.check_review_outcome(checks.source, evidence, snapshot, request,
            evidence_dir=paths[target], accepted_verdicts=("Approved",), step_allowance=2)


def test_replay_no_network_and_preserves_all_existing_bytes(operator, monkeypatch):
    checks, snapshot, request, saved = completed(operator)
    before = {path: path.read_bytes() for path in operator[2].parent.rglob("*") if path.is_file()}

    def deny(*args, **kwargs):
        raise AssertionError("Offline review outcome attempted network access")

    monkeypatch.setattr(socket, "socket", deny)
    monkeypatch.setattr(socket, "create_connection", deny)
    result = review_outcome.check_review_outcome(checks.source, operator[2], snapshot, request,
        evidence_dir=operator[2].parent / "outcomes", accepted_verdicts=("Approved",), step_allowance=2)
    assert result.remedy.passed
    assert all(path.read_bytes() == content for path, content in before.items())
    assert json.loads(result.packet_path.read_bytes())["historical_usage"] == saved["role_usage"]


@pytest.mark.parametrize("accepted, allowance, driver", [
    ((), 2, "reference"), (("Approved", "Approved"), 2, "reference"),
    (("invalid",), 2, "reference"), (("Approved",), True, "reference"),
    (("Approved",), 3, "reference"), (("Approved",), 2, "invalid")])
def test_invalid_policy_stops_before_replay(operator, accepted, allowance, driver):
    checks, snapshot, request, _ = completed(operator)
    before = set(operator[2].iterdir())
    with pytest.raises(ValueError):
        review_outcome.check_review_outcome(checks.source, operator[2], snapshot, request,
            evidence_dir=operator[2].parent / "outcomes", accepted_verdicts=accepted,
            step_allowance=allowance, driver=driver)
    assert set(operator[2].iterdir()) == before


@pytest.mark.parametrize("verdict, code", [("Approved", 0), ("Blocked", 1)])
def test_cli_reports_paths_without_copy_and_nonzero_unresolved(operator, monkeypatch, capsys, verdict, code):
    _, snapshot, request, saved = completed(operator, verdict)
    monkeypatch.setattr(sys, "argv", ["review_outcome", "--config", str(operator[0]),
        "--recordings", str(operator[2]), "--snapshot", snapshot, "--run-request", request,
        "--store", str(operator[2].parent / "outcomes"), "--accept-verdict", "Approved",
        "--step-allowance", "2", "--driver", "graph"])
    if code:
        with pytest.raises(SystemExit) as exit:
            review_outcome.main()
        assert exit.value.code == code
    else:
        review_outcome.main()
    output = capsys.readouterr().out
    view = json.loads(output)
    assert view["status"] == ("exhausted" if code else "passed")
    assert view["alert_status"] == "not_requested" and view["human_decision"] == "required"
    assert saved["result"]["post"] not in output


def test_packet_execution_failure_is_ineligible_and_not_retried(operator, monkeypatch):
    calls = []

    def fail(output, state):
        calls.append(output)
        raise OSError("private error text")

    monkeypatch.setattr(review_outcome, "_write_packet", fail)
    result, _ = run(operator)
    assert result.remedy.receipt.status == "ineligible" and len(calls) == 1
    assert result.remedy.repair is None
    assert "private error text" not in result.remedy.receipt_path.read_text()
