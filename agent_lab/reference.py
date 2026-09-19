"""Offline, in-memory Transform/Decision reference target; not conformance."""
from collections.abc import Callable, Mapping
from dataclasses import dataclass
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


@dataclass(frozen=True)
class ReferencePlan(Generic[S]):
    spec: WorkflowSpec
    state_type: type[S]
    bindings: Mapping[str, Callable[[S], object]]

    def _snapshot(self, value: object) -> S:
        if type(value) is not self.state_type:
            raise ValueError("State must be an instance of the declared type")
        assert isinstance(value, BaseModel)
        return self.state_type.model_validate(
            deepcopy(value.model_dump(mode="python", round_trip=True, warnings="error")), strict=True,
        )

    def run(self, initial: S, *, run_id: str, log: RunLog) -> ReferenceResult[S]:
        """Fresh single-pass execution; each invocation reserves one step."""
        try:
            state = self._snapshot(initial)
        except Exception as exc:
            raise ValueError("Invalid initial state") from exc
        try:
            with log.fresh_run(run_id):
                return self._execute(state, run_id=run_id, log=log)
        except OSError as exc:
            raise AuditError("Reference audit I/O failed; execution stopped") from exc

    def _execute(self, initial: S, *, run_id: str, log: RunLog) -> ReferenceResult[S]:
        state = initial
        budget = Budget(max_steps=self.spec.budget)
        accounting = RunAccounting()
        nodes = {node.id: node for node in self.spec.nodes}
        routes = {(edge.source, edge.outcome): edge.target for edge in self.spec.edges
                  if isinstance(edge, Route)}
        current = self.spec.entry
        while current not in self.spec.terminals:
            node = nodes[current]
            label: object = None
            failure = None
            try:
                budget = accounting.reserve(run_id, budget)
            except BudgetExceeded:
                failure = "budget_exhausted"
            try:
                if failure:
                    raise BudgetExceeded("Invocation refused")
                snapshot = self._snapshot(state)
                next_state = state
                if isinstance(node, TransformNode):
                    result = self.bindings[node.operation](snapshot)
                    if not isinstance(result, TransformResult):
                        raise ValueError("Expected TransformResult")
                    next_state, label = self._snapshot(result.state), result.outcome
                elif isinstance(node, DecisionNode):
                    label = self.bindings[node.value](snapshot)
                else:
                    raise ValueError("Unsupported node")
                if type(label) is not str or label not in node.route_labels:
                    raise ValueError("Expected declared route label")
                target = routes[(current, label)]
                state = next_state
            except BudgetExceeded:
                if failure != "budget_exhausted":
                    # A binding raising BudgetExceeded is a binding failure,
                    # not evidence that the reference reservation was refused.
                    label, target, failure = None, "FAILED_VALIDATION", "invalid_binding_result"
                else:
                    label, target = None, "FAILED_BUDGET"
            except Exception:
                # Trusted local bindings may raise any ordinary exception. Keep
                # audit I/O outside this boundary; never translate it to success.
                label, target, failure = None, "FAILED_VALIDATION", "invalid_binding_result"
            log.append_next(RunEvent(
                run_id, 0, current, node.kind, label,
                target if target in self.spec.terminals else None,
                {"target": target, "failure": failure,
                 "used_steps": budget.used_steps, "max_steps": budget.max_steps},
            ))
            current = target
        return ReferenceResult(state, current, budget.used_steps,
                               tuple(event for event in log.read() if event.run_id == run_id))


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
