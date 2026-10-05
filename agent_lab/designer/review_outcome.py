"""Offline declared outcome for an existing completed LinkedIn review pair.

Repair rebuilds a review packet, never revises copy or changes Guardian's verdict.
An editorial verdict is evidence for a caller's policy, never publication permission.
"""
import argparse
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from agent_lab.alerts import AlertAdapter, DeliveredAlert, deliver_alert_with_adapter, deliver_outcome_alert
from agent_lab.designer import validate_evidence_root
from agent_lab.designer.draft_checks import DraftChecks
from agent_lab.designer.draft_runs import digest
from agent_lab.designer.drafts import DraftSource
from agent_lab.designer.linkedin import canonical
from agent_lab.outcome import OutputVerdict
from agent_lab.reference import TransformResult
from agent_lab.remedy import RemediedRun, run_with_remedy
from agent_lab.spec import JsonOutputExpectation, Route, StringFieldExpectation, TransformNode, WorkflowSpec

Verdict = Literal["Approved", "Changes requested", "Blocked"]
ATTRIBUTION_FIELDS = ("snapshot", "run_request", "receipt_digest", "check_digest", "draft_digest", "review_digest")


class PacketInput(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")
    packet_json: str


@dataclass(frozen=True)
class ReviewOutcome:
    check: dict[str, Any]
    remedy: RemediedRun[PacketInput]
    alert: DeliveredAlert | None

    @property
    def packet_path(self) -> Path:
        latest = self.remedy.repair or self.remedy.original
        return latest.root / "output" / "review-packet.json"


def _write_packet(output: Path, state: PacketInput) -> TransformResult[PacketInput]:
    with (output / "review-packet.json").open("x", encoding="utf-8") as handle:
        handle.write(state.packet_json)
    return TransformResult(state, "done")


def check_review_outcome(source: DraftSource, recording_dir: Path, snapshot: str, run_request: str, *,
                         evidence_dir: Path, accepted_verdicts: tuple[Verdict, ...], step_allowance: int,
                         driver: Literal["reference", "graph"] = "reference", endpoint: str | None = None,
                         protected_roots: tuple[Path, ...] = (), adapter: AlertAdapter | None = None) -> ReviewOutcome:
    """Replay the exact pair before projecting a bounded, declared review packet.

    The caller must name its accepted editorial verdicts and local step allowance.
    Each request creates fresh evidence; it never resumes a provider attempt.
    Invalid recordings stop before packet production/repair/delivery. A rejected
    editorial verdict remains rejected after repair: no new model call is made.
    """
    if endpoint is not None and adapter is not None:
        raise ValueError("Choose one explicit alert transport")
    if (not accepted_verdicts or len(set(accepted_verdicts)) != len(accepted_verdicts)
            or any(value not in ("Approved", "Changes requested", "Blocked") for value in accepted_verdicts)):
        raise ValueError("Name distinct accepted Guardian verdicts")
    if type(step_allowance) is not int or step_allowance not in (1, 2):
        raise ValueError("Offline step allowance must be one or two")
    if driver not in ("reference", "graph"):
        raise ValueError("Unknown driver")
    if recording_dir.expanduser().resolve() != source.evidence_root:
        raise ValueError("Recording store must match the captured source's pinned evidence root")
    destination = source.validate_output_root(evidence_dir)
    destination = validate_evidence_root(destination, protected_roots=(*protected_roots, recording_dir))
    if recording_dir.resolve().is_relative_to(destination):
        raise ValueError("Derived output and recording store must be disjoint")
    check = DraftChecks(source, recording_dir, protected_roots).check(snapshot, run_request)
    if not check["passed"]:
        raise ValueError(f"Completed-pair replay failed; inspect {check['check_receipt']}")
    check_bytes = Path(check["check_receipt"]).read_bytes()
    if json.loads(check_bytes) != check:
        raise ValueError("Saved check receipt changed")
    state = check["outputs"][0]["state"]
    packet = {
        "snapshot": snapshot, "run_request": run_request,
        "receipt_digest": check["receipt_digest"], "check_digest": digest(check_bytes),
        "draft_digest": state["review"]["draft_digest"],
        "review_digest": digest(canonical(state["review"]).encode()),
        "verdict": state["review"]["verdict"], "scope": "copy-only", "human_decision": "required",
        "result": state["result"], "review": state["review"],
        "historical_usage": check["historical_usage"], "model_calls": 0, "auth_requests": 0,
    }
    # Bind exact identities/scope as literal values using ticket35's contract.
    strings = tuple(StringFieldExpectation(field=key, allowed_values=(packet[key],)) for key in
        (*ATTRIBUTION_FIELDS, "scope", "human_decision")) + (
            StringFieldExpectation(field="verdict", allowed_values=accepted_verdicts),)
    spec = WorkflowSpec(entry="packet", budget=1,
        nodes=(TransformNode(id="packet", operation="write_review_packet",
            expected_output=JsonOutputExpectation(file="review-packet.json", required_fields=tuple(packet),
                                                  string_fields=strings)),),
        edges=(Route(source="packet", outcome="done", target="COMPLETED"),),
        terminals=("COMPLETED", "FAILED_VALIDATION", "FAILED_BUDGET"))

    def bindings(output: Path):
        return {"write_review_packet": lambda initial: _write_packet(output, initial)}

    def repair(output: Path, failed: OutputVerdict):
        # The same immutable projection is all that local repair is allowed to do.
        return bindings(output)

    remedy = run_with_remedy(spec, PacketInput(packet_json=canonical(packet)), bindings_factory=bindings,
        repair_bindings_factory=repair, step_allowance=step_allowance, evidence_dir=destination, driver=driver,
        protected_roots=(*protected_roots, recording_dir))
    alert = (deliver_outcome_alert(remedy, endpoint=endpoint, private_fields=ATTRIBUTION_FIELDS)
             if endpoint is not None else
             deliver_alert_with_adapter(remedy, adapter=adapter, private_fields=ATTRIBUTION_FIELDS)
             if adapter is not None else None)
    return ReviewOutcome(check, remedy, alert)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--recordings", type=Path, required=True)
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--run-request", required=True)
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--accept-verdict", action="append", choices=("Approved", "Changes requested", "Blocked"),
                        required=True)
    parser.add_argument("--step-allowance", type=int, choices=(1, 2), required=True)
    parser.add_argument("--driver", choices=("reference", "graph"), default="reference")
    parser.add_argument("--endpoint")
    args = parser.parse_args()
    source = DraftSource(args.config, args.recordings)
    outcome = check_review_outcome(source, args.recordings, args.snapshot, args.run_request,
        evidence_dir=args.store, accepted_verdicts=tuple(args.accept_verdict), step_allowance=args.step_allowance,
        driver=args.driver, endpoint=args.endpoint)
    print(json.dumps({"status": outcome.remedy.receipt.status, "receipt": str(outcome.remedy.receipt_path),
        "packet": str(outcome.packet_path), "check_receipt": outcome.check["check_receipt"],
        "alert_status": outcome.alert.receipt.status if outcome.alert else "not_requested",
        "model_calls": 0, "auth_requests": 0, "human_decision": "required"}, indent=2))
    if not outcome.remedy.passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
