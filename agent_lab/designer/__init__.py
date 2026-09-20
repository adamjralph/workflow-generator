"""Bounded questionnaire front door; JSON is private UI transport, not a spec format."""
import os
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from agent_lab.conformance import check_conformance
from agent_lab.generation import generate_graph
from agent_lab.reference import TransformResult
from agent_lab.spec import DecisionNode, Route, TransformNode, WorkflowSpec


class StrictAnswer(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class ReceiveAnswer(StrictAnswer):
    id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z][A-Za-z0-9_-]*$")
    operation: Literal["receive"]
    done: str


class AdjustmentAnswer(StrictAnswer):
    id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z][A-Za-z0-9_-]*$")
    operation: Literal["adjust"]
    adjustment: int
    done: str

    @field_validator("adjustment")
    @classmethod
    def catalog_adjustment(cls, value: int) -> int:
        if value not in (-10, 10):
            raise ValueError("Adjustment must be -10 or +10")
        return value


class DecisionAnswer(StrictAnswer):
    id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z][A-Za-z0-9_-]*$")
    operation: Literal["compare"]
    threshold: int
    below: str
    at_or_above: str

    @field_validator("threshold")
    @classmethod
    def catalog_threshold(cls, value: int) -> int:
        if value not in (10, 50, 100):
            raise ValueError("Threshold must be 10, 50 or 100")
        return value


NodeAnswer = Annotated[ReceiveAnswer | AdjustmentAnswer | DecisionAnswer,
                       Field(discriminator="operation")]


class Answers(StrictAnswer):
    nodes: tuple[NodeAnswer, ...] = Field(min_length=1, max_length=6)

    @field_validator("nodes", mode="before")
    @classmethod
    def freeze_nodes(cls, value: object) -> object:
        return tuple(value) if isinstance(value, list) else value


class RequestState(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    score: int


@dataclass(frozen=True)
class CasePath:
    routes: tuple[tuple[str, str, str], ...]
    lower: int | None
    upper: int | None

    @property
    def feasible(self) -> bool:
        return self.lower is None or self.upper is None or self.lower <= self.upper


@dataclass(frozen=True)
class Design:
    answers: Answers
    spec: WorkflowSpec
    bindings: Mapping[str, Callable[[RequestState], object]]
    cases: Mapping[str, RequestState]
    paths: tuple[CasePath, ...]
    state_type: type[RequestState] = RequestState

    def view(self) -> dict[str, Any]:
        labels = {node.id: ("Receive request" if isinstance(node, ReceiveAnswer) else
                           f"Score {node.adjustment:+d}" if isinstance(node, AdjustmentAnswer)
                           else f"Score >= {node.threshold}?") for node in self.answers.nodes}
        return {
            "answers": self.answers.model_dump(),
            "nodes": [{"id": node.id, "kind": node.kind, "label": labels[node.id]}
                      for node in self.spec.nodes],
            "edges": [{"source": edge.source, "outcome": edge.outcome, "target": edge.target}
                      for edge in self.spec.edges if isinstance(edge, Route)],
            "terminals": list(self.spec.terminals), "budget": self.spec.budget,
            "cases": [{"name": name, "score": state.score} for name, state in self.cases.items()],
            "scope": (f"{len(self.cases)} deterministic offline inputs from "
                      f"{sum(path.feasible for path in self.paths)} feasible / {len(self.paths)} "
                      "syntactic paths. Finite interval endpoints and representatives only; "
                      "not exhaustive correctness."),
            "infeasible_routes": [list(path.routes) for path in self.paths if not path.feasible],
        }


def _routes(node: NodeAnswer) -> tuple[tuple[str, str], ...]:
    if isinstance(node, DecisionAnswer):
        return (("below", node.below), ("at_or_above", node.at_or_above))
    return (("done", node.done),)


def _paths(answers: Answers) -> tuple[str, tuple[CasePath, ...]]:
    """Validate all graph declarations, then enumerate bounded acyclic paths."""
    nodes = {node.id: node for node in answers.nodes}
    terminals = {"ACCEPTED", "REVIEW", "FAILED_VALIDATION", "FAILED_BUDGET"}
    if len(nodes) != len(answers.nodes) or nodes.keys() & terminals:
        raise ValueError("Node identities must be unique and distinct from terminals")
    entries = [node.id for node in answers.nodes if isinstance(node, ReceiveAnswer)]
    if len(entries) != 1:
        raise ValueError("Exactly one receive Transform is required as entry")
    if sum(isinstance(node, DecisionAnswer) for node in answers.nodes) > 2:
        raise ValueError("At most two Decisions are supported")
    for node in answers.nodes:
        for label, target in _routes(node):
            if target not in nodes and target not in ("ACCEPTED", "REVIEW"):
                raise ValueError(f"Missing destination: {node.id}.{label} -> {target!r}")
    visited: set[str] = set()
    active: set[str] = set()

    def validate(identity: str) -> None:
        if identity in active:
            raise ValueError(f"Cycle at {identity}; every path must terminate")
        if identity in visited:
            return
        visited.add(identity)
        active.add(identity)
        for _, target in _routes(nodes[identity]):
            if target in nodes:
                validate(target)
        active.remove(identity)

    validate(entries[0])
    if visited != nodes.keys():
        raise ValueError(f"Unreachable nodes: {sorted(nodes.keys() - visited)}")
    paths: list[CasePath] = []

    def walk(identity: str, offset: int, lower: int | None, upper: int | None,
             routes: tuple[tuple[str, str, str], ...]) -> None:
        if identity not in nodes:
            paths.append(CasePath(routes, lower, upper))
            return
        node = nodes[identity]
        if isinstance(node, AdjustmentAnswer):
            offset += node.adjustment
        for outcome, target in _routes(node):
            lo, hi = lower, upper
            if isinstance(node, DecisionAnswer):
                boundary = node.threshold - offset
                if outcome == "below":
                    hi = boundary - 1 if hi is None else min(hi, boundary - 1)
                else:
                    lo = boundary if lo is None else max(lo, boundary)
            walk(target, offset, lo, hi, routes + ((identity, outcome, target),))

    walk(entries[0], 0, None, None, ())
    return entries[0], tuple(paths)


def _case_inputs(paths: tuple[CasePath, ...]) -> tuple[int, ...]:
    inputs: set[int] = set()
    for path in paths:
        if not path.feasible:
            continue
        lo, hi = path.lower, path.upper
        if lo is None and hi is None:
            inputs.add(0)
        elif lo is None:
            assert hi is not None
            inputs.update((hi - 1, hi))
        elif hi is None:
            inputs.update((lo, lo + 1))
        else:
            inputs.update((lo, hi))
            if hi - lo > 1:
                inputs.add((lo + hi) // 2)
    return tuple(sorted(inputs))


def _adjust(amount: int) -> Callable[[RequestState], object]:
    return lambda state: TransformResult(RequestState(score=state.score + amount), "done")


def _compare(threshold: int) -> Callable[[RequestState], object]:
    return lambda state: "at_or_above" if state.score >= threshold else "below"


def author_design(raw: object) -> Design:
    answers = Answers.model_validate(raw)
    entry, paths = _paths(answers)
    nodes: list[TransformNode | DecisionNode] = []
    edges: list[Route] = []
    bindings: dict[str, Callable[[RequestState], object]] = {}
    for node in answers.nodes:
        if isinstance(node, DecisionAnswer):
            key = f"score_at_least_{node.threshold}"
            nodes.append(DecisionNode(id=node.id, value=key, cases=("below", "at_or_above")))
            bindings[key] = _compare(node.threshold)
        else:
            key = "receive_request" if isinstance(node, ReceiveAnswer) else f"adjust_{node.adjustment}"
            nodes.append(TransformNode(id=node.id, operation=key))
            bindings[key] = _adjust(0 if isinstance(node, ReceiveAnswer) else node.adjustment)
        edges.extend(Route(source=node.id, outcome=label, target=target)
                     for label, target in _routes(node))
    spec = WorkflowSpec(entry=entry, budget=max(len(path.routes) for path in paths if path.feasible),
                        nodes=tuple(nodes), edges=tuple(edges),
                        terminals=("ACCEPTED", "REVIEW", "FAILED_VALIDATION", "FAILED_BUDGET"))
    cases = {f"score_{score}": RequestState(score=score) for score in _case_inputs(paths)}
    return Design(answers, spec, MappingProxyType(bindings), MappingProxyType(cases), paths)


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
