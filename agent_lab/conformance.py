"""Case-scoped structural and behavioural evidence, never semantic correctness."""
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
import os
import sys
import tempfile
from typing import Literal

from .generation import GraphCandidate, UnsupportedCandidate
from .judgment import JevSource
from .reference import S, AuditError, CompileFinding, JudgmentBinding, compile_reference
from .runlog import RunLog
from .spec import DecisionNode, Finding, JudgmentNode, LoopNode, Route, TransformNode, WorkflowSpec


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
        if isinstance(node, LoopNode):
            fields[("nodes", node.id, "max_iterations")] = node.max_iterations
        fields[("nodes", node.id)] = (node.kind, reference, frozenset(node.route_labels))
    for edge in spec.edges:
        assert isinstance(edge, Route)
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


@dataclass(frozen=True)
class ConformanceReport:
    attempted: tuple[str, ...] = ()
    completed: tuple[str, ...] = ()
    evidence: tuple[CaseEvidence, ...] = ()
    findings: tuple[Finding | CompileFinding | ConformanceFinding, ...] = ()

    @property
    def passed(self) -> bool:
        return bool(self.completed) and self.attempted == self.completed and not self.findings


def check_conformance(spec: object, candidate: object, *, state_type: type[S],
                      bindings: Mapping[str, Callable[[S], object]], cases: Mapping[str, S],
                      evidence_dir: Path,
                      judgments: Mapping[str, JudgmentBinding[S]] | None = None,
                      protected_roots: tuple[Path, ...] = ()) -> ConformanceReport:
    """Check supplied cases; ValueError inputs and programming errors propagate.

    Additional Hermes source/install locations must be supplied as protected_roots
    when not discoverable from a loaded hermes_cli host. No Hermes import occurs.
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
    compilation = compile_reference(spec, state_type=state_type, bindings=bindings, judgments=judgments)
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
    try:
        destination.mkdir(parents=True, exist_ok=True)
        root = Path(tempfile.mkdtemp(prefix="check-", dir=destination))
    except OSError as exc:
        return ConformanceReport(findings=(ConformanceFinding("incomplete", ("evidence_dir",), str(exc)),))
    evidence = []
    attempted = []
    completed: list[str] = []
    findings: list[Finding | CompileFinding | ConformanceFinding] = []
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
        except (AuditError, OSError) as exc:
            findings.append(ConformanceFinding("incomplete", ("cases", name, phase), str(exc)))
            return ConformanceReport(tuple(attempted), tuple(completed), tuple(evidence), tuple(findings))
        for field, agrees in comparisons.items():
            if not agrees:
                findings.append(ConformanceFinding("behavioral_mismatch", ("cases", name, field),
                                                   "Candidate differs from plain reference"))
        completed.append(name)
    return ConformanceReport(tuple(attempted), tuple(completed), tuple(evidence), tuple(findings))
