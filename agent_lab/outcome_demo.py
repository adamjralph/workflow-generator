"""Offline ticket-34 demonstration: actual passing and failing JSON outputs.

Run: python -m agent_lab.outcome_demo --store /approved/evidence/folder
"""
import argparse
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from .outcome import run_checked
from .reference import TransformResult
from .spec import JsonOutputExpectation, Route, TransformNode, WorkflowSpec


class FixtureState(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)
    value: int = 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", required=True, type=Path)
    args = parser.parse_args()
    spec = WorkflowSpec(entry="produce", budget=1,
        nodes=(TransformNode(id="produce", operation="fixture",
            expected_output=JsonOutputExpectation(file="result.json", required_fields=("title", "body"))),),
        edges=(Route(source="produce", outcome="done", target="COMPLETED"),),
        terminals=("COMPLETED", "FAILED_VALIDATION", "FAILED_BUDGET"))
    results = []
    for driver in ("reference", "graph"):
        for case, payload in (("pass", {"title": "Offline fixture", "body": "Produced file"}),
                              ("fail", {"title": "Deliberately missing body"})):
            def bindings(output: Path):
                def produce(state: FixtureState) -> TransformResult[FixtureState]:
                    (output / "result.json").write_text(json.dumps(payload), encoding="utf-8")
                    return TransformResult(state, "done")
                return {"fixture": produce}
            actual = run_checked(spec, FixtureState(), bindings_factory=bindings,
                                 evidence_dir=args.store, driver=driver)
            if actual.execution.terminal != "COMPLETED" or actual.verdict.passed != (case == "pass"):
                raise RuntimeError("Offline demonstration did not meet the expected case")
            results.append({"driver": driver, "case": case, "run_id": actual.run_id,
                "terminal": actual.execution.terminal, "passed": actual.verdict.passed,
                "findings": [finding.model_dump() for finding in actual.verdict.findings],
                "verdict": str(actual.verdict_path)})
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
