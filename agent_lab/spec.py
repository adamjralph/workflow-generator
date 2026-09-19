"""In-memory workflow declarations and structural validation, not conformance.

No execution, persistence or on-disk format is defined by this module.
"""

from dataclasses import dataclass
from graphlib import CycleError, TopologicalSorter
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError

Name = Annotated[str, StringConstraints(min_length=1, pattern=r"\S")]
PositiveSteps = Annotated[int, Field(gt=0)]


class Declaration(BaseModel):
    """Strict, immutable declarations, including nested instances at admission."""

    model_config = ConfigDict(
        strict=True, frozen=True, extra="forbid", revalidate_instances="always",
    )


class Node(Declaration):
    id: Name

    @property
    def route_labels(self) -> tuple[str, ...]:
        raise NotImplementedError


class TransformNode(Node):
    kind: Literal["transform"] = "transform"
    operation: Name
    outcomes: Annotated[tuple[Name, ...], Field(min_length=1)] = ("done",)

    @property
    def route_labels(self) -> tuple[str, ...]:
        return self.outcomes


class JudgmentNode(Node):
    kind: Literal["judgment"] = "judgment"
    options: Annotated[tuple[Name, ...], Field(min_length=1)]

    @property
    def route_labels(self) -> tuple[str, ...]:
        return self.options


class DecisionNode(Node):
    kind: Literal["decision"] = "decision"
    value: Name
    cases: Annotated[tuple[Name, ...], Field(min_length=1)]

    @property
    def route_labels(self) -> tuple[str, ...]:
        return self.cases


class GateNode(Node):
    kind: Literal["gate"] = "gate"

    @property
    def route_labels(self) -> tuple[str, ...]:
        return ("approved", "rejected", "pending", "invalid")


class LoopNode(Node):
    kind: Literal["loop"] = "loop"
    max_iterations: PositiveSteps
    exit_predicate: Name

    @property
    def route_labels(self) -> tuple[str, ...]:
        return ("repeat", "exit", "exhausted")


SpecNode = Annotated[
    TransformNode | JudgmentNode | DecisionNode | GateNode | LoopNode,
    Field(discriminator="kind"),
]


class Route(Declaration):
    kind: Literal["route"] = "route"
    source: Name
    outcome: Name
    target: Name

    @property
    def targets(self) -> tuple[str, ...]:
        return (self.target,)


class Fork(Declaration):
    kind: Literal["fork"] = "fork"
    source: Name
    outcome: Name
    branches: Annotated[tuple[Name, ...], Field(min_length=2)]
    join: Name

    @property
    def targets(self) -> tuple[str, ...]:
        return self.branches


SpecEdge = Annotated[Route | Fork, Field(discriminator="kind")]


class WorkflowSpec(Declaration):
    entry: Name
    nodes: tuple[SpecNode, ...]
    edges: tuple[SpecEdge, ...]
    budget: PositiveSteps
    terminals: Annotated[tuple[Name, ...], Field(min_length=1)]


FindingCode = Literal[
    "invalid_declaration", "duplicate_identity", "missing_entry", "unknown_reference",
    "duplicate_outcome", "unknown_outcome", "missing_route", "conflicting_route",
    "invalid_fork", "invalid_join", "unbounded_cycle",
]


@dataclass(frozen=True)
class Finding:
    code: FindingCode
    path: tuple[str | int, ...]
    message: str


@dataclass(frozen=True)
class SpecValidation:
    spec: WorkflowSpec | None
    findings: tuple[Finding, ...] = ()

    def __post_init__(self) -> None:
        if (self.spec is None) == (not self.findings):
            raise ValueError("Validation returns either a spec or nonempty findings")

    @property
    def valid(self) -> bool:
        return self.spec is not None


def validate_spec(candidate: object) -> SpecValidation:
    """Admit Python declarations; malformed input is returned as typed findings."""
    try:
        spec = WorkflowSpec.model_validate(candidate)
    except ValidationError as exc:
        return SpecValidation(None, tuple(
            Finding("invalid_declaration", error["loc"], error["msg"])
            for error in exc.errors(include_url=False)
        ))
    findings = _references(spec)
    if not findings:
        findings.extend(_routing(spec))
    if not findings:
        findings.extend(_cycles(spec))
    if not findings:
        findings.extend(_joins(spec))
    return SpecValidation(None, tuple(findings)) if findings else SpecValidation(spec)


def _references(spec: WorkflowSpec) -> list[Finding]:
    findings: list[Finding] = []
    names: set[str] = set()
    for i, node in enumerate(spec.nodes):
        if node.id in names:
            findings.append(Finding("duplicate_identity", ("nodes", i, "id"),
                                    f"Duplicate identity: {node.id}"))
        names.add(node.id)
    if spec.entry not in names:
        findings.append(Finding("missing_entry", ("entry",), "Entry must name a node"))
    for i, terminal in enumerate(spec.terminals):
        if terminal in names:
            findings.append(Finding("duplicate_identity", ("terminals", i),
                                    f"Duplicate identity: {terminal}"))
        names.add(terminal)
    node_ids = {node.id for node in spec.nodes}
    for i, edge in enumerate(spec.edges):
        if edge.source not in node_ids:
            findings.append(Finding("unknown_reference", ("edges", i, "source"),
                                    "Source must name a node"))
        if isinstance(edge, Route):
            if edge.target not in names:
                findings.append(Finding("unknown_reference", ("edges", i, "target"),
                                        "Target must name a node or terminal"))
        else:
            for j, target in enumerate(edge.branches):
                if target not in node_ids:
                    findings.append(Finding("unknown_reference", ("edges", i, "branches", j),
                                            "Branch must name a node"))
            if edge.join not in node_ids:
                findings.append(Finding("unknown_reference", ("edges", i, "join"),
                                        "Join must name a node"))
            if (len(set(edge.branches)) != len(edge.branches)
                    or edge.join in edge.branches or edge.source == edge.join):
                findings.append(Finding("invalid_fork", ("edges", i),
                                        "Fork needs distinct branches and a separate join"))
    return findings


def _cycles(spec: WorkflowSpec) -> list[Finding]:
    # Each traversal of a Loop's repeat edge consumes its declared finite bound.
    # Removing precisely those edges must leave a DAG: merely visiting a Loop
    # somewhere in a strongly connected component is not sufficient.
    loops = {node.id for node in spec.nodes if isinstance(node, LoopNode)}
    graph: dict[str, list[str]] = {node.id: [] for node in spec.nodes}
    unbounded = [(i, edge) for i, edge in enumerate(spec.edges)
                 if edge.source not in loops or edge.outcome != "repeat"]
    for _, edge in unbounded:
        graph[edge.source].extend(edge.targets)
    try:
        tuple(TopologicalSorter(graph).static_order())
    except CycleError as exc:
        cycle = set(exc.args[1])
        index = next(i for i, edge in unbounded
                     if edge.source in cycle and cycle.intersection(edge.targets))
        return [Finding("unbounded_cycle", ("edges", index),
                        "A cycle remains after removing bounded Loop repeat edges")]
    return []


def _joins(spec: WorkflowSpec) -> list[Finding]:
    graph: dict[str, set[str]] = {name: set() for name in spec.terminals}
    graph.update({node.id: set() for node in spec.nodes})
    for edge in spec.edges:
        graph[edge.source].update(edge.targets)
    findings: list[Finding] = []
    for i, edge in enumerate(spec.edges):
        if not isinstance(edge, Fork):
            continue
        # Stop the walk at the join. Every pre-join declaration must be able to
        # converge there, and none may terminate the branch early. Loop bounds
        # are checked separately; predicates are not executed here.
        pending = list(edge.branches)
        region: set[str] = set()
        while pending:
            current = pending.pop()
            if current == edge.join or current in region:
                continue
            region.add(current)
            pending.extend(graph[current])
        converges = {edge.join}
        while True:
            additions = {node for node in region - converges
                         if graph[node] & converges}
            if not additions:
                break
            converges.update(additions)
        if not region <= converges:
            findings.append(Finding("invalid_join", ("edges", i, "join"),
                                    "Every branch path must converge before terminating"))
    return findings


def _routing(spec: WorkflowSpec) -> list[Finding]:
    findings: list[Finding] = []
    nodes = {node.id: node for node in spec.nodes}
    routes: set[tuple[str, str]] = set()
    for i, edge in enumerate(spec.edges):
        key = (edge.source, edge.outcome)
        if key in routes:
            findings.append(Finding("conflicting_route", ("edges", i),
                                    "An outcome must have exactly one dispatch"))
        routes.add(key)
        if edge.outcome not in nodes[edge.source].route_labels:
            findings.append(Finding("unknown_outcome", ("edges", i, "outcome"),
                                    "Outcome is not declared by the source node"))
    for i, node in enumerate(spec.nodes):
        if len(set(node.route_labels)) != len(node.route_labels):
            findings.append(Finding("duplicate_outcome", ("nodes", i),
                                    "Outcome labels must be distinct"))
        for label in node.route_labels:
            if (node.id, label) not in routes:
                findings.append(Finding("missing_route", ("nodes", i),
                                        f"No dispatch for outcome {label}"))
    return findings
