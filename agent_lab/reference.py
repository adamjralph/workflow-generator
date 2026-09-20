"""Offline, in-memory Transform/Decision reference target; not conformance."""
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from copy import deepcopy
from types import MappingProxyType
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel

from .accounting import RunAccounting
from .runlog import RunEvent, RunLog
from .spec import DecisionNode, Finding, Route, TransformNode, WorkflowSpec, validate_spec
from .state import Budget, BudgetExceeded

S = TypeVar("S", bound=BaseModel)


class AuditError(RuntimeError):
    """Audit I/O failed. No claim that a terminal was persisted is made."""


@dataclass(frozen=True)
class TransformResult(Generic[S]):
    state: S
    outcome: str


@dataclass(frozen=True)
class ReferenceResult(Generic[S]):
    state: S
    terminal: str
    used_steps: int
    trace: tuple[RunEvent, ...]


@dataclass(frozen=True)
class CompileFinding:
    code: Literal["unsupported_node", "unsupported_edge", "unbound_reference",
                  "missing_safety_terminal", "invalid_state_type"]
    path: tuple[str | int, ...]
    message: str


@dataclass(frozen=True)
class Compilation(Generic[S]):
    plan: "ReferencePlan[S] | None"
    findings: tuple[Finding | CompileFinding, ...] = ()


def _snapshot(state_type: type[S], value: object) -> S:
    if type(value) is not state_type:
        raise ValueError("State must be an instance of the declared type")
    assert isinstance(value, BaseModel)
    return state_type.model_validate(
        deepcopy(value.model_dump(mode="python", round_trip=True, warnings="error")), strict=True,
    )


def _initial_snapshot(state_type: type[S], value: object) -> S:
    try:
        return _snapshot(state_type, value)
    except Exception as exc:
        raise ValueError("Invalid initial state") from exc


@dataclass
class _Execution(Generic[S]):
    """Shared invocation/audit mechanics, deliberately no scheduling loop."""

    state: S
    state_type: type[S]
    budget: Budget
    run_id: str
    log: RunLog
    accounting: RunAccounting = field(default_factory=RunAccounting)

    def invoke(self, node: TransformNode | DecisionNode,
               binding: Callable[[S], object], routes: Mapping[str, str],
               terminals: tuple[str, ...]) -> str:
        selected: str | None = None
        failure = None
        try:
            self.budget = self.accounting.reserve(self.run_id, self.budget)
        except BudgetExceeded:
            target, failure = "FAILED_BUDGET", "budget_exhausted"
        else:
            try:
                snapshot = _snapshot(self.state_type, self.state)
                next_state = self.state
                label: object
                result = binding(snapshot)
                if isinstance(node, TransformNode):
                    if not isinstance(result, TransformResult):
                        raise ValueError("Expected TransformResult")
                    next_state, label = _snapshot(self.state_type, result.state), result.outcome
                else:
                    label = result
                if type(label) is not str or label not in node.route_labels:
                    raise ValueError("Expected declared route label")
                target = routes[label]
                self.state, selected = next_state, label
            except Exception:
                # Binding-raised BudgetExceeded is not reservation refusal.
                # Audit I/O remains outside this boundary.
                target, failure = "FAILED_VALIDATION", "invalid_binding_result"
        self.log.append_next(RunEvent(
            self.run_id, 0, node.id, node.kind, selected,
            target if target in terminals else None,
            {"target": target, "failure": failure,
             "used_steps": self.budget.used_steps, "max_steps": self.budget.max_steps},
        ))
        return target

    def result(self, terminal: str) -> ReferenceResult[S]:
        return ReferenceResult(self.state, terminal, self.budget.used_steps,
                               tuple(event for event in self.log.read() if event.run_id == self.run_id))


@dataclass(frozen=True)
class ReferencePlan(Generic[S]):
    spec: WorkflowSpec
    state_type: type[S]
    bindings: Mapping[str, Callable[[S], object]]

    def run(self, initial: S, *, run_id: str, log: RunLog) -> ReferenceResult[S]:
        """Fresh single-pass execution; each invocation reserves one step."""
        state = _initial_snapshot(self.state_type, initial)
        try:
            with log.fresh_run(run_id):
                return self._execute(state, run_id=run_id, log=log)
        except OSError as exc:
            raise AuditError("Reference audit I/O failed; execution stopped") from exc

    def _execute(self, initial: S, *, run_id: str, log: RunLog) -> ReferenceResult[S]:
        execution = _Execution(initial, self.state_type, Budget(max_steps=self.spec.budget), run_id, log)
        nodes = {node.id: node for node in self.spec.nodes}
        routes = {(edge.source, edge.outcome): edge.target for edge in self.spec.edges
                  if isinstance(edge, Route)}
        current = self.spec.entry
        while current not in self.spec.terminals:
            node = nodes[current]
            assert isinstance(node, (TransformNode, DecisionNode))
            key = node.operation if isinstance(node, TransformNode) else node.value
            current = execution.invoke(
                node, self.bindings[key],
                {label: routes[(current, label)] for label in node.route_labels},
                self.spec.terminals,
            )
        return execution.result(current)


def compile_reference(candidate: object, *, state_type: type[S],
                      bindings: Mapping[str, Callable[[S], object]]) -> Compilation[S]:
    """References are opaque explicit keys, never import paths or expressions."""
    admitted = validate_spec(candidate)
    if admitted.spec is None:
        return Compilation(None, admitted.findings)
    spec = admitted.spec
    findings: list[Finding | CompileFinding] = []
    resolved = dict(bindings)
    if not isinstance(state_type, type) or not issubclass(state_type, BaseModel) or not state_type.model_config.get("frozen"):
        findings.append(CompileFinding("invalid_state_type", ("state_type",), "State must be a frozen Pydantic model"))
    for index, node in enumerate(spec.nodes):
        if not isinstance(node, (TransformNode, DecisionNode)):
            findings.append(CompileFinding("unsupported_node", ("nodes", index), node.kind))
            continue
        field = "operation" if isinstance(node, TransformNode) else "value"
        key = node.operation if isinstance(node, TransformNode) else node.value
        if key not in resolved or not callable(resolved[key]):
            findings.append(CompileFinding("unbound_reference", ("nodes", index, field), key))
    for index, edge in enumerate(spec.edges):
        if not isinstance(edge, Route):
            findings.append(CompileFinding("unsupported_edge", ("edges", index), edge.kind))
    for terminal in ("FAILED_VALIDATION", "FAILED_BUDGET"):
        if terminal not in spec.terminals:
            findings.append(CompileFinding("missing_safety_terminal", ("terminals", terminal), terminal))
    if findings:
        return Compilation(None, tuple(findings))
    return Compilation(ReferencePlan(spec.model_copy(deep=True), state_type, MappingProxyType(resolved)))
