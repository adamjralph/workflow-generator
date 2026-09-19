"""Evidence helper, not the ticket-06 baseline/role-management product.

Run from repository root:
  .venv/bin/python -m docs.reproduce_ticket05 --hermes-home ~/.hermes --store /tmp/ticket05-evidence

Pins the original 23 runs, excluding newer runs. Uses only the read-only public
adapters; never executes the historical script's live SQLite connections.
"""
import argparse
import json
from pathlib import Path

from agent_lab.diagnosis import diagnose
from agent_lab.diagnosis.hermes import HermesUsage, KanbanAdapter
from agent_lab.diagnosis.store import DiagnosisStore


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hermes-home", type=Path, required=True)
    parser.add_argument("--store", type=Path, required=True)
    args = parser.parse_args()
    manifest = Path(__file__).resolve().parents[1] / "tests/fixtures/cost-baseline-2026-09-18.json"
    runs = json.loads(manifest.read_text())["runs"]
    store = DiagnosisStore(args.store, protected_roots=(args.hermes_home,))
    records = []
    for run in runs:
        record = diagnose(run["attribution"]["run_id"], KanbanAdapter(args.hermes_home, run["board"]),
                          HermesUsage(args.hermes_home), store).record
        if record.attribution.model_dump(mode="json") != run["attribution"]:
            raise ValueError("Historical attribution changed; not the original baseline")
        records.append(record)
    calls = sum(r.calls_per_run for r in records)
    fresh = sum(r.tokens_per_run.input_tokens for r in records)
    cached = sum(r.tokens_per_run.cache_read_tokens for r in records)
    output = sum(r.tokens_per_run.output_tokens for r in records)
    reasoning = sum(r.tokens_per_run.reasoning_tokens for r in records)
    written = sum(r.tokens_per_run.cache_write_tokens for r in records)
    traffic = [t for r in records for t in r.traffic]
    worker = sum(t.calls_per_run for t in traffic if t.kind == "worker")
    auxiliary = sum(t.calls_per_run for t in traffic if t.kind == "auxiliary")
    review = sum(t.calls_per_run for t in traffic if t.kind == "review")
    actual = (len(records), calls, fresh, cached, output, written, reasoning, worker, auxiliary, review)
    expected = (23, 214, 1132524, 4608338, 89103, 0, 19237, 188, 26, 0)
    if actual != expected:
        raise ValueError(f"Baseline counters changed: {actual!r}; expected {expected!r}")
    print(f"Runs: {len(records)}; calls: {calls} (worker={worker}, auxiliary={auxiliary}, review={review})")
    print(f"Tokens: input={fresh} output={output} cache_read={cached} cache_write={written} reasoning={reasoning}")
    print(f"Calls/run: {calls / len(records):.1f}; context/call: {(fresh + cached) / calls:.0f}")
    print(f"Fresh input/run: {fresh / len(records):.0f}; cache hit rate: {cached / (fresh + cached):.0%}")
    print(f"Artifacts: {store.root}")


if __name__ == "__main__":
    main()
