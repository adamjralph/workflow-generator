"""In-memory Transform/Decision/Intervention Judgment/Loop reference; not conformance."""
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from copy import deepcopy
from graphlib import TopologicalSorter
import hashlib
from types import MappingProxyType
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel

from .accounting import RunAccounting
from .judgment import JudgmentSource
from .model_operation import ModelOperation, validate_request, validate_response
from .runlog import RunEvent, RunLog
from .spec import (DecisionNode, Finding, Fork, JudgmentNode, LoopNode, Route,
                   TransformNode, WorkflowSpec, branch_regions, validate_spec)
from .state import Budget, BudgetExceeded, Intervention, Judgment

S = TypeVar("S", bound=BaseModel)


class AuditError(RuntimeError):
    """Audit I/O failed. No claim that a terminal was persisted is made."""


@dataclass(frozen=True)
class JudgmentBinding(Generic[S]):
    """Explicit trusted source and deterministic assessment adapter, keyed by node ID."""

    source: JudgmentSource
    assessment: Callable[[S], str]


@dataclass(frozen=True)
class TransformResult(Generic[S]):
    state: S
    outcome: str


@dataclass(frozen=True)
class ReducerObservation:
    """Detached Python-mode inputs and admitted join result, not a purity proof."""
    join: str
    inputs: object
    output: object


@dataclass(frozen=True)
class ReferenceResult(Generic[S]):
    state: S
    terminal: str
    used_steps: int
    trace: tuple[RunEvent, ...]
    reducer_observations: tuple[ReducerObservation, ...] = ()


@dataclass(frozen=True)
class CompileFinding:
    code: Literal["unsupported_node", "unsupported_edge", "unbound_reference",
                  "missing_safety_terminal", "invalid_state_type", "unsupported_options",
                  "invalid_model_operation", "invalid_wave", "invalid_reducer", "invalid_wave_concurrency"]
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

    repeat_counts: dict[str, int] = field(default_factory=dict)
    reducer_observations: list[ReducerObservation] = field(default_factory=list)

    def invoke(self, node: TransformNode | DecisionNode | JudgmentNode | LoopNode,
               binding: Callable[[S], object] | JudgmentBinding[S], routes: Mapping[str, str],
               terminals: tuple[str, ...], observation: Mapping[str, object] | None = None) -> str:
        selected: str | None = None
        judgment: Judgment | None = None
        assessment_sha: str | None = None
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
                if isinstance(node, JudgmentNode):
                    assert isinstance(binding, JudgmentBinding)
                    assessment = binding.assessment(snapshot)
                    if type(assessment) is not str:
                        raise ValueError("Expected assessment text")
                    assessment_sha = hashlib.sha256(assessment.encode("utf-8")).hexdigest()
                    raw = binding.source.judge(assessment)
                    if not isinstance(raw, Judgment):
                        raise ValueError("Expected Judgment")
                    judgment = Judgment.model_validate(raw.model_dump(warnings=False), strict=True)
                    label = judgment.intervention.value
                else:
                    assert callable(binding)
                    result = binding(snapshot)
                    if isinstance(node, TransformNode):
                        if not isinstance(result, TransformResult):
                            raise ValueError("Expected TransformResult")
                        next_state, label = _snapshot(self.state_type, result.state), result.outcome
                    elif isinstance(node, LoopNode):
                        if type(result) is not bool:
                            raise ValueError("Expected strict boolean predicate")
                        count = self.repeat_counts.get(node.id, 0)
                        label = ("exit" if result else
                                 "repeat" if count < node.max_iterations else "exhausted")
                        if label == "repeat":
                            self.repeat_counts[node.id] = count + 1
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
            {**(observation or {}), "target": target, "failure": failure,
             "used_steps": self.budget.used_steps, "max_steps": self.budget.max_steps,
             **({"repeat_count": self.repeat_counts.get(node.id, 0),
                 "max_iterations": node.max_iterations}
                if isinstance(node, LoopNode) else {}),
             **({"judgment": judgment.model_dump(mode="json") if judgment else None,
                 "assessment_sha": assessment_sha}
                if isinstance(node, JudgmentNode) else {})},
        ))
        return target

    def record_model(self, node: TransformNode, target: str, selected: str | None,
                     failure: str | None, request_digest: str | None,
                     response_digest: str | None, terminals: tuple[str, ...],
                     observation: Mapping[str, object] | None = None) -> str:
        self.log.append_next(RunEvent(
            self.run_id, 0, node.id, node.kind, selected,
            target if target in terminals else None,
            {**(observation or {}), "target": target, "failure": failure, "used_steps": self.budget.used_steps,
             "max_steps": self.budget.max_steps, "operation": node.operation,
             "operation_version": node.operation_version, "schema_version": node.schema_version,
             "request_digest": request_digest, "response_digest": response_digest},
        ))
        return target

    def result(self, terminal: str) -> ReferenceResult[S]:
        return ReferenceResult(self.state, terminal, self.budget.used_steps,
                               tuple(event for event in self.log.read() if event.run_id == self.run_id),
                               tuple(self.reducer_observations))


@dataclass(frozen=True)
class ReferencePlan(Generic[S]):
    spec: WorkflowSpec
    state_type: type[S]
    bindings: Mapping[str, Callable[[S], object]]
    judgments: Mapping[str, JudgmentBinding[S]]
    model_operations: Mapping[str, ModelOperation[S]]
    reducers: Mapping[str, Callable[[S, tuple[S, ...]], TransformResult[S]]]
    wave_concurrency: int | None

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
        forks = {edge.join: edge for edge in self.spec.edges if isinstance(edge, Fork)}
        routes.update({(edge.source, edge.outcome): edge.join for edge in forks.values()})
        current = self.spec.entry
        while current not in self.spec.terminals:
            if current in forks:
                fork = forks[current]
                if not admit_wave(execution, self.spec, fork):
                    return execution.result("FAILED_BUDGET")
                items = []
                for index, branch in enumerate(fork.branches):
                    holder = branch_execution(execution)
                    target = branch
                    while target != fork.join and target not in self.spec.terminals:
                        declaration = nodes[target]
                        assert isinstance(declaration, (TransformNode, DecisionNode, LoopNode))
                        key = (declaration.operation if isinstance(declaration, TransformNode) else
                               declaration.exit_predicate if isinstance(declaration, LoopNode) else declaration.value)
                        target = holder.invoke(declaration, self.bindings[key],
                                               {label: routes[(target, label)]
                                                for label in declaration.route_labels}, self.spec.terminals)
                    items.append(BranchItem(index, holder.state,
                                            target if target in self.spec.terminals else None))
                current = finish_wave(execution, self.spec, fork, items, self.reducers[fork.join])
                continue
            node = nodes[current]
            assert isinstance(node, (TransformNode, DecisionNode, JudgmentNode, LoopNode))
            if isinstance(node, TransformNode) and node.model_operation:
                operation = self.model_operations[node.operation]
                selected = failure = request_digest = response_digest = None
                try:
                    execution.budget = execution.accounting.reserve(run_id, execution.budget)
                except BudgetExceeded:
                    target, failure = "FAILED_BUDGET", "budget_exhausted"
                else:
                    try:
                        snapshot = _snapshot(self.state_type, execution.state)
                        request = validate_request(operation, operation.prepare(snapshot))
                        request_digest = request.digest
                        response = validate_response(operation.source.invoke(request))
                        response_digest = hashlib.sha256(response.body.encode("utf-8")).hexdigest()
                        result = operation.apply(snapshot, response)
                        if not isinstance(result, TransformResult):
                            raise ValueError("Expected TransformResult")
                        next_state = _snapshot(self.state_type, result.state)
                        if type(result.outcome) is not str or result.outcome not in node.route_labels:
                            raise ValueError("Expected declared route label")
                        target = routes[(current, result.outcome)]
                        execution.state, selected = next_state, result.outcome
                    except Exception:
                        target, failure = "FAILED_VALIDATION", "invalid_binding_result"
                current = execution.record_model(node, target, selected, failure, request_digest,
                                                 response_digest, self.spec.terminals,
                                                 wave_observation(self.spec, node.id, self.wave_concurrency))
                continue
            binding: Callable[[S], object] | JudgmentBinding[S]
            if isinstance(node, JudgmentNode):
                binding = self.judgments[node.id]
            else:
                key = (node.operation if isinstance(node, TransformNode) else
                       node.exit_predicate if isinstance(node, LoopNode) else node.value)
                binding = self.bindings[key]
            current = execution.invoke(
                node, binding,
                {label: routes[(current, label)] for label in node.route_labels},
                self.spec.terminals, wave_observation(self.spec, node.id, self.wave_concurrency),
            )
        return execution.result(current)


def compile_reference(candidate: object, *, state_type: type[S],
                      bindings: Mapping[str, Callable[[S], object]],
                      judgments: Mapping[str, JudgmentBinding[S]] | None = None,
                      model_operations: Mapping[str, ModelOperation[S]] | None = None,
                      reducers: Mapping[str, Callable[[S, tuple[S, ...]], TransformResult[S]]] | None = None,
                      wave_concurrency: int | None = None) -> Compilation[S]:
    """References are opaque explicit keys, never import paths or expressions."""
    admitted = validate_spec(candidate)
    if admitted.spec is None:
        return Compilation(None, admitted.findings)
    spec = admitted.spec
    findings: list[Finding | CompileFinding] = []
    resolved = dict(bindings)
    resolved_judgments = dict(judgments or {})
    resolved_models = dict(model_operations or {})
    resolved_reducers = dict(reducers or {})
    joins = {edge.join for edge in spec.edges if isinstance(edge, Fork)}
    findings.extend(_wave_findings(spec, resolved_reducers, wave_concurrency))
    if not isinstance(state_type, type) or not issubclass(state_type, BaseModel) or not state_type.model_config.get("frozen"):
        findings.append(CompileFinding("invalid_state_type", ("state_type",), "State must be a frozen Pydantic model"))
    for index, node in enumerate(spec.nodes):
        if isinstance(node, JudgmentNode):
            if any(option not in {item.value for item in Intervention} for option in node.options):
                findings.append(CompileFinding("unsupported_options", ("nodes", index, "options"),
                                               "Executable Judgment requires Intervention options"))
            binding = resolved_judgments.get(node.id)
            if (not isinstance(binding, JudgmentBinding) or not callable(binding.assessment)
                    or not callable(getattr(binding.source, "judge", None))):
                findings.append(CompileFinding("unbound_reference", ("nodes", index, "id"), node.id))
            continue
        if not isinstance(node, (TransformNode, DecisionNode, LoopNode)):
            findings.append(CompileFinding("unsupported_node", ("nodes", index), node.kind))
            continue
        field = ("operation" if isinstance(node, TransformNode) else
                 "exit_predicate" if isinstance(node, LoopNode) else "value")
        key = (node.operation if isinstance(node, TransformNode) else
               node.exit_predicate if isinstance(node, LoopNode) else node.value)
        if isinstance(node, TransformNode):
            operation = resolved_models.get(key)
            if node.id in joins:
                if node.model_operation or operation is not None or node.operation_version or node.schema_version:
                    findings.append(CompileFinding("invalid_model_operation", ("nodes", index), key))
                continue
            if node.model_operation:
                if (key in resolved or key not in {"draft_linkedin", "review_linkedin"}
                        or not isinstance(operation, ModelOperation)
                        or operation.operation != key or operation.state_type is not state_type
                        or not node.operation_version or operation.version != node.operation_version
                        or not node.schema_version or operation.schema_version != node.schema_version
                        or not callable(operation.prepare) or not callable(operation.apply)
                        or getattr(operation.source, "mode", None) not in {"live", "fixture", "recorded"}
                        or not callable(getattr(operation.source, "invoke", None))):
                    findings.append(CompileFinding("invalid_model_operation", ("nodes", index), key))
                continue
            if operation is not None or node.operation_version is not None or node.schema_version is not None:
                findings.append(CompileFinding("invalid_model_operation", ("nodes", index), key))
        elif key in resolved_models:
            findings.append(CompileFinding("invalid_model_operation", ("nodes", index), key))
        if key not in resolved or not callable(resolved[key]):
            findings.append(CompileFinding("unbound_reference", ("nodes", index, field), key))

    for terminal in ("FAILED_VALIDATION", "FAILED_BUDGET"):
        if terminal not in spec.terminals:
            findings.append(CompileFinding("missing_safety_terminal", ("terminals", terminal), terminal))
    if findings:
        return Compilation(None, tuple(findings))
    return Compilation(ReferencePlan(spec.model_copy(deep=True), state_type, MappingProxyType(resolved),
                                     MappingProxyType(resolved_judgments), MappingProxyType(resolved_models),
                                     MappingProxyType(resolved_reducers), wave_concurrency))


def _wave_findings(spec: WorkflowSpec, reducers: Mapping[str, object],
                   concurrency: int | None) -> list[CompileFinding]:
    forks = tuple(edge for edge in spec.edges if isinstance(edge, Fork))
    findings: list[CompileFinding] = []
    if not forks:
        return findings
    joins = {fork.join for fork in forks}
    for key in reducers.keys() | joins:
        if key not in joins or not callable(reducers.get(key)):
            findings.append(CompileFinding("invalid_reducer", ("reducers", key), "Expected one callable per join"))
    if concurrency is not None and (type(concurrency) is not int or not 1 <= concurrency <= 16):
        findings.append(CompileFinding("invalid_wave_concurrency", ("wave_concurrency",), "Expected integer 1-16"))
    if len(forks) != 1:
        findings.append(CompileFinding("invalid_wave", ("edges",), "Only one wave is supported"))
    nodes = {node.id: node for node in spec.nodes}
    graph = {node.id: set[str]() for node in spec.nodes}
    for edge in spec.edges:
        graph[edge.source].update(edge.targets)

    def reachable(start: str) -> set[str]:
        seen: set[str] = set()
        pending = [start]
        while pending:
            current = pending.pop()
            if current not in seen:
                seen.add(current)
                pending.extend(graph.get(current, ()))
        return seen

    reached = reachable(spec.entry)
    for fork in forks:
        regions = branch_regions(spec, fork)
        region = set().union(*regions)
        loop_invalid = any(_invalid_branch_loop(spec, nodes, graph, branch_region)
                           for branch_region in regions)
        invalid = (
            not isinstance(nodes[fork.join], TransformNode)
            or not ({fork.source, fork.join} | region) <= reached
            or any(regions[i] & regions[j] for i in range(len(regions)) for j in range(i))
            or any(not isinstance(nodes.get(key), (TransformNode, DecisionNode, LoopNode))
                   or getattr(nodes.get(key), "model_operation", False) for key in region | {fork.join})
            or loop_invalid
            or any(other.source in region for other in forks)
            or sum(other.join == fork.join for other in forks) != 1
            or any(isinstance(node, LoopNode) and fork.source in reachable(node.id)
                   and node.id in reachable(fork.source) for node in spec.nodes)
            or spec.entry in region | {fork.join}
            or any(edge.source not in region and any(target in region | {fork.join} for target in edge.targets)
                   for edge in spec.edges if edge is not fork)
            or any(target in spec.terminals for edge in spec.edges if edge.source in region
                   for target in edge.targets)
        )
        if invalid:
            findings.append(CompileFinding("invalid_wave", ("edges", spec.edges.index(fork)),
                                           "Unsupported, overlapping, model-backed or unreachable wave"))
    return findings


def _invalid_branch_loop(spec: WorkflowSpec, nodes: Mapping[str, object],
                         graph: Mapping[str, set[str]], region: frozenset[str]) -> bool:
    """Repeat body must return to its only Loop; it cannot escape or be entered elsewhere."""
    loops = [nodes[key] for key in region if isinstance(nodes.get(key), LoopNode)]
    if not loops:
        return False
    if len(loops) != 1:
        return True
    loop = loops[0]
    assert isinstance(loop, LoopNode)
    repeat = next((edge.target for edge in spec.edges
                   if isinstance(edge, Route) and edge.source == loop.id and edge.outcome == "repeat"), None)
    if repeat is None:
        return True
    body: set[str] = set()
    pending = [repeat]
    while pending:
        current = pending.pop()
        if current == loop.id or current in body:
            continue
        if current not in region:
            return True
        body.add(current)
        pending.extend(graph[current])
    converges = {loop.id}
    while True:
        additions = {key for key in body - converges if graph[key] & converges}
        if not additions:
            break
        converges.update(additions)
    return (not body <= converges or
            any(edge.source not in body | {loop.id} and any(target in body for target in edge.targets)
                for edge in spec.edges))


@dataclass(frozen=True)
class BranchItem(Generic[S]):
    index: int
    state: S
    failure: str | None


def branch_execution(execution: _Execution[S]) -> _Execution[S]:
    return _Execution(_snapshot(execution.state_type, execution.state), execution.state_type,
                      execution.budget, execution.run_id, execution.log, execution.accounting)


def wave_observation(spec: WorkflowSpec, source: str, concurrency: int | None) -> dict[str, object]:
    fork = next((edge for edge in spec.edges if isinstance(edge, Fork) and edge.source == source), None)
    return {"wave_concurrency": concurrency or min(len(fork.branches), 4)} if fork else {}


def branch_worst_paths(spec: WorkflowSpec, fork: Fork) -> tuple[int, ...]:
    """Longest whole-branch route through the admitted single repeat-only cycle."""
    regions = branch_regions(spec, fork)
    nodes = {node.id: node for node in spec.nodes}
    results = []
    for branch, region in zip(fork.branches, regions):
        members = set(region) | {fork.join}
        routes: dict[str, dict[str, str]] = {key: {} for key in members}
        dependencies: dict[str, list[str]] = {key: [] for key in members}
        for edge in spec.edges:
            if isinstance(edge, Route) and edge.source in region:
                routes[edge.source][edge.outcome] = edge.target
                if not (isinstance(nodes[edge.source], LoopNode) and edge.outcome == "repeat"):
                    dependencies[edge.source].append(edge.target)
        order = tuple(TopologicalSorter(dependencies).static_order())
        loops = [node for key in region if isinstance(node := nodes[key], LoopNode)]

        def price(loop_cost: int) -> dict[str, int]:
            costs = {fork.join: 0}
            for key in order:
                if key == fork.join:
                    continue
                node = nodes[key]
                costs[key] = (loop_cost if isinstance(node, LoopNode) else
                              1 + max(costs[target] for target in routes[key].values()))
            return costs

        if loops:
            loop = loops[0]
            assert isinstance(loop, LoopNode)
            # Removing the repeat edge leaves a DAG. With Loop priced at zero,
            # the repeat body costs one finite trip back, while exit/exhausted
            # tails price their independent routes to the join. Each repeat
            # adds the same body plus one Loop visit; no count-sized expansion.
            tails = price(0)
            body = tails[routes[loop.id]["repeat"]]
            end = max(tails[routes[loop.id][label]] for label in ("exit", "exhausted"))
            loop_cost = loop.max_iterations * (1 + body) + 1 + end
        else:
            loop_cost = 0
        results.append(price(loop_cost)[branch])
    return tuple(results)


def admit_wave(execution: _Execution[S], spec: WorkflowSpec, fork: Fork) -> bool:
    worst = branch_worst_paths(spec, fork)
    required = sum(worst) + 1
    remaining = execution.budget.max_steps - execution.budget.used_steps
    if remaining >= required:
        return True
    execution.log.append_next(RunEvent(
        execution.run_id, 0, fork.source, next(node.kind for node in spec.nodes if node.id == fork.source),
        "FAILED_BUDGET", "FAILED_BUDGET",
        {"target": "FAILED_BUDGET", "failure": "wave_budget_refused", "required": required,
         "remaining_steps": remaining, "branch_worst": list(worst),
         "used_steps": execution.budget.used_steps, "max_steps": execution.budget.max_steps},
    ))
    return False


def finish_wave(execution: _Execution[S], spec: WorkflowSpec, fork: Fork,
                items: list[BranchItem[S]], reducer: Callable[[S, tuple[S, ...]], TransformResult[S]]) -> str:
    ordered = sorted(items, key=lambda item: item.index)
    if [item.index for item in ordered] != list(range(len(fork.branches))):
        raise ValueError("Wave collector requires exactly one item per branch")
    node = next(node for node in spec.nodes if node.id == fork.join)
    assert isinstance(node, TransformNode)
    failed = next((item for item in ordered if item.failure is not None), None)
    if failed is not None:
        target = failed.failure
        assert target is not None
        failure = "wave_branch_failure"
        try:
            execution.budget = execution.accounting.reserve(execution.run_id, execution.budget)
        except BudgetExceeded:
            target, failure = "FAILED_BUDGET", "budget_exhausted"
        execution.log.append_next(RunEvent(
            execution.run_id, 0, node.id, node.kind, target, target,
            {"target": target, "failure": failure, "branch_index": failed.index,
             "used_steps": execution.budget.used_steps, "max_steps": execution.budget.max_steps},
        ))
        return target
    inputs: object = None

    def reduce(entry: S) -> TransformResult[S]:
        nonlocal inputs
        branches = tuple(_snapshot(execution.state_type, item.state) for item in ordered)
        # Capture before caller mutation; never copy or replay the callable itself.
        inputs = deepcopy(tuple(state.model_dump(mode="python", round_trip=True)
                                for state in (entry, *branches)))
        return reducer(entry, branches)

    target = execution.invoke(
        node, reduce,
        {edge.outcome: edge.target for edge in spec.edges if isinstance(edge, Route) and edge.source == node.id},
        spec.terminals, {"reducer_branches": [item.index for item in ordered]},
    )
    if inputs is not None:
        event = execution.log.read()[-1]
        output = deepcopy((execution.state.model_dump(mode="python", round_trip=True),
                           event.transition, target, event.detail["failure"]))
        execution.reducer_observations.append(ReducerObservation(fork.join, inputs, output))
    return target
