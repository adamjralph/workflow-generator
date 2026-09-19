"""Public multi-run report and baseline seams, using offline Hermes databases."""
import hashlib
import json
import sqlite3
import runpy
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

from agent_lab.diagnosis import DiagnosisError, RunAttribution, TokenCounts, UsageRow
from agent_lab.diagnosis.report import KanbanRun, RunSelection, diagnose_report, load_report, measure_report
from agent_lab.diagnosis.store import DiagnosisStore
from tests.test_diagnosis import make_hermes


def test_runtime_neutral_report_uses_the_supplied_attribution_and_usage_contracts(tmp_path):
    class RecordedRuntime:
        measurement_method = "recorded-runtime/attributed-usage/four-units-v1"

        @property
        def usage_source(self):
            return self

        def adapter(self, selection):
            return self

        def attribute(self, run_id):
            return RunAttribution(run_id=run_id, runtime="recorded", role="researcher",
                                  session_ids=("s1",), workflow_identity="research")

        def usage(self, session_ids):
            return (UsageRow(session_id="s1", task=None, calls=2, tokens=TokenCounts(
                input_tokens=40, output_tokens=5, cache_read_tokens=60,
                cache_write_tokens=0, reasoning_tokens=3)),)

    source = RecordedRuntime()
    runs = (RunSelection(source="recording", run_id="r1"),)
    store = DiagnosisStore(tmp_path / "artifacts")
    before = measure_report(runs, source, "research", store)
    after = measure_report(runs, source, "research", store, baseline=before.path)
    report = load_report(after.path, store)
    assert report.current.runs[0].attribution.runtime == "recorded"
    assert report.current.roles[0].measurements.context_per_call == 50
    assert report.comparison.calls_per_run == 0
    source.measurement_method = "recorded-runtime/different-join/four-units-v1"
    with pytest.raises(DiagnosisError, match="measurement method"):
        measure_report(runs, source, "research", store, baseline=before.path)


def test_report_exposes_run_role_and_total_measurements(tmp_path):
    home = make_hermes(tmp_path)
    result = diagnose_report(home, (KanbanRun(board="stillroom-research", run_id="2"),),
                             "team", DiagnosisStore(tmp_path / "artifacts"))
    report = result.report
    assert report.before is None
    assert report.comparison is None
    assert len(report.current.runs) == 1
    totals = report.current.total
    assert totals.run_count == 1
    assert totals.calls == 10
    assert totals.calls_per_run == 10
    assert totals.context_per_call == 17683.1
    assert totals.tokens_per_run.input_tokens == 39103
    assert totals.cache_hit_rate == pytest.approx(0.778868)
    role = report.current.roles[0]
    assert role.role == "stillroom-media-analyst"
    assert role.measurements == totals
    assert role.traffic[0].measurements.calls == 9
    assert role.traffic[1].measurements.calls == 1
    assert report.current.runs[0].tokens_per_run.reasoning_tokens == 656


def test_measured_before_is_preserved_and_compared_in_all_four_units(tmp_path):
    home = make_hermes(tmp_path)
    store = DiagnosisStore(tmp_path / "artifacts")
    runs = (KanbanRun(board="stillroom-research", run_id="2"),)
    before = diagnose_report(home, runs, "team", store)
    original = before.path.read_bytes()
    with sqlite3.connect(home / "profiles/stillroom-media-analyst/state.db") as db:
        db.execute("UPDATE session_model_usage SET api_call_count=4 WHERE task=''")
    after = diagnose_report(home, runs, "team", store, baseline=before.path)
    assert before.path.read_bytes() == original
    assert after.path != before.path
    assert after.path.stem == hashlib.sha256(after.path.read_bytes()).hexdigest()
    loaded = load_report(after.path, store)
    assert loaded == after.report
    artifact = json.loads(after.path.read_bytes())
    assert artifact["current"]["roles"][0]["measurements"]["calls_per_run"] == 5
    assert artifact["before"]["total"]["calls"] == 10
    assert artifact["comparison"]["calls_per_run"] == -5
    assert loaded.before == before.report.current
    assert loaded.baseline_digest == before.path.stem
    delta = loaded.comparison
    assert delta is not None
    assert delta.calls_per_run == -5
    assert delta.context_per_call == pytest.approx(17683.1)
    assert delta.tokens_per_run.input_tokens == 0
    assert delta.cache_hit_rate == 0
    assert loaded.role_comparisons[0].delta == delta
    after.path.chmod(0o644)
    after.path.write_bytes(after.path.read_bytes() + b" ")
    with pytest.raises(DiagnosisError, match="digest"):
        load_report(after.path, store)


@pytest.mark.parametrize("invalid", ["empty", "duplicate", "shared-session", "wrong-workflow", "wrong-join", "legacy"])
def test_report_rejects_invalid_cohorts_and_unmeasured_baselines(tmp_path, invalid):
    home = make_hermes(tmp_path)
    store = DiagnosisStore(tmp_path / "artifacts")
    runs = (KanbanRun(board="stillroom-research", run_id="2"),)
    before = diagnose_report(home, runs, "team", store)
    baseline = before.path
    if invalid == "empty":
        runs = ()
    elif invalid == "duplicate":
        runs = runs + runs
    elif invalid == "shared-session":
        with sqlite3.connect(home / "kanban/boards/stillroom-research/kanban.db") as db:
            db.execute("INSERT INTO task_runs SELECT 3, task_id, profile, metadata FROM task_runs")
        runs = runs + (KanbanRun(board="stillroom-research", run_id="3"),)
    elif invalid == "wrong-join":
        raw = before.path.read_bytes().replace(b"summed-usage", b"session-rollup")
        baseline = before.path.parent / (hashlib.sha256(raw).hexdigest() + ".json")
        baseline.write_bytes(raw)
    elif invalid == "legacy":
        raw = b'{"calls":214,"input_tokens":1132524}'
        baseline = before.path.parent / (hashlib.sha256(raw).hexdigest() + ".json")
        baseline.write_bytes(raw)
    with pytest.raises(DiagnosisError):
        diagnose_report(home, runs, "other" if invalid == "wrong-workflow" else "team",
                        store, baseline=baseline)


def test_terminal_and_plugin_present_the_same_report_and_measured_before(tmp_path):
    home = make_hermes(tmp_path)
    manifest = tmp_path / "runs.json"
    manifest.write_text('[{"board":"stillroom-research","run_id":"2"}]')
    store = DiagnosisStore(tmp_path / "artifacts")
    baseline = diagnose_report(home, (KanbanRun(board="stillroom-research", run_id="2"),), "team", store)
    command = [sys.executable, "-m", "agent_lab.diagnosis", "--hermes-home", str(home),
               "--store", str(store.root), "--report", str(manifest), "--workflow", "team",
               "--baseline", str(baseline.path)]
    terminal = subprocess.run(command, text=True, capture_output=True)
    assert terminal.returncode == 0, terminal.stderr
    plugin = runpy.run_path(str(Path(__file__).parents[1] / "plugins/workflow-diagnosis/__init__.py"))
    output = plugin["report_command"](shlex.join([str(home), str(manifest), "team", str(store.root),
                                                str(baseline.path)]))
    for rendered in (terminal.stdout, output):
        assert "Before (measured" in rendered
        assert "Role: stillroom-media-analyst" in rendered
        assert "Run: 2" in rendered
        assert "Calls/run: 10" in rendered
        assert "Context/call: 17683.1" in rendered
        assert "input=39103" in rendered
        assert "Cache hit rate: 77.9%" in rendered
        assert "After minus before" in rendered
        assert "auxiliary (title_generation)" in rendered
        assert "reasoning=656" in rendered
        assert "Artifact:" in rendered
    unbased = subprocess.run(command[:-2], text=True, capture_output=True)
    assert unbased.returncode == 0, unbased.stderr
    assert "No measured baseline; no comparison or improvement claim." in unbased.stdout
    assert "After minus before" not in unbased.stdout


def test_zero_denominators_remain_undefined_in_baseline_comparisons(tmp_path):
    home = make_hermes(tmp_path)
    with sqlite3.connect(home / "profiles/stillroom-media-analyst/state.db") as db:
        db.execute("""UPDATE session_model_usage SET api_call_count=0, input_tokens=0,
                   output_tokens=0, cache_read_tokens=0, cache_write_tokens=0, reasoning_tokens=0""")
    store = DiagnosisStore(tmp_path / "artifacts")
    runs = (KanbanRun(board="stillroom-research", run_id="2"),)
    before = diagnose_report(home, runs, "team", store)
    after = diagnose_report(home, runs, "team", store, baseline=before.path)
    report = load_report(after.path, store)
    assert report.current.total.context_per_call is None
    assert report.current.total.cache_hit_rate is None
    assert report.comparison.context_per_call is None
    assert report.comparison.cache_hit_rate is None
    assert report.comparison.calls_per_run == 0


def test_report_refuses_store_inside_the_measured_home(tmp_path):
    home = make_hermes(tmp_path)
    with pytest.raises(DiagnosisError, match="outside Hermes"):
        diagnose_report(home, (KanbanRun(board="stillroom-research", run_id="2"),),
                        "team", DiagnosisStore(home / "artifacts"))
    assert not (home / "artifacts").exists()


def test_digest_valid_but_inconsistent_summary_cannot_be_a_baseline(tmp_path):
    home = make_hermes(tmp_path)
    store = DiagnosisStore(tmp_path / "artifacts")
    baseline = diagnose_report(home, (KanbanRun(board="stillroom-research", run_id="2"),), "team", store)
    data = json.loads(baseline.path.read_bytes())
    data["current"]["total"]["calls"] = 999
    raw = json.dumps(data).encode()
    forged = baseline.path.parent / (hashlib.sha256(raw).hexdigest() + ".json")
    forged.write_bytes(raw)
    with pytest.raises(DiagnosisError, match="summaries"):
        load_report(forged, store)
