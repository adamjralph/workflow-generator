"""Completed-pair conformance from private recordings, without live capabilities."""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
import json
import math
import tempfile
from typing import Any, Literal

from agent_lab.conformance import check_conformance
from agent_lab.designer import report_view, validate_evidence_root
from agent_lab.designer import linkedin, linkedin_review
from agent_lab.designer.draft_runs import Evidence, _identifier, digest
from agent_lab.designer.drafts import DraftSource
from agent_lab.designer.linkedin import canonical
from agent_lab.generation import generate_graph
from agent_lab.model_operation import ModelOperation, ModelRequest, ModelResponse

Operations = Mapping[str, ModelOperation[linkedin_review.ReviewState]]


def generate_recorded_candidate(operations: Operations) -> object:
    return generate_graph(linkedin_review.SPEC, state_type=linkedin_review.ReviewState,
                          bindings={}, model_operations=operations).candidate


class RecordedPair:
    """One driver's ordered, exact-request response source; never a fallback."""
    mode: Literal["recorded"] = "recorded"

    def __init__(self, exchanges: tuple[tuple[ModelRequest, ModelResponse], ...]) -> None:
        self.exchanges = exchanges
        self.used = 0
        self.rejected = False

    def invoke(self, request: ModelRequest) -> ModelResponse:
        if self.rejected or self.used >= len(self.exchanges) or request != self.exchanges[self.used][0]:
            self.rejected = True
            raise ValueError("Recorded operation order or exact request differs")
        response = self.exchanges[self.used][1]
        self.used += 1
        return response


def _same(actual: object, expected: object) -> None:
    if canonical(actual) != canonical(expected):
        raise ValueError("Recording binding differs")


def _object(data: bytes) -> dict[str, Any]:
    value = json.loads(data)
    if not isinstance(value, dict) or canonical(value).encode() != data:
        raise ValueError("Expected canonical recording object")
    return value


@dataclass(frozen=True)
class Recording:
    initial: linkedin_review.ReviewState
    final: linkedin_review.ReviewState
    exchanges: tuple[tuple[ModelRequest, ModelResponse], ...]
    historical_usage: dict[str, Any]
    receipt_digest: str
    events: tuple[dict[str, Any], ...]


def load_recording(source: DraftSource, store: Evidence, snapshot: str, run_request: str) -> Recording:
    """Validate the entire completed evidence chain before either driver runs."""
    captured = source.load(snapshot)
    initial = linkedin_review.ReviewState(snapshot=snapshot, captured_json=canonical({
        key: captured[key] for key in ("selected", "guidance", "models", "instruction_version")}))
    receipt_bytes = store.read("receipt.json")
    receipt = _object(receipt_bytes)
    _same(sorted(receipt), sorted(("format_version", "view", "snapshot", "draft_digest",
                                  "review_digest", "exchanges", "digests")))
    _same(receipt["format_version"], 2)
    _same(receipt["snapshot"], snapshot)
    view = receipt["view"]
    _same({key: view[key] for key in ("snapshot", "run_request", "status", "succeeded", "failure",
                                    "used_steps", "generation_attempts")},
          {"snapshot": snapshot, "run_request": run_request, "status": "completed", "succeeded": True,
           "failure": None, "used_steps": 2, "generation_attempts": 2})
    names = receipt["exchanges"]
    if not isinstance(names, list) or len(names) != 2 or len(set(names)) != 2:
        raise ValueError("Expected exactly two ordered exchanges")
    for name in names:
        if not isinstance(name, str) or not name.endswith(".json"):
            raise ValueError("Invalid exchange name")
        _identifier(name[:-5])
    digests = receipt["digests"]
    logs = [name for name in digests if name.endswith(".jsonl")]
    if len(logs) != 1:
        raise ValueError("Expected one immutable execution log")
    _identifier(logs[0][:-6])
    _same(sorted(digests), sorted(["request.json", "claimed.json", "attempt.json",
                                  "guardian-attempt.json", *names, *logs]))
    records = {name: store.read(name) for name in digests}
    for name, data in records.items():
        _same(digest(data), digests[name])
        if name in names + logs:
            _same(name.split(".")[0], digest(data))
    identity = _object(records["request.json"])
    options = identity["execution_options"]
    _same(identity, {"snapshot": snapshot, "run_request": run_request, "status": "ready",
                     "workflow_version": "linkedin-pair-v1", "execution_options": options})
    _same(_object(records["claimed.json"]), identity)
    _same(sorted(options), sorted(("operations", "limits", "generator_mode", "guardian_mode", "guardian")))
    _same(options["operations"], {"draft_linkedin": [linkedin.VERSION, linkedin.SCHEMA_VERSION],
                                 "review_linkedin": [linkedin_review.VERSION, linkedin_review.SCHEMA_VERSION]})
    _same(options["limits"], {"workflow_steps": 2, "generation_attempts": 2, "attempts_per_role": 1,
        "deadline_seconds_per_role": 180, "response_bytes": 65536, "post_code_points": 3000,
        "provider_token_cap": None, "remote_cancellation": False})
    for role in ("generator", "guardian"):
        if options[role + "_mode"] not in ("fixture", "recorded", "live"):
            raise ValueError("Unknown recorded source mode")
    routing = options["guardian"]
    if routing:
        _same(sorted(routing), sorted(("project", "region", "credential_kind", "credential_source_digest",
                                     "auth_max_requests", "auth_persistence")))
        _identifier(routing["credential_source_digest"])
        _same(routing["credential_kind"], "pinned-authorized-user")
        _same(routing["auth_max_requests"], 1)
        _same(routing["auth_persistence"], False)
        if any(not isinstance(routing[key], str) or not routing[key] for key in ("project", "region")):
            raise ValueError("Invalid recorded routing")
    elif options["guardian_mode"] == "live":
        raise ValueError("Missing recorded Vertex routing")
    state = initial
    exchanges = []
    expected_events = []
    historical_usage = {}
    attribution = []
    for index, (role, reservation) in enumerate((("generator", "attempt.json"),
                                                ("guardian", "guardian-attempt.json"))):
        request = linkedin.prepare(state) if index == 0 else linkedin_review.prepare(state)
        attempt = {"format_version": 2, **identity, "ordinal": index + 1,
            "request": request.model_dump(), "request_digest": request.digest,
            "source_mode": options[role + "_mode"], "limits": {"attempts": 2, "attempts_per_role": 1,
                "deadline_seconds": 180, "response_bytes": 65536, "post_code_points": 3000,
                "remote_token_cap": None, "remote_cancellation": False}}
        _same(_object(records[reservation]), attempt)
        exchange = _object(records[names[index]])
        response = ModelResponse.model_validate(exchange["response"], strict=True)
        elapsed = exchange["elapsed_seconds"]
        if type(elapsed) not in (int, float) or not math.isfinite(elapsed) or elapsed < 0:
            raise ValueError("Invalid transport provenance")
        response_digest = digest(response.body.encode())
        _same(exchange, {**attempt, "response": response.model_dump(), "response_digest": response_digest,
                         "failure": None, "elapsed_seconds": elapsed})
        # Validate stored editorial results, not as a substitute for either driver.
        applied = (linkedin.apply(state, response) if index == 0 else linkedin_review.apply(state, response))
        state = linkedin_review.ReviewState.model_validate(applied.state.model_dump(), strict=True)
        if applied.outcome != ("draft" if index == 0 else "done"):
            raise ValueError("Recording did not complete both roles")
        model = next(item for item in captured["models"] if item["role"] == role)
        if options[role + "_mode"] == "live" and model["provider"] != ("openai-codex" if index == 0 else "vertex"):
            raise ValueError("Recorded provider differs")
        attribution.append({**model, "operation": request.operation,
                            "operation_version": request.operation_version, "schema_version": request.schema_version})
        historical_usage[role] = {key: getattr(response, key) for key in
            ("input_tokens", "output_tokens", "reasoning_tokens", "cache_read_tokens", "auth_requests")}
        expected_events.append({"run_id": run_request, "seq": index, "node": role, "stage": "transform",
            "transition": applied.outcome, "terminal": None if index == 0 else "COMPLETED",
            "detail": {"target": "guardian" if index == 0 else "COMPLETED", "failure": None,
                "used_steps": index + 1, "max_steps": 2, "operation": request.operation,
                "operation_version": request.operation_version, "schema_version": request.schema_version,
                "request_digest": request.digest, "response_digest": response_digest}})
        exchanges.append((request, response))
    _same([json.loads(row) for row in records[logs[0]].split(b"\n") if row], expected_events)
    if (attribution[0]["provider"], attribution[0]["model"]) == (attribution[1]["provider"], attribution[1]["model"]):
        raise ValueError("Review model is not independent")
    assert state.result is not None and state.result.post is not None and state.review is not None
    _same(view["result"], state.result.model_dump(mode="json"))
    _same(view["review"], state.review.model_dump(mode="json"))
    _same(receipt["draft_digest"], linkedin_review.draft_digest(state.result.post))
    _same(view["draft_digest"], receipt["draft_digest"])
    _same(receipt["review_digest"], digest(canonical(view["review"]).encode()))
    _same(view["attribution"], attribution)
    _same(view["role_usage"], historical_usage)
    _same(view["usage"], {key: value for key, value in historical_usage["generator"].items() if key != "auth_requests"})
    _same(view["auth_requests"], sum(item["auth_requests"] for item in historical_usage.values()))
    _same(view["evidence"], [str(store.directory / name) for name in
        ("request.json", "claimed.json", "attempt.json", "guardian-attempt.json", *names, *logs, "receipt.json")])
    return Recording(initial, state, tuple(exchanges), historical_usage, digest(receipt_bytes), tuple(expected_events))


class DraftChecks:
    """Read captured evidence only; no model source or credential configuration."""
    def __init__(self, source: DraftSource, evidence_dir: Path,
                 protected_roots: tuple[Path, ...] = ()) -> None:
        self.source = source
        self._protected = protected_roots
        self._root = validate_evidence_root(evidence_dir, protected_roots=protected_roots)

    def check(self, snapshot: str, run_request: str, *,
              candidate_factory: Callable[[Operations], object] = generate_recorded_candidate) -> dict[str, Any]:
        _identifier(snapshot)
        _identifier(run_request)
        if validate_evidence_root(self._root, protected_roots=self._protected) != self._root:
            raise ValueError("Pinned evidence root changed")
        store = Evidence(self._root / "draft-runs" / run_request)
        result: dict[str, Any] = {"passed": False, "cases": ["completed_pair"], "completed_cases": [],
            "outputs": [], "findings": [], "evidence": [], "snapshot": snapshot, "run_request": run_request,
            "model_calls": 0, "auth_requests": 0, "historical_usage": None,
            "message": "Case-scoped offline conformance, not a new editorial review or publication permission."}
        self._root.mkdir(parents=True, exist_ok=True, mode=0o700)
        destination = Path(tempfile.mkdtemp(prefix="draft-check-", dir=self._root))
        try:
            recording = load_recording(self.source, store, snapshot, run_request)
        except (ValueError, OSError, KeyError, TypeError, AttributeError, RecursionError, StopIteration):
            result["findings"] = [{"code": "invalid_recording", "path": ["recording"],
                "message": "Completed-pair evidence is missing, unsupported or inconsistent; no replay performed."}]
        else:
            result.update(historical_usage=recording.historical_usage, receipt_digest=recording.receipt_digest)
            reference, candidate = RecordedPair(recording.exchanges), RecordedPair(recording.exchanges)
            try:
                report = check_conformance(linkedin_review.SPEC,
                    candidate_factory(linkedin_review.operations(candidate, candidate)),
                    state_type=linkedin_review.ReviewState, bindings={},
                    model_operations=linkedin_review.operations(reference, reference),
                    cases={"completed_pair": recording.initial}, evidence_dir=destination, protected_roots=self._protected)
                result.update(report_view(report, ("completed_pair",)))
                for evidence in report.evidence:
                    expected_events = [{**event, "run_id": evidence.run_id} for event in recording.events]
                    for path in (evidence.reference_log, evidence.candidate_log):
                        _same([json.loads(row) for row in path.read_bytes().split(b"\n") if row], expected_events)
                if (reference.rejected or candidate.rejected or reference.used != 2 or candidate.used != 2
                        or len(report.outputs) != 1
                        or report.outputs[0].terminal != "COMPLETED" or report.outputs[0].used_steps != 2
                        or canonical(report.outputs[0].state.model_dump(mode="json")) !=
                           canonical(recording.final.model_dump(mode="json"))):
                    result["passed"] = False
                    result["findings"].append({"code": "recording_mismatch", "path": ["replay"],
                        "message": "Both drivers must consume the exact pair and reproduce its completed result."})
            except (ValueError, OSError, TypeError):
                result["passed"] = False
                result["findings"].append({"code": "replay_failed", "path": ["replay"],
                    "message": "Independent offline replay could not complete; no conformance established."})
        result["check_receipt"] = str(destination / "check.json")
        Evidence(destination).publish("check.json", canonical(result).encode())
        return result
