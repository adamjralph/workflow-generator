"""Minimal line-oriented terminal UI; all measurement lives behind diagnose()."""
import argparse
import subprocess
import sys
from pathlib import Path

from . import DiagnosisError, Measurements, diagnose
from .hermes import HermesUsage, KanbanAdapter
from .store import DiagnosisStore


def print_measurements(measurements: Measurements, indent: str = "") -> None:
    context = "n/a" if measurements.context_per_call is None else f"{measurements.context_per_call:.1f}"
    cache = "n/a" if measurements.cache_hit_rate is None else f"{measurements.cache_hit_rate:.1%}"
    tokens = measurements.tokens_per_run
    print(f"{indent}Calls/run: {measurements.calls_per_run}")
    print(f"{indent}Context/call: {context}")
    print(f"{indent}Tokens/run: input={tokens.input_tokens} output={tokens.output_tokens} "
          f"cache_read={tokens.cache_read_tokens} cache_write={tokens.cache_write_tokens} "
          f"reasoning={tokens.reasoning_tokens}")
    print(f"{indent}Cache hit rate: {cache}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnose one Kanban run (read-only)")
    parser.add_argument("--hermes-home", type=Path, required=True)
    parser.add_argument("--store", type=Path, required=True, help="artifact directory outside Hermes")
    parser.add_argument("--protected-root", type=Path, action="append", default=[],
                        help="additional Hermes source/install root (repeatable)")
    args = parser.parse_args()
    try:
        protected = tuple(args.protected_root)
        store = DiagnosisStore(args.store, protected_roots=(args.hermes_home, *protected))
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
    except (DiagnosisError, OSError, subprocess.SubprocessError) as exc:
        print(f"Diagnosis failed: {exc}", file=sys.stderr)
        return 1
    except (EOFError, KeyboardInterrupt):
        print("\nDiagnosis cancelled.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
