"""Minimal line-oriented terminal UI; all measurement lives behind diagnose()."""
import argparse
import subprocess
import sys
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

from . import DiagnosisError, Measurements, diagnose
from .hermes import HermesUsage, KanbanAdapter
from .store import DiagnosisStore
from .report import Aggregate, Cohort, DiagnosisReport, KanbanRun, MeasurementDelta, diagnose_report


def print_measurements(measurements: Measurements | Aggregate | MeasurementDelta,
                       indent: str = "") -> None:
    context = "n/a" if measurements.context_per_call is None else f"{measurements.context_per_call:.1f}"
    cache = "n/a" if measurements.cache_hit_rate is None else f"{measurements.cache_hit_rate:.1%}"
    tokens = measurements.tokens_per_run
    print(f"{indent}Calls/run: {measurements.calls_per_run}")
    print(f"{indent}Context/call: {context}")
    print(f"{indent}Tokens/run: input={tokens.input_tokens} output={tokens.output_tokens} "
          f"cache_read={tokens.cache_read_tokens} cache_write={tokens.cache_write_tokens} "
          f"reasoning={tokens.reasoning_tokens}")
    print(f"{indent}Cache hit rate: {cache}")


def print_cohort(cohort: Cohort) -> None:
    print(f"Runs: {cohort.total.run_count}; Calls: {cohort.total.calls}; "
          f"Fresh input tokens: {cohort.total.tokens.input_tokens}")
    print_measurements(cohort.total)
    for traffic in cohort.traffic:
        print(f"{traffic.kind} ({traffic.task or 'main loop'}):")
        print_measurements(traffic.measurements, "  ")
    for role in cohort.roles:
        print(f"Role: {role.role} ({role.measurements.run_count} runs)")
        print_measurements(role.measurements, "  ")
        for traffic in role.traffic:
            print(f"  {traffic.kind} ({traffic.task or 'main loop'}):")
            print_measurements(traffic.measurements, "    ")
    for selection, run in zip(cohort.selections, cohort.runs):
        print(f"Run: {run.attribution.run_id} (source={selection.source}, role={run.attribution.role})")
        print_measurements(run, "  ")
        for task in run.traffic:
            print(f"  {task.kind} ({task.task or 'main loop'}):")
            print_measurements(task, "    ")


def print_report(report: DiagnosisReport) -> None:
    print(f"Report: {report.workflow_identity}; Join: {report.measurement_method}")
    print("Scope: attributed sessions only; includes auxiliary/review, excludes unrelated chat.")
    if report.before is not None:
        print(f"Before (measured; artifact {report.baseline_digest}):")
        print_cohort(report.before)
    print("Current:")
    print_cohort(report.current)
    if report.comparison is None:
        print("No measured baseline; no comparison or improvement claim.")
    else:
        print("After minus before (cache rate: percentage-point change):")
        print_measurements(report.comparison)
        for role in report.role_comparisons:
            print(f"Role delta: {role.role}")
            print_measurements(role.delta, "  ")
        print("Descriptive comparison only: run counts and role/task mix may differ; "
              "not a causal improvement claim. Role deltas cover shared roles only.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnose Kanban runs (read-only)")
    parser.add_argument("--hermes-home", type=Path, required=True)
    parser.add_argument("--store", type=Path, required=True, help="artifact directory outside Hermes")
    parser.add_argument("--protected-root", type=Path, action="append", default=[],
                        help="additional Hermes source/install root (repeatable)")
    parser.add_argument("--report", type=Path, help="JSON list of {board, run_id} selections")
    parser.add_argument("--workflow", help="stable identity for this report cohort")
    parser.add_argument("--baseline", type=Path, help="prior report artifact in the same store")
    args = parser.parse_args()
    if bool(args.report) != bool(args.workflow) or (args.baseline and not args.report):
        parser.error("--report and --workflow are required together; --baseline requires --report")
    try:
        protected = tuple(args.protected_root)
        store = DiagnosisStore(args.store, protected_roots=(args.hermes_home, *protected))
        if args.report:
            runs = TypeAdapter(tuple[KanbanRun, ...]).validate_json(args.report.read_bytes())
            report = diagnose_report(args.hermes_home, runs, args.workflow, store,
                                     baseline=args.baseline, protected_roots=protected)
            print_report(report.report)
            print(f"Artifact: {report.path}")
            return 0
        print("Single-run diagnosis — Kanban (read-only)")
        board = input("Board: ").strip()
        run_id = input("Run id: ").strip()
        result = diagnose(run_id, KanbanAdapter(args.hermes_home, board, protected_roots=protected),
                          HermesUsage(args.hermes_home, protected_roots=protected), store)
        print(f"\nRun: {result.record.attribution.run_id}")
        print(f"Role: {result.record.attribution.role}")
        print("Scope: attributed sessions only; includes auxiliary/review, excludes unrelated chat.")
        print_measurements(result.record)
        for traffic in result.record.traffic:
            print(f"{traffic.kind} ({traffic.task or 'main loop'}):")
            print_measurements(traffic, indent="  ")
        print(f"Artifact: {result.path}")
        return 0
    except (DiagnosisError, ValidationError, OSError, subprocess.SubprocessError) as exc:
        print(f"Diagnosis failed: {exc}", file=sys.stderr)
        return 1
    except (EOFError, KeyboardInterrupt):
        print("\nDiagnosis cancelled.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
