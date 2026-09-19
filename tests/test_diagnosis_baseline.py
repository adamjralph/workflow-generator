"""Reproduce published figures through the real adapter, without live Hermes."""
import json
import sqlite3
from pathlib import Path

from agent_lab.diagnosis import diagnose
from agent_lab.diagnosis.hermes import HermesUsage, KanbanAdapter
from agent_lab.diagnosis.report import KanbanRun, diagnose_report, load_report
from agent_lab.diagnosis.store import DiagnosisStore


def test_september_18_baseline_reproduces_all_four_units(tmp_path):
    fixture = json.loads((Path(__file__).parent / "fixtures/cost-baseline-2026-09-18.json").read_text())
    home = tmp_path / "hermes"
    profile = home / "profiles/recorded/state.db"
    profile.parent.mkdir(parents=True)
    with sqlite3.connect(profile) as db:
        db.execute("""CREATE TABLE session_model_usage (session_id TEXT, task TEXT,
                   api_call_count INTEGER, input_tokens INTEGER, output_tokens INTEGER,
                   cache_read_tokens INTEGER, cache_write_tokens INTEGER, reasoning_tokens INTEGER)""")
        for run in fixture["runs"]:
            for row in run["usage"]:
                tokens = row["tokens"]
                db.execute("INSERT INTO session_model_usage VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (
                    row["session_id"], row["task"], row["calls"], tokens["input_tokens"],
                    tokens["output_tokens"], tokens["cache_read_tokens"],
                    tokens["cache_write_tokens"], tokens["reasoning_tokens"],
                ))
        # The baseline explicitly excludes a larger interactive session.
        db.execute("""INSERT INTO session_model_usage VALUES
                   ('unrecorded-telegram-session', '', 47, 991884, 10000, 0, 0, 20000)""")
    for run in fixture["runs"]:
        board = home / "kanban/boards" / run["board"] / "kanban.db"
        board.parent.mkdir(parents=True, exist_ok=True)
        a = run["attribution"]
        with sqlite3.connect(board) as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY, workflow_template_id TEXT);
                CREATE TABLE IF NOT EXISTS task_runs
                    (id INTEGER PRIMARY KEY, task_id TEXT, profile TEXT, metadata TEXT);
            """)
            db.execute("INSERT INTO tasks VALUES (?, NULL)", (a["run_id"],))
            db.execute("INSERT INTO task_runs VALUES (?, ?, ?, ?)", (
                a["run_id"], a["run_id"], a["role"],
                json.dumps({"worker_session_id": a["session_ids"][0]}),
            ))
    store = DiagnosisStore(tmp_path / "artifacts")
    records = [diagnose(r["attribution"]["run_id"], KanbanAdapter(home, r["board"]),
                        HermesUsage(home), store).record for r in fixture["runs"]]
    selections = tuple(KanbanRun(board=r["board"], run_id=r["attribution"]["run_id"])
                       for r in fixture["runs"])
    baseline = diagnose_report(home, selections, "september-18-team", store)
    result = diagnose_report(home, selections, "september-18-team", store, baseline=baseline.path)
    report = load_report(result.path, store)
    assert report.before == baseline.report.current
    assert report.before.total.run_count == 23
    assert report.before.total.calls == 214
    assert report.before.total.tokens.input_tokens == 1132524
    assert report.current.total.calls_per_run == 214 / 23
    assert round(report.current.total.context_per_call) == 26826
    assert round(report.current.total.tokens_per_run.input_tokens) == 49240
    assert round(report.current.total.cache_hit_rate * 100) == 80
    assert report.comparison.calls_per_run == 0
    assert report.comparison.tokens_per_run.input_tokens == 0
    assert len(report.current.runs) == 23
    assert len(records) == 23
    calls = sum(r.calls_per_run for r in records)
    fresh = sum(r.tokens_per_run.input_tokens for r in records)
    cached = sum(r.tokens_per_run.cache_read_tokens for r in records)
    assert calls == 214
    assert fresh == 1132524
    assert cached == 4608338
    assert sum(r.tokens_per_run.output_tokens for r in records) == 89103
    assert sum(r.tokens_per_run.reasoning_tokens for r in records) == 19237
    assert sum(r.tokens_per_run.cache_write_tokens for r in records) == 0
    assert round(calls / len(records), 1) == 9.3
    assert round((fresh + cached) / calls) == 26826
    assert round(fresh / len(records)) == 49240
    assert round(100 * cached / (fresh + cached)) == 80
    traffic = [t for r in records for t in r.traffic]
    assert sum(t.calls_per_run for t in traffic if t.kind == "worker") == 188
    assert sum(t.calls_per_run for t in traffic if t.kind == "auxiliary") == 26
    assert sum(t.tokens_per_run.input_tokens for t in traffic if t.kind == "auxiliary") == 8950
    assert sum(t.calls_per_run for t in traffic if t.kind == "review") == 0
    # Rounded per-role figures copied from the published table, not the fixture.
    published = {
        "stillroom-research-assistant": (6, 10.0, 69510, 5930, 35326),
        "stillroom-signal-guardian": (2, 9.0, 96720, 1859, 22519),
        "stillroom-signal-generator": (3, 10.0, 41858, 4608, 24879),
        "stillroom-chief-of-staff": (7, 9.9, 37967, 3473, 27198),
        "stillroom-media-analyst": (1, 10.0, 39103, 3591, 17683),
        "life-agent": (4, 6.8, 22894, 2018, 15410),
    }
    for role, expected in published.items():
        group = [r for r in records if r.attribution.role == role]
        n = len(group)
        c = sum(r.calls_per_run for r in group)
        i = sum(r.tokens_per_run.input_tokens for r in group)
        o = sum(r.tokens_per_run.output_tokens for r in group)
        cr = sum(r.tokens_per_run.cache_read_tokens for r in group)
        assert (n, round(c / n, 1), round(i / n), round(o / n), round((i + cr) / c)) == expected
        measured = next(item.measurements for item in report.current.roles if item.role == role)
        assert (measured.run_count, round(measured.calls_per_run, 1),
                round(measured.tokens_per_run.input_tokens), round(measured.tokens_per_run.output_tokens),
                round(measured.context_per_call)) == expected
