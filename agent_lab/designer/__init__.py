"""Bounded questionnaire front door onto the existing generation/checking core.

The JSON view is private UI transport, not a persistent spec format.
"""
import os
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from agent_lab.conformance import check_conformance
from agent_lab.generation import generate_graph
from agent_lab.reference import TransformResult
from agent_lab.spec import DecisionNode, Route, TransformNode, WorkflowSpec


class Answers(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    threshold: int = Field(strict=True)
    below: Literal["ACCEPTED", "REVIEW"]
    at_or_above: Literal["ACCEPTED", "REVIEW"]


class RequestState(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    score: int


@dataclass(frozen=True)
class Design:
    answers: Answers
    spec: WorkflowSpec
    bindings: Mapping[str, Callable[[RequestState], object]]
    cases: Mapping[str, RequestState]
    state_type: type[RequestState] = RequestState

    def view(self) -> dict[str, Any]:
        return {
            "answers": self.answers.model_dump(),
            "nodes": [{"id": node.id, "kind": node.kind,
                       "label": ("Receive request" if node.id == "receive" else
                                 f"Score >= {self.answers.threshold}?")}
                      for node in self.spec.nodes],
            "edges": [{"source": edge.source, "outcome": edge.outcome, "target": edge.target}
                      for edge in self.spec.edges if isinstance(edge, Route)],
            "terminals": list(self.spec.terminals), "budget": self.spec.budget,
            "cases": [{"name": name, "score": state.score,
                       "expected_terminal": (self.answers.below if name == "below"
                                             else self.answers.at_or_above)}
                      for name, state in self.cases.items()],
        }


def author_design(raw: object) -> Design:
    answers = Answers.model_validate(raw)
    if answers.threshold not in (10, 50, 100):
        raise ValueError("Threshold must be 10, 50 or 100")
    key = f"score_at_least_{answers.threshold}"
    spec = WorkflowSpec(entry="receive", budget=2,
        nodes=(TransformNode(id="receive", operation="receive_request"),
               DecisionNode(id="threshold", value=key, cases=("below", "at_or_above"))),
        edges=(Route(source="receive", outcome="done", target="threshold"),
               Route(source="threshold", outcome="below", target=answers.below),
               Route(source="threshold", outcome="at_or_above", target=answers.at_or_above)),
        terminals=("ACCEPTED", "REVIEW", "FAILED_VALIDATION", "FAILED_BUDGET"))
    bindings: dict[str, Callable[[RequestState], object]] = {
        "receive_request": lambda state: TransformResult(state, "done"),
        key: lambda state: "at_or_above" if state.score >= answers.threshold else "below",
    }
    return Design(answers, spec, MappingProxyType(bindings), MappingProxyType({
        "below": RequestState(score=answers.threshold - 1),
        "at": RequestState(score=answers.threshold),
        "above": RequestState(score=answers.threshold + 1),
    }))


def validate_evidence_root(path: Path, *, protected_roots: tuple[Path, ...] = ()) -> Path:
    """Apply the core's read-only boundary before serving or generating anything."""
    destination = path.expanduser().resolve()
    protected = (Path.home() / ".hermes", Path(__file__).resolve().parents[2], *protected_roots)
    if configured := os.environ.get("HERMES_HOME"):
        protected += (Path(configured).expanduser(),)
    if host_file := getattr(sys.modules.get("hermes_cli"), "__file__", None):
        protected += (Path(host_file).resolve().parents[1],)
    if any(destination.is_relative_to(root.resolve()) for root in protected):
        raise ValueError("Evidence directory must be outside Hermes and project source")
    return destination


def generate_candidate(design: Design) -> object:
    generation = generate_graph(design.spec, state_type=design.state_type, bindings=design.bindings)
    if generation.candidate is None:
        raise ValueError(f"Generation failed: {generation.findings}")
    return generation.candidate


def check_design(raw: object, *, evidence_dir: Path,
                 candidate_factory: Callable[[Design], object] = generate_candidate,
                 protected_roots: tuple[Path, ...] = ()) -> dict[str, Any]:
    """Generate/check fresh evidence; candidate injection is trusted Python only."""
    design = author_design(raw)
    destination = validate_evidence_root(evidence_dir, protected_roots=protected_roots)
    candidate = candidate_factory(design)
    report = check_conformance(design.spec, candidate, state_type=design.state_type,
                               bindings=design.bindings, cases=design.cases,
                               evidence_dir=destination, protected_roots=protected_roots)
    return {
        "passed": report.passed, "cases": list(design.cases),
        "completed_cases": list(report.completed),
        "findings": [{"code": item.code, "path": list(item.path), "message": item.message}
                     for item in report.findings],
        "evidence": [{"name": item.case, "reference_log": str(item.reference_log),
                      "candidate_log": str(item.candidate_log)} for item in report.evidence],
    }
