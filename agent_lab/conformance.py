"""Case-scoped structural and behavioural evidence, never semantic correctness."""
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
import hashlib
from pathlib import Path
import os
import sys
import tempfile
from typing import Literal

from pydantic import BaseModel

from .generation import GraphCandidate, UnsupportedCandidate
from .judgment import JevSource
from .model_operation import ModelOperation
from .reference import S, AuditError, CompileFinding, JudgmentBinding, ReducerObservation, TransformResult, compile_reference
from .runlog import RunEvent, RunLog
from .spec import DecisionNode, Finding, Fork, JudgmentNode, LoopNode, Route, TransformNode, WorkflowSpec, branch_regions


_INSPECT = GraphCandidate.inspect_structure


def _strict_equal(left: object, right: object) -> bool:
    """Python equality alone conflates True/1 and 1/1.0 inside typed unions."""
    if type(left) is not type(right):
        return False
    if isinstance(left, dict) and isinstance(right, dict):
        return len(left) == len(right) and all(
            any(_strict_equal(key, other) and _strict_equal(value, other_value)
                for other, other_value in right.items())
            for key, value in left.items()
        )
    if isinstance(left, (set, frozenset)) and isinstance(right, (set, frozenset)):
        return len(left) == len(right) and all(
            any(_strict_equal(value, other) for other in right) for value in left
        )
    if isinstance(left, (list, tuple)) and isinstance(right, (list, tuple)):
        return len(left) == len(right) and all(_strict_equal(a, b) for a, b in zip(left, right))
    return left == right


def _structure(spec: WorkflowSpec) -> dict[tuple[str | int, ...], object]:
    fields: dict[tuple[str | int, ...], object] = {
        ("entry",): spec.entry, ("budget",): spec.budget,
        ("terminals",): frozenset(spec.terminals),
    }
    for node in spec.nodes:
        assert isinstance(node, (TransformNode, DecisionNode, JudgmentNode, LoopNode))
        reference = (node.operation if isinstance(node, TransformNode) else
                     node.value if isinstance(node, DecisionNode) else
                     node.exit_predicate if isinstance(node, LoopNode) else node.id)
        if isinstance(node, TransformNode):
            fields[("nodes", node.id, "model_operation")] = (
                node.model_operation, node.operation_version, node.schema_version)
        if isinstance(node, LoopNode):
            fields[("nodes", node.id, "max_iterations")] = node.max_iterations
        fields[("nodes", node.id)] = (node.kind, reference, frozenset(node.route_labels))
    for edge in spec.edges:
        if isinstance(edge, Fork):
            fields[("forks", edge.source, edge.outcome)] = (edge.branches, edge.join)
        else:
            fields[("edges", edge.source, edge.outcome)] = edge.target
    return fields


@dataclass(frozen=True)
class ConformanceFinding:
    code: Literal["structural_mismatch", "behavioral_mismatch", "unsupported_candidate",
                  "empty_cases", "incomplete"]
    path: tuple[str | int, ...]
    message: str


@dataclass(frozen=True)
class CaseEvidence:
    case: str
    run_id: str
    reference_log: Path
    candidate_log: Path
    reference_digest: str = ""
    candidate_digest: str = ""
    reference_projection_digest: str = ""
    candidate_projection_digest: str = ""


@dataclass(frozen=True)
class CaseOutput:
    """Observed candidate result from the checked run, not a second execution."""
    case: str
    state: BaseModel
    terminal: str
    used_steps: int
    route: tuple[tuple[str, str | None, str], ...]


@dataclass(frozen=True)
class ConformanceReport:
    attempted: tuple[str, ...] = ()
    completed: tuple[str, ...] = ()
    evidence: tuple[CaseEvidence, ...] = ()
    findings: tuple[Finding | CompileFinding | ConformanceFinding, ...] = ()
    outputs: tuple[CaseOutput, ...] = ()

    @property
    def passed(self) -> bool:
        return bool(self.completed) and self.attempted == self.completed and not self.findings


def check_conformance(spec: object, candidate: object, *, state_type: type[S],
                      bindings: Mapping[str, Callable[[S], object]], cases: Mapping[str, S],
                      evidence_dir: Path,
                      judgments: Mapping[str, JudgmentBinding[S]] | None = None,
                      protected_roots: tuple[Path, ...] = (),
                      model_operations: Mapping[str, ModelOperation[S]] | None = None,
                      reducers: Mapping[str, Callable[[S, tuple[S, ...]], TransformResult[S]]] | None = None,
                      wave_concurrency: int | None = None) -> ConformanceReport:
    """Check supplied cases; ValueError inputs and programming errors propagate.

    Additional Hermes source/install locations must be supplied as protected_roots
    when not discoverable from a loaded hermes_cli host. No Hermes import occurs.
    Reducer observations reject identical-input divergence across supplied cases.
    This does not prove purity or reset caller-owned callable state between cases;
    the public mappings provide no callable factory, and the candidate owns its mapping.
    """
    try:
        destination = Path(evidence_dir).expanduser().resolve()
        protected = (Path.home() / ".hermes", Path(__file__).resolve().parents[1],
                     *protected_roots)
        if configured := os.environ.get("HERMES_HOME"):
            protected += (Path(configured).expanduser(),)
        if host_file := getattr(sys.modules.get("hermes_cli"), "__file__", None):
            protected += (Path(host_file).resolve().parents[1],)
        if any(destination.is_relative_to(path.resolve()) for path in protected):
            raise ValueError("Evidence directory must be outside Hermes and project source")
    except OSError as exc:
        return ConformanceReport(findings=(ConformanceFinding("incomplete", ("evidence_dir",), str(exc)),))
    named_cases = tuple(cases.items())
    if any(type(name) is not str or not name.strip() for name, _ in named_cases):
        raise ValueError("Case names must be nonempty strings")
    compilation = compile_reference(spec, state_type=state_type, bindings=bindings, judgments=judgments,
                                    model_operations=model_operations, reducers=reducers,
                                    wave_concurrency=wave_concurrency)
    if compilation.plan is None:
        return ConformanceReport(findings=compilation.findings)
    if not named_cases:
        return ConformanceReport(findings=(ConformanceFinding("empty_cases", ("cases",),
                                                             "Supply at least one case"),))
    if type(candidate) is not GraphCandidate:
        return ConformanceReport(findings=(ConformanceFinding("unsupported_candidate", ("candidate",),
                                                             "Expected exact GraphCandidate type"),))
    try:
        actual_structure = _INSPECT(candidate)
    except UnsupportedCandidate as exc:
        return ConformanceReport(findings=(ConformanceFinding("unsupported_candidate", ("candidate",),
                                                             str(exc)),))
    expected_fields, actual_fields = _structure(compilation.plan.spec), _structure(actual_structure)
    differences = [ConformanceFinding("structural_mismatch", path,
                                     "Candidate execution configuration differs from spec")
                   for path in expected_fields.keys() | actual_fields.keys()
                   if expected_fields.get(path) != actual_fields.get(path)]
    if candidate.state_type is not state_type:
        differences.append(ConformanceFinding("structural_mismatch", ("state_type",),
                                              "Candidate state type differs"))
    if differences:
        return ConformanceReport(findings=tuple(sorted(differences, key=lambda f: str(f.path))))
    # Bindings are trusted local code, not a sandbox. Refuse known live sources
    # and directly shared replay objects; callers must also avoid hidden shared
    # cursors inside their custom offline sources.
    judgment_ids = tuple(node.id for node in compilation.plan.spec.nodes
                         if isinstance(node, JudgmentNode))
    reference_sources = tuple(compilation.plan.judgments[key].source for key in judgment_ids)
    candidate_sources = tuple(candidate._judgments[key].source for key in judgment_ids)
    if any(isinstance(source, JevSource) for source in reference_sources + candidate_sources):
        raise ValueError("Conformance requires explicit offline judgment sources")
    if any(left is right for left in reference_sources for right in candidate_sources):
        raise ValueError("Conformance requires independent judgment sources for each driver")
    model_keys = tuple(node.operation for node in compilation.plan.spec.nodes
                       if isinstance(node, TransformNode) and node.model_operation)
    reference_models = tuple(compilation.plan.model_operations[key].source for key in model_keys)
    candidate_models = tuple(candidate._model_operations[key].source for key in model_keys)
    if any(source.mode not in {"fixture", "recorded"} for source in reference_models + candidate_models):
        raise ValueError("Conformance requires explicit offline model sources")
    if any(left is right for left in reference_models for right in candidate_models):
        raise ValueError("Conformance requires independent model sources for each driver")
    try:
        destination.mkdir(parents=True, exist_ok=True)
        root = Path(tempfile.mkdtemp(prefix="check-", dir=destination))
    except OSError as exc:
        return ConformanceReport(findings=(ConformanceFinding("incomplete", ("evidence_dir",), str(exc)),))
    evidence = []
    attempted = []
    completed: list[str] = []
    outputs: list[CaseOutput] = []
    findings: list[Finding | CompileFinding | ConformanceFinding] = []
    reducer_history: dict[str, list[tuple[str, ReducerObservation]]] = {"reference": [], "candidate": []}
    for index, (name, initial) in enumerate(named_cases):
        run_id = f"case-{index}"
        record = CaseEvidence(name, run_id, root / f"{index}-reference.jsonl",
                              root / f"{index}-candidate.jsonl")
        plain, graph = RunLog(record.reference_log), RunLog(record.candidate_log)
        attempted.append(name)
        evidence.append(record)
        phase = "reference"
        try:
            expected = compilation.plan.run(initial, run_id=run_id, log=plain)
            phase = "candidate"
            actual = candidate.run(initial, run_id=run_id, log=graph)
            phase = "comparison"
            for driver, result in (("reference", expected), ("candidate", actual)):
                for observation in result.reducer_observations:
                    for previous_case, previous in reducer_history[driver]:
                        if (observation.join == previous.join
                                and _strict_equal(observation.inputs, previous.inputs)
                                and not _strict_equal(observation.output, previous.output)):
                            findings.append(ConformanceFinding(
                                "behavioral_mismatch", ("cases", name, "reducers", observation.join, driver),
                                f"Identical reducer inputs differ from case {previous_case!r}"))
                            break
                    reducer_history[driver].append((name, observation))
            forks = tuple(edge for edge in compilation.plan.spec.edges if isinstance(edge, Fork))
            if forks and not _strict_equal(
                tuple((item.join, item.inputs, item.output) for item in expected.reducer_observations),
                tuple((item.join, item.inputs, item.output) for item in actual.reducer_observations),
            ):
                findings.append(ConformanceFinding(
                    "behavioral_mismatch", ("cases", name, "reducers", forks[0].join),
                    "Candidate reducer observation differs from plain reference"))
            # Owned drivers strictly validate and detach state at every boundary.
            comparisons = {
                "state": _strict_equal(expected.state.model_dump(mode="python", round_trip=True),
                                       actual.state.model_dump(mode="python", round_trip=True)),
                "terminal": expected.terminal == actual.terminal,
                "used_steps": expected.used_steps == actual.used_steps,
                "trace": plain.read() == graph.read(),
                "bytes": plain.read_bytes() == graph.read_bytes(),
                "digest": plain.digest() == graph.digest(),
            }
            if any(isinstance(edge, Fork) for edge in compilation.plan.spec.edges):
                expected_projection = wave_projection(compilation.plan.spec, plain.read())
                actual_projection = wave_projection(compilation.plan.spec, graph.read())
                for key in ("trace", "bytes", "digest"):
                    del comparisons[key]
                comparisons["wave_projection"] = expected_projection == actual_projection
                evidence[-1] = replace(record, reference_digest=plain.digest(), candidate_digest=graph.digest(),
                                       reference_projection_digest=expected_projection,
                                       candidate_projection_digest=actual_projection)
        except (AuditError, OSError) as exc:
            findings.append(ConformanceFinding("incomplete", ("cases", name, phase), str(exc)))
            return ConformanceReport(tuple(attempted), tuple(completed), tuple(evidence), tuple(findings))
        for field, agrees in comparisons.items():
            if not agrees:
                findings.append(ConformanceFinding("behavioral_mismatch", ("cases", name, field),
                                                   "Candidate differs from plain reference"))
        outputs.append(CaseOutput(name, actual.state, actual.terminal, actual.used_steps,
                                  tuple((event.node, event.transition, event.detail["target"])
                                        for event in graph.read())))
        completed.append(name)
    return ConformanceReport(tuple(attempted), tuple(completed), tuple(evidence), tuple(findings),
                             tuple(outputs))


def wave_projection(spec: WorkflowSpec, events: list[RunEvent]) -> str:
    """Derive comparison order from persisted events; never rewrite the raw log."""
    fork = next(edge for edge in spec.edges if isinstance(edge, Fork))
    regions = branch_regions(spec, fork)
    members = set().union(*regions)
    # The single admitted wave has no alternate entrance or repeated visit.
    # Keep run-level records in place; group only the branch interval.
    positions = [i for i, event in enumerate(events) if event.node in members]
    projected = list(events)
    if positions:
        start, end = min(positions), max(positions) + 1
        interval = events[start:end]
        if any(event.node not in members for event in interval):
            raise ValueError("Run-level event inside branch interval")
        grouped = []
        for region in regions:
            for visit, event in enumerate((event for event in interval if event.node in region), 1):
                grouped.append(replace(event, detail={**event.detail, "used_steps": visit}))
        projected[start:end] = grouped
    projected = [replace(event, detail={key: value for key, value in event.detail.items()
                                       if key != "wave_concurrency"})
                 if event.node == fork.source else event for event in projected]
    material = "\n".join(replace(event, seq=index).to_json() for index, event in enumerate(projected))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()
