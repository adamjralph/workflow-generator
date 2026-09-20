"""Owned pydantic-graph target for Transform/Decision/Intervention Judgment/Loop + Route.

No persistent bundle and no conformance verdict. Configuration is the executable
input, not a separately stored spec manifest; a fresh framework graph is built
from it per run so mutable framework internals never escape to callers.
"""
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Generic, Literal, NamedTuple

from pydantic_graph import GraphBuilder, StepContext

from .reference import (
    S, AuditError, CompileFinding, JudgmentBinding, ReferenceResult, _Execution, _initial_snapshot,
    compile_reference,
)
from .runlog import RunLog
from .spec import DecisionNode, Finding, JudgmentNode, LoopNode, Route, TransformNode, WorkflowSpec
from .state import Budget


class _Node(NamedTuple):
    identity: str
    kind: Literal["transform", "decision", "judgment", "loop"]
    reference: str
    labels: tuple[str, ...]
    routes: tuple[tuple[str, str], ...]

    max_iterations: int | None = None

    def declaration(self) -> TransformNode | DecisionNode | JudgmentNode | LoopNode:
        if self.kind == "loop":
            assert self.max_iterations is not None
            return LoopNode(id=self.identity, exit_predicate=self.reference,
                            max_iterations=self.max_iterations)
        if self.kind == "judgment":
            return JudgmentNode(id=self.identity, options=self.labels)
        if self.kind == "transform":
            return TransformNode(id=self.identity, operation=self.reference, outcomes=self.labels)
        return DecisionNode(id=self.identity, value=self.reference, cases=self.labels)


class UnsupportedCandidate(ValueError):
    """Candidate executable methods/configuration are not the owned target."""


@dataclass(frozen=True, slots=True, init=False)
class GraphCandidate(Generic[S]):
    """Generate via generate_graph; run with a fresh run identity in a RunLog."""

    state_type: type[S]
    _entry: str
    _nodes: tuple[_Node, ...]
    _terminals: tuple[str, ...]
    _budget: int
    _bindings: Mapping[str, Callable[[S], object]]
    _judgments: Mapping[str, JudgmentBinding[S]]
    _seal: tuple[object, ...] = field(repr=False)

    def inspect_structure(self) -> WorkflowSpec:
        """Reconstruct execution configuration; reject unsupported mutations.

        This is an integrity boundary for the owned target, not a Python sandbox.
        Use generate_graph again to supply changed structure or bindings.
        """
        _assert_supported(self)
        return WorkflowSpec(
            entry=self._entry, budget=self._budget, terminals=self._terminals,
            nodes=tuple(node.declaration() for node in self._nodes),
            edges=tuple(Route(source=node.identity, outcome=label, target=target)
                        for node in self._nodes for label, target in node.routes),
        )

    def run(self, initial: S, *, run_id: str, log: RunLog) -> ReferenceResult[S]:
        _assert_supported(self)
        state = _initial_snapshot(self.state_type, initial)
        execution = _Execution(state, self.state_type, Budget(max_steps=self._budget), run_id, log)
        builder = GraphBuilder(
            state_type=_Execution, deps_type=type(None), input_type=type(None), output_type=str,
        )

        def make_step(node: _Node):
            async def invoke(ctx: StepContext) -> str:
                binding = (self._judgments[node.identity] if node.kind == "judgment"
                           else self._bindings[node.reference])
                return execution.invoke(node.declaration(), binding,
                                        dict(node.routes), self._terminals)
            return invoke

        steps = {node.identity: builder.step(make_step(node), node_id=f"node_{i}")
                 for i, node in enumerate(self._nodes)}
        builder.add(builder.edge_from(builder.start_node).to(steps[self._entry]))
        for i, node in enumerate(self._nodes):
            decision = builder.decision(node_id=f"route_{i}")
            targets = dict.fromkeys([target for _, target in node.routes] +
                                    ["FAILED_VALIDATION", "FAILED_BUDGET"])
            def matches_target(target: str) -> Callable[[str], bool]:
                return lambda value: value == target

            for target in targets:
                branch = builder.match(str, matches=matches_target(target))
                destination = builder.end_node if target in self._terminals else steps[target]
                decision = decision.branch(branch.to(destination))
            builder.add(builder.edge_from(steps[node.identity]).to(decision))
        # Admission already validates every route/cycle. Unlike the framework's
        # default policy our contract intentionally permits unreachable nodes.
        graph = builder.build(validate_graph_structure=False)
        try:
            with log.fresh_run(run_id):
                terminal = graph.run_sync(state=execution, deps=None, inputs=None)
                return execution.result(terminal)
        except OSError as exc:
            raise AuditError("Graph audit I/O failed; execution stopped") from exc


_CONFIG_FIELDS = ("state_type", "_entry", "_nodes", "_terminals", "_budget", "_bindings", "_judgments")
_METHODS = ((GraphCandidate, "run", GraphCandidate.run, GraphCandidate.run.__code__),
            (GraphCandidate, "inspect_structure", GraphCandidate.inspect_structure,
             GraphCandidate.inspect_structure.__code__),
            (_Node, "declaration", _Node.declaration, _Node.declaration.__code__))


def _assert_supported(candidate: GraphCandidate[S]) -> None:
    try:
        intact = (type(candidate) is GraphCandidate and
                  len(candidate._seal) == len(_CONFIG_FIELDS) and
                  all(getattr(candidate, name) is original
                      for name, original in zip(_CONFIG_FIELDS, candidate._seal)) and
                  all(getattr(cls, name) is method and method.__code__ is code
                      for cls, name, method, code in _METHODS))
    except AttributeError:
        intact = False
    if not intact:
        raise UnsupportedCandidate("Unsupported candidate executable mutation or construction")


@dataclass(frozen=True)
class Generation(Generic[S]):
    candidate: GraphCandidate[S] | None
    findings: tuple[Finding | CompileFinding, ...] = ()


def generate_graph(candidate: object, *, state_type: type[S],
                   bindings: Mapping[str, Callable[[S], object]],
                   judgments: Mapping[str, JudgmentBinding[S]] | None = None) -> Generation[S]:
    """Admit all declarations without invoking trusted local bindings."""
    admitted = compile_reference(candidate, state_type=state_type, bindings=bindings, judgments=judgments)
    if admitted.plan is None:
        return Generation(None, admitted.findings)
    plan = admitted.plan
    nodes = []
    for node in plan.spec.nodes:
        assert isinstance(node, (TransformNode, DecisionNode, JudgmentNode, LoopNode))
        nodes.append(_Node(
            node.id, node.kind,
            (node.operation if isinstance(node, TransformNode) else
             node.value if isinstance(node, DecisionNode) else
             node.exit_predicate if isinstance(node, LoopNode) else node.id),
            node.route_labels,
            tuple((edge.outcome, edge.target) for edge in plan.spec.edges
                  if isinstance(edge, Route) and edge.source == node.id),
            node.max_iterations if isinstance(node, LoopNode) else None,
        ))
    result = object.__new__(GraphCandidate)
    owned = (state_type, plan.spec.entry, tuple(nodes), plan.spec.terminals,
             plan.spec.budget, MappingProxyType(dict(plan.bindings)),
             MappingProxyType(dict(plan.judgments)))
    for name, value in zip(_CONFIG_FIELDS, owned):
        object.__setattr__(result, name, value)
    object.__setattr__(result, "_seal", owned)
    return Generation(result)
