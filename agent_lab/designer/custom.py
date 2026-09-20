"""Single offline generated-graph runs, separate from supplied-case conformance."""
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from . import Design, generate_candidate, validate_evidence_root
from .triage import TriageRequest, TriageState, author_triage
from agent_lab.generation import GraphCandidate
from agent_lab.reference import AuditError
from agent_lab.runlog import RunLog


def run_request(raw: object, request: object, *, evidence_dir: Path,
                candidate_factory: Callable[[Design], object] = generate_candidate,
                protected_roots: tuple[Path, ...] = ()) -> dict[str, Any]:
    """Validate before generation; trusted Python injection is never HTTP input.

    Errors propagate without a success claim. A recorded safety terminal is a
    failed run, even though the engine successfully recorded its outcome.
    """
    design = author_triage(raw)
    submitted = TriageRequest.model_validate(request)
    destination = validate_evidence_root(evidence_dir, protected_roots=protected_roots)
    candidate = candidate_factory(design)
    if type(candidate) is not GraphCandidate:
        raise ValueError("Expected exact GraphCandidate type")
    if (candidate.state_type is not TriageState
            or candidate.inspect_structure() != design.spec):
        raise ValueError("Candidate execution configuration differs from authored Spec")
    destination.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix="run-", dir=destination))
    log = RunLog(root / "candidate.jsonl")
    actual = candidate.run(TriageState.model_validate(submitted.model_dump()),
                           run_id=root.name, log=log)
    events = log.read()
    if (not events or events[-1].terminal != actual.terminal
            or len(events) != actual.used_steps + (actual.terminal == "FAILED_BUDGET")
            or [event.seq for event in events] != list(range(len(events)))
            or any(event.run_id != root.name for event in events)
            or events[0].node != design.spec.entry
            or [event.node for event in events[1:]]
               != [event.detail["target"] for event in events[:-1]]
            or events[-1].detail["target"] != actual.terminal
            or [event.detail["used_steps"] for event in events]
               != [min(index + 1, design.spec.budget) for index in range(len(events))]
            or events[-1].detail["used_steps"] != actual.used_steps):
        raise AuditError("Incomplete run evidence; no successful run established")
    return {
        "succeeded": actual.terminal == "COMPLETED",
        "input": submitted.model_dump(mode="json"),
        "output": {"state": actual.state.model_dump(mode="json"),
                   "terminal": actual.terminal, "used_steps": actual.used_steps,
                   "route": [[event.node, event.transition, event.detail["target"]]
                             for event in events]},
        "evidence": str(log.path),
    }
