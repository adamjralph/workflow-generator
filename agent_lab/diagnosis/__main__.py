"""Minimal line-oriented terminal UI; all measurement lives behind diagnose()."""
import argparse
import subprocess
import sys
from pathlib import Path

from . import DiagnosisError, diagnose
from .hermes import HermesUsage, KanbanAdapter
from .store import DiagnosisStore


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnose one Kanban run (read-only)")
    parser.add_argument("--hermes-home", type=Path, required=True)
    parser.add_argument("--store", type=Path, required=True, help="artifact directory outside Hermes")
    args = parser.parse_args()
    try:
        store = DiagnosisStore(args.store, protected_roots=(args.hermes_home,))
        print("Single-run diagnosis — Kanban (read-only)")
        board = input("Board: ").strip()
        run_id = input("Run id: ").strip()
        result = diagnose(run_id, KanbanAdapter(args.hermes_home, board),
                          HermesUsage(args.hermes_home), store)
        print(f"\nRun: {result.record.attribution.run_id}")
        print(f"Role: {result.record.attribution.role}")
        print(f"Calls/run: {result.record.calls_per_run} (includes auxiliary calls)")
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
