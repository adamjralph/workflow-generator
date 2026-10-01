"""Declared JSON output checks, separate from execution and semantic quality.

This opt-in offline slice uses the existing drivers and trusted local bindings.
It checks a fresh run-owned output directory, never an agent's completion claim.
"""
from collections.abc import Callable, Mapping
from dataclasses import dataclass
import hashlib
import json
import os
import stat
from contextlib import ExitStack
from pathlib import Path
import tempfile
from typing import Generic, Literal

from .designer import validate_evidence_root
from .generation import generate_graph
from .reference import ReferenceResult, S, compile_reference
from .runlog import RunLog
from .spec import Declaration, JsonOutputExpectation, TransformNode, validate_spec


class _OutputTooLarge(ValueError):
    pass


OutcomeCode = Literal["missing_file", "unsafe_file", "invalid_json", "invalid_object",
                      "missing_field", "step_not_completed", "file_too_large"]


class OutcomeFinding(Declaration):
    code: OutcomeCode
    requirement: str


class OutputVerdict(Declaration):
    run_id: str
    step: str
    spec_digest: str
    terminal: str
    declaration: JsonOutputExpectation
    findings: tuple[OutcomeFinding, ...]
    output_digest: str | None = None
    passed: bool


@dataclass(frozen=True)
class CheckedRun(Generic[S]):
    run_id: str
    root: Path
    execution: ReferenceResult[S]
    verdict: OutputVerdict
    verdict_path: Path


def run_checked(candidate: object, initial: S, *,
                bindings_factory: Callable[[Path], Mapping[str, Callable[[S], object]]],
                evidence_dir: Path, driver: Literal["reference", "graph"] = "reference",
                protected_roots: tuple[Path, ...] = ()) -> CheckedRun[S]:
    """Admit a declaration BEFORE work; execute once, inspect and save a verdict.

    Exactly one Transform expectation is supported in this slice. Fields mean
    literal top-level key presence (null is present), not value/quality checks.
    Bindings are trusted fixture code, not a sandbox. No model operations run.
    """
    admitted = validate_spec(candidate)
    if admitted.spec is None:
        raise ValueError(f"Invalid declaration: {admitted.findings}")
    spec = admitted.spec
    checked = [node for node in spec.nodes
               if isinstance(node, TransformNode) and node.expected_output is not None]
    if len(checked) != 1:
        raise ValueError("Exactly one Transform must declare an expected output")
    if any(isinstance(node, TransformNode) and node.model_operation for node in spec.nodes):
        raise ValueError("This offline checker does not run model operations")
    if driver not in {"reference", "graph"}:
        raise ValueError("Unknown driver")
    destination = validate_evidence_root(evidence_dir, protected_roots=protected_roots)
    destination.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix="outcome-", dir=destination))
    output = root / "output"
    output.mkdir()
    declared_bytes = spec.model_dump_json().encode("utf-8") + b"\n"
    spec_digest = hashlib.sha256(declared_bytes).hexdigest()
    with (root / "declaration.json").open("xb") as handle:
        handle.write(declared_bytes)
    bindings = bindings_factory(output)
    compiled = compile_reference(spec, state_type=type(initial), bindings=bindings)
    if compiled.plan is None:
        raise ValueError(f"Invalid executable: {compiled.findings}")
    log = RunLog(root / "run.jsonl")
    if driver == "reference":
        execution = compiled.plan.run(initial, run_id=root.name, log=log)
    else:
        generated = generate_graph(spec, state_type=type(initial), bindings=bindings)
        assert generated.candidate is not None
        if generated.candidate.inspect_structure() != spec:
            raise ValueError("Generated declaration differs from admitted workflow")
        execution = generated.candidate.run(initial, run_id=root.name, log=log)
    node = checked[0]
    declaration = node.expected_output
    assert declaration is not None
    findings, digest = _check_file(output, declaration)
    if not any(event.node == node.id and event.transition is not None
               and not event.detail.get("failure") for event in execution.trace):
        findings = (OutcomeFinding(code="step_not_completed", requirement=node.id),) + findings
    verdict = OutputVerdict(run_id=root.name, step=node.id,
        spec_digest=spec_digest,
        terminal=execution.terminal, declaration=declaration, findings=findings,
        output_digest=digest, passed=not findings)
    verdict_path = root / "verdict.json"
    with verdict_path.open("x", encoding="utf-8") as handle:
        handle.write(verdict.model_dump_json(indent=2) + "\n")
    return CheckedRun(root.name, root, execution, verdict, verdict_path)


def _check_file(output: Path, declaration: JsonOutputExpectation) -> tuple[tuple[OutcomeFinding, ...], str | None]:
    def failed(code: OutcomeCode, digest: str | None = None):
        return (OutcomeFinding(code=code, requirement=declaration.file),), digest

    try:
        data = _read_output(output, declaration.file, declaration.max_bytes)
    except FileNotFoundError:
        return failed("missing_file")
    except _OutputTooLarge:
        return failed("file_too_large")
    except (OSError, ValueError):
        return failed("unsafe_file")
    digest = hashlib.sha256(data).hexdigest()
    try:
        value = json.loads(data, parse_constant=_reject_constant)
    except (ValueError, UnicodeError, RecursionError):
        return failed("invalid_json", digest)
    if not isinstance(value, dict):
        return failed("invalid_object", digest)
    return tuple(OutcomeFinding(code="missing_field", requirement=field)
                 for field in declaration.required_fields if field not in value), digest


def _reject_constant(value: str) -> None:
    raise ValueError(f"Not JSON: {value}")


def _read_output(output: Path, file: str, max_bytes: int) -> bytes:
    """Walk pinned directory descriptors; never follow links or open devices."""
    with ExitStack() as stack:
        directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        directory = os.open(output, directory_flags)
        stack.callback(os.close, directory)
        parts = file.split("/")
        for part in parts[:-1]:
            directory = os.open(part, directory_flags, dir_fd=directory)
            stack.callback(os.close, directory)
        descriptor = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                             dir_fd=directory)
        stack.callback(os.close, descriptor)
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise ValueError("Expected a regular file without hard links")
        if metadata.st_size > max_bytes:
            raise _OutputTooLarge("Output exceeds the declared byte limit")
        with os.fdopen(os.dup(descriptor), "rb") as handle:
            data = handle.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise _OutputTooLarge("Output grew beyond the read limit")
        return data
