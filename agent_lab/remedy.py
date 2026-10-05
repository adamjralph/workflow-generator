"""One opt-in offline repair for a completed, single-step output producer.

Trusted local bindings are not sandboxed. No models, gates, source writes,
restart/resume, or automatic retry of execution failures are supported.
"""
from collections.abc import Callable, Mapping
from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Generic, Literal

from .outcome import CheckedRun, OutputVerdict, run_checked
from .reference import AuditError, S
from .spec import Declaration, Route, TransformNode, validate_spec


class RemedyReceipt(Declaration):
    status: Literal["passed", "repaired", "exhausted", "ineligible", "repair_failed"]
    step_allowance: int
    reserved_steps: int
    original_run: str
    original_verdict_digest: str
    repair_run: str | None = None
    repair_verdict_digest: str | None = None


@dataclass(frozen=True)
class RemediedRun(Generic[S]):
    original: CheckedRun[S]
    repair: CheckedRun[S] | None
    receipt: RemedyReceipt
    receipt_path: Path

    @property
    def passed(self) -> bool:
        return self.receipt.status in {"passed", "repaired"}


def run_with_remedy(candidate: object, initial: S, *,
                    bindings_factory: Callable[[Path], Mapping[str, Callable[[S], object]]],
                    repair_bindings_factory: Callable[[Path, OutputVerdict], Mapping[str, Callable[[S], object]]],
                    step_allowance: int, evidence_dir: Path,
                    driver: Literal["reference", "graph"] = "reference",
                    protected_roots: tuple[Path, ...] = ()) -> RemediedRun[S]:
    """Reserve one original step and optionally one repair step before invoking it.

    An allowance of one disables repair; two permits exactly one attempt. Each
    execution starts from a detached original input, and writes fresh output.
    Only output failure after COMPLETED is eligible. No existing run is resumed.
    Factory failures consume their reservation and omit exception content.
    """
    if type(step_allowance) is not int or step_allowance not in {1, 2}:
        raise ValueError("Offline step allowance must be one or two")
    admitted = validate_spec(candidate)
    spec = admitted.spec
    if spec is None:
        raise ValueError("Invalid remedy declaration")
    if (len(spec.nodes) != 1 or not isinstance(spec.nodes[0], TransformNode)
            or spec.nodes[0].model_operation or spec.nodes[0].expected_output is None
            or spec.budget != 1 or spec.nodes[0].outcomes != ("done",)
            or not {"COMPLETED", "FAILED_VALIDATION", "FAILED_BUDGET"} <= set(spec.terminals)
            or spec.entry != spec.nodes[0].id
            or spec.edges != (Route(source=spec.entry, outcome="done", target="COMPLETED"),)):
        raise ValueError("Remedy requires one offline Transform routed directly to COMPLETED")
    # Snapshot before trusted factories can mutate the caller's initial model.
    snapshot = type(initial).model_validate(initial.model_dump(), strict=True)

    def original_bindings(output: Path) -> Mapping[str, Callable[[S], object]]:
        with (output.parent / "remedy-policy.json").open("x", encoding="utf-8") as handle:
            handle.write(f'{{"step_allowance":{step_allowance},"reserved_steps":1}}\n')
        return bindings_factory(output)

    original = run_checked(spec, snapshot.model_copy(deep=True), bindings_factory=original_bindings,
        evidence_dir=evidence_dir, driver=driver, protected_roots=protected_roots)
    original_digest = hashlib.sha256(original.verdict_path.read_bytes()).hexdigest()
    repair = None
    status: Literal["passed", "repaired", "exhausted", "ineligible", "repair_failed"]
    reserved = 1
    if original.verdict.passed:
        status = "passed"
    elif original.execution.terminal != "COMPLETED" or original.execution.used_steps != 1:
        status = "ineligible"
    elif step_allowance == 1:
        status = "exhausted"
    else:
        # Exclusive marker precedes ANY repair factory work. No API re-enters it.
        with (original.root / "repair-reserved.json").open("x", encoding="utf-8") as handle:
            handle.write('{"reserved_steps":2}\n')
        reserved = 2
        try:
            repair = run_checked(spec, snapshot.model_copy(deep=True),
                bindings_factory=lambda output: repair_bindings_factory(output, original.verdict),
                evidence_dir=original.root / "repair", driver=driver, protected_roots=protected_roots)
        except AuditError:
            raise  # An audit failure cannot be converted into a completed receipt.
        except Exception:
            status = "repair_failed"
        else:
            status = ("repaired" if repair.verdict.passed and repair.execution.terminal == "COMPLETED"
                      else "exhausted")
    receipt = RemedyReceipt(status=status, step_allowance=step_allowance, reserved_steps=reserved,
        original_run=original.run_id, original_verdict_digest=original_digest,
        repair_run=repair.run_id if repair else None,
        repair_verdict_digest=hashlib.sha256(repair.verdict_path.read_bytes()).hexdigest() if repair else None)
    path = original.root / "remedy.json"
    with path.open("x", encoding="utf-8") as handle:
        handle.write(receipt.model_dump_json(indent=2) + "\n")
    return RemediedRun(original, repair, receipt, path)
