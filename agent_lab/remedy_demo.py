"""Demonstrate repaired and exhausted output checks without live calls."""
import argparse
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from .outcome import OutputVerdict
from .reference import TransformResult
from .remedy import run_with_remedy
from .spec import JsonOutputExpectation, Route, TransformNode, WorkflowSpec


class ReportInput(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)
    title: str = "Internal release checklist"
    items: tuple[str, ...] = ("Declared output check", "One bounded remedy", "Real alert", "Useful real workflow")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", required=True, type=Path)
    args = parser.parse_args()
    spec = WorkflowSpec(entry="report", budget=1,
        nodes=(TransformNode(id="report", operation="write_report",
            expected_output=JsonOutputExpectation(file="report.json", required_fields=("title", "body"))),),
        edges=(Route(source="report", outcome="done", target="COMPLETED"),),
        terminals=("COMPLETED", "FAILED_VALIDATION", "FAILED_BUDGET"))
    results = []
    for driver in ("reference", "graph"):
        for case in ("repairable", "unrepairable"):
            def original(output: Path):
                def write(state: ReportInput):
                    (output / "report.json").write_text(json.dumps({"title": state.title}), encoding="utf-8")
                    return TransformResult(state, "done")
                return {"write_report": write}

            def repair(output: Path, failed: OutputVerdict):
                def write(state: ReportInput):
                    payload = {"title": state.title}
                    if case == "repairable" and any(f.requirement == "body" for f in failed.findings):
                        payload["body"] = "\n".join(state.items)
                    (output / "report.json").write_text(json.dumps(payload), encoding="utf-8")
                    return TransformResult(state, "done")
                return {"write_report": write}

            result = run_with_remedy(spec, ReportInput(), bindings_factory=original,
                repair_bindings_factory=repair, step_allowance=2, evidence_dir=args.store, driver=driver)
            expected = "repaired" if case == "repairable" else "exhausted"
            if result.receipt.status != expected:
                raise RuntimeError("Demonstration did not produce the expected outcome")
            results.append({"driver": driver, "case": case, "status": result.receipt.status,
                "reserved_steps": result.receipt.reserved_steps, "receipt": str(result.receipt_path)})
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
