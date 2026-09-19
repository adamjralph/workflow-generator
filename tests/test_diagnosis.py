"""Public diagnosis seams; all databases here are offline fixtures."""
import json
import sqlite3
import subprocess
import sys

import pytest

from pathlib import Path

from agent_lab.diagnosis import DiagnosisError, RunAttribution, UsageRow, TokenCounts, diagnose
from agent_lab.diagnosis.store import DiagnosisStore
from agent_lab.diagnosis.hermes import HermesUsage, KanbanAdapter


def make_hermes(tmp_path: Path) -> Path:
    home = tmp_path / "hermes"
    board = home / "kanban/boards/stillroom-research/kanban.db"
    board.parent.mkdir(parents=True)
    with sqlite3.connect(board) as db:
        db.executescript("""
            CREATE TABLE tasks (id TEXT PRIMARY KEY, workflow_template_id TEXT);
            CREATE TABLE task_runs (id INTEGER PRIMARY KEY, task_id TEXT, profile TEXT, metadata TEXT);
            INSERT INTO tasks VALUES ('t_fb59e5d1', NULL);
        """)
        db.execute("INSERT INTO task_runs VALUES (2, 't_fb59e5d1', 'stillroom-media-analyst', ?)",
                   (json.dumps({"worker_session_id": "20260914_093544_993097"}),))
    profile = home / "profiles/stillroom-media-analyst/state.db"
    profile.parent.mkdir(parents=True)
    with sqlite3.connect(profile) as db:
        db.executescript("""
            CREATE TABLE sessions (id TEXT PRIMARY KEY, api_call_count INTEGER);
            CREATE TABLE session_model_usage (session_id TEXT, model TEXT,
                billing_provider TEXT, task TEXT, api_call_count INTEGER);
            INSERT INTO sessions VALUES ('20260914_093544_993097', 9);
            INSERT INTO session_model_usage VALUES
              ('20260914_093544_993097', 'gpt-5.6-sol', 'openai-codex', '', 9),
              ('20260914_093544_993097', 'gpt-5.6-sol', 'openai-codex', 'title_generation', 1),
              ('unrelated-interactive-session', 'model', 'provider', '', 999);
        """)
        for column in ("input_tokens", "output_tokens", "cache_read_tokens",
                       "cache_write_tokens", "reasoning_tokens"):
            db.execute(f"ALTER TABLE session_model_usage ADD COLUMN {column} INTEGER DEFAULT 0")
        db.execute("""UPDATE session_model_usage SET input_tokens=38863, output_tokens=3539,
                      cache_read_tokens=137728, reasoning_tokens=656
                      WHERE session_id='20260914_093544_993097' AND task=''""")
        db.execute("""UPDATE session_model_usage SET input_tokens=240, output_tokens=52
                      WHERE task='title_generation'""")
    return home


def test_kanban_attributes_a_historical_run_without_inventing_a_template(tmp_path):
    home = make_hermes(tmp_path)
    attribution = KanbanAdapter(home, "stillroom-research").attribute("2")
    assert attribution.run_id == "2"
    assert attribution.runtime == "kanban"
    assert attribution.role == "stillroom-media-analyst"
    assert attribution.session_ids == ("20260914_093544_993097",)
    assert attribution.workflow_identity == "board:stillroom-research/task:t_fb59e5d1"


def test_historical_run_reports_ten_calls_not_nine_and_preserves_versions(tmp_path):
    home = make_hermes(tmp_path)
    store = DiagnosisStore(tmp_path / "artifacts")
    adapter, usage = KanbanAdapter(home, "stillroom-research"), HermesUsage(home)
    first = diagnose("2", adapter, usage, store)
    assert first.record.calls_per_run == 10
    assert store.load(first.path) == first.record
    original = first.path.read_bytes()
    second = diagnose("2", adapter, usage, store)
    assert second.record.calls_per_run == 10
    assert second.path != first.path
    assert second.path.parent == first.path.parent
    assert first.path.read_bytes() == original
    assert store.load(first.path) == first.record
    import hashlib
    assert first.path.stem == hashlib.sha256(original).hexdigest()


def test_historical_run_reports_all_four_units_and_separate_token_lines(tmp_path):
    home = make_hermes(tmp_path)
    result = diagnose("2", KanbanAdapter(home, "stillroom-research"), HermesUsage(home),
                      DiagnosisStore(tmp_path / "artifacts"))
    record = result.record
    assert record.schema_version == 2
    assert record.calls_per_run == 10
    assert record.context_per_call == 17683.1
    assert record.cache_hit_rate == pytest.approx(0.778868)
    assert record.tokens_per_run.input_tokens == 39103
    assert record.tokens_per_run.output_tokens == 3591
    assert record.tokens_per_run.cache_read_tokens == 137728
    assert record.tokens_per_run.cache_write_tokens == 0
    assert record.tokens_per_run.reasoning_tokens == 656
    assert DiagnosisStore(tmp_path / "artifacts").load(result.path) == record


def test_review_and_auxiliary_tasks_are_not_attributed_to_the_worker_loop(tmp_path):
    home = make_hermes(tmp_path)
    with sqlite3.connect(home / "profiles/stillroom-media-analyst/state.db") as db:
        db.executemany("INSERT INTO session_model_usage VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", [
            ("20260914_093544_993097", "reviewer", "p", "background_review", 2, 100, 20, 300, 40, 60),
            ("20260914_093544_993097", "m", "p", None, 1, 50, 10, 0, 0, 0),
            ("20260914_093544_993097", "m", "p", "future_aux", 1, 10, 5, 0, 0, 0),
            ("unrelated-interactive-session", "reviewer", "p", "background_review", 999, 999999, 999, 0, 0, 999),
        ])
    record = diagnose("2", KanbanAdapter(home, "stillroom-research"), HermesUsage(home),
                      DiagnosisStore(tmp_path / "artifacts")).record
    assert record.calls_per_run == 14
    assert record.tokens_per_run.input_tokens == 39263
    assert record.tokens_per_run.reasoning_tokens == 716
    traffic = {item.task: item for item in record.traffic}
    assert traffic[None].kind == "worker"
    assert traffic[None].calls_per_run == 10
    assert traffic["title_generation"].kind == "auxiliary"
    assert traffic["title_generation"].calls_per_run == 1
    assert traffic["future_aux"].kind == "auxiliary"
    review = traffic["background_review"]
    assert review.kind == "review"
    assert review.calls_per_run == 2
    assert review.context_per_call == 200
    assert review.cache_hit_rate == 0.75
    assert review.tokens_per_run.output_tokens == 20
    assert review.tokens_per_run.reasoning_tokens == 60
    assert review.tokens_per_run.cache_write_tokens == 40


def test_terminal_front_door_runs_diagnosis_and_displays_calls(tmp_path):
    home = make_hermes(tmp_path)
    result = subprocess.run(
        [sys.executable, "-m", "agent_lab.diagnosis", "--hermes-home", str(home),
         "--store", str(tmp_path / "artifacts")],
        input="stillroom-research\n2\n", text=True, capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    assert "Calls/run: 10" in result.stdout
    assert "Context/call: 17683.1" in result.stdout
    assert "Cache hit rate: 77.9%" in result.stdout
    assert "Tokens/run: input=39103 output=3591 cache_read=137728 cache_write=0 reasoning=656" in result.stdout
    assert "worker (main loop)" in result.stdout
    assert "auxiliary (title_generation)" in result.stdout
    assert "attributed sessions only" in result.stdout
    assert "stillroom-media-analyst" in result.stdout
    path = Path(result.stdout.split("Artifact: ")[1].strip())
    assert DiagnosisStore(tmp_path / "artifacts").load(path).calls_per_run == 10


def test_terminal_refuses_artifacts_inside_hermes(tmp_path):
    home = make_hermes(tmp_path)
    result = subprocess.run(
        [sys.executable, "-m", "agent_lab.diagnosis", "--hermes-home", str(home),
         "--store", str(home / "artifacts")],
        input="stillroom-research\n2\n", text=True, capture_output=True,
    )
    assert result.returncode != 0
    assert "outside Hermes" in result.stderr
    assert not (home / "artifacts").exists()


def test_measurement_is_runtime_neutral_and_sums_multiple_sessions(tmp_path):
    class OtherRuntime:
        def attribute(self, run_id: str) -> RunAttribution:
            return RunAttribution(run_id=run_id, runtime="other", role="researcher",
                                  session_ids=("a", "b"), workflow_identity="research")

    class OtherUsage:
        def usage(self, session_ids: tuple[str, ...]) -> tuple[UsageRow, ...]:
            assert session_ids == ("a", "b")
            tokens = TokenCounts(input_tokens=100, output_tokens=10, cache_read_tokens=300,
                                 cache_write_tokens=20, reasoning_tokens=30)
            return (UsageRow(session_id="a", task=None, calls=4, tokens=tokens),
                    UsageRow(session_id="b", task=None, calls=7, tokens=tokens))

    store = DiagnosisStore(tmp_path / "artifacts")
    result = diagnose("run", OtherRuntime(), OtherUsage(), store)
    assert store.load(result.path).calls_per_run == 11
    assert result.record.attribution.runtime == "other"
    assert result.record.tokens_per_run.input_tokens == 200
    assert result.record.tokens_per_run.reasoning_tokens == 60
    assert result.record.context_per_call == pytest.approx(72.7272727)
    assert result.record.cache_hit_rate == 0.75


@pytest.mark.parametrize("metadata", [None, "not-json", "[]", '{}', '{"worker_session_id": 123}'])
def test_unattributable_runs_fail_without_artifacts(tmp_path, metadata):
    home = make_hermes(tmp_path)
    with sqlite3.connect(home / "kanban/boards/stillroom-research/kanban.db") as db:
        db.execute("UPDATE task_runs SET metadata = ?", (metadata,))
    root = tmp_path / "artifacts"
    with pytest.raises(DiagnosisError):
        diagnose("2", KanbanAdapter(home, "stillroom-research"), HermesUsage(home), DiagnosisStore(root))
    assert not root.exists()


@pytest.mark.parametrize("count", [None, -1, 1.5, "unknown"])
def test_invalid_usage_is_not_silently_reported_as_cost(tmp_path, count):
    home = make_hermes(tmp_path)
    with sqlite3.connect(home / "profiles/stillroom-media-analyst/state.db") as db:
        db.execute("UPDATE session_model_usage SET api_call_count = ? WHERE task = ''", (count,))
    with pytest.raises(DiagnosisError):
        diagnose("2", KanbanAdapter(home, "stillroom-research"), HermesUsage(home),
                 DiagnosisStore(tmp_path / "artifacts"))


@pytest.mark.parametrize("field", ["input_tokens", "output_tokens", "cache_read_tokens",
                                   "cache_write_tokens", "reasoning_tokens"])
@pytest.mark.parametrize("value", [None, -1, 1.5, "unknown"])
def test_invalid_token_counters_fail_without_publishing_measurements(tmp_path, field, value):
    home = make_hermes(tmp_path)
    with sqlite3.connect(home / "profiles/stillroom-media-analyst/state.db") as db:
        db.execute(f"UPDATE session_model_usage SET {field}=? WHERE task='title_generation'", (value,))
    store = DiagnosisStore(tmp_path / "artifacts")
    with pytest.raises(DiagnosisError):
        diagnose("2", KanbanAdapter(home, "stillroom-research"), HermesUsage(home), store)
    assert not store.root.exists()


def test_missing_token_column_is_not_reported_as_zero(tmp_path):
    home = make_hermes(tmp_path)
    with sqlite3.connect(home / "profiles/stillroom-media-analyst/state.db") as db:
        db.execute("ALTER TABLE session_model_usage DROP COLUMN reasoning_tokens")
    with pytest.raises(DiagnosisError, match="reasoning_tokens"):
        diagnose("2", KanbanAdapter(home, "stillroom-research"), HermesUsage(home),
                 DiagnosisStore(tmp_path / "artifacts"))


def test_missing_usage_is_not_zero_but_an_explicit_zero_is_valid(tmp_path):
    home = make_hermes(tmp_path)
    profile = home / "profiles/stillroom-media-analyst/state.db"
    adapter, usage = KanbanAdapter(home, "stillroom-research"), HermesUsage(home)
    store = DiagnosisStore(tmp_path / "artifacts")
    with sqlite3.connect(profile) as db:
        db.execute("DELETE FROM session_model_usage")
    with pytest.raises(DiagnosisError, match="No usage rows"):
        diagnose("2", adapter, usage, store)
    assert not store.root.exists()
    with sqlite3.connect(profile) as db:
        db.execute("""INSERT INTO session_model_usage
                      (session_id, model, billing_provider, task, api_call_count)
                      VALUES ('20260914_093544_993097', 'm', 'p', '', 0)""")
    record = diagnose("2", adapter, usage, store).record
    assert record.calls_per_run == 0
    assert record.context_per_call is None
    assert record.cache_hit_rate is None
    assert record.tokens_per_run.input_tokens == 0
    assert record.traffic[0].context_per_call is None


def test_template_identity_and_legacy_session_link_are_preserved(tmp_path):
    home = make_hermes(tmp_path)
    with sqlite3.connect(home / "kanban/boards/stillroom-research/kanban.db") as db:
        db.execute("UPDATE tasks SET workflow_template_id = 'research-v1'")
        db.execute('UPDATE task_runs SET metadata = ?', (json.dumps({"session_id": "legacy"}),))
    result = KanbanAdapter(home, "stillroom-research").attribute("2")
    assert result.workflow_identity == "board:stillroom-research/template:research-v1"
    assert result.session_ids == ("legacy",)


def test_unknown_run_and_missing_database_fail_without_creating_a_database(tmp_path):
    home = make_hermes(tmp_path)
    with pytest.raises(DiagnosisError, match="not found"):
        KanbanAdapter(home, "stillroom-research").attribute("999")
    with pytest.raises(DiagnosisError):
        KanbanAdapter(home, "missing-board").attribute("2")
    assert not (home / "kanban/boards/missing-board").exists()


def test_calls_only_artifacts_remain_readable_without_inventing_token_measurements(tmp_path):
    import hashlib
    raw = json.dumps({
        "schema_version": 1, "observation_id": "old-observation",
        "observed_at": "2026-09-18T00:00:00Z", "calls_per_run": 10,
        "attribution": {"run_id": "2", "runtime": "kanban", "role": "media-analyst",
                        "session_ids": ["s"], "workflow_identity": "research"},
    }).encode()
    path = tmp_path / (hashlib.sha256(raw).hexdigest() + ".json")
    path.write_bytes(raw)
    record = DiagnosisStore(tmp_path).load(path)
    assert record.schema_version == 1
    assert record.calls_per_run == 10
    assert "tokens_per_run" not in record.model_dump()
    assert path.read_bytes() == raw


def test_artifact_tampering_is_detected_and_never_overwritten(tmp_path):
    home = make_hermes(tmp_path)
    store = DiagnosisStore(tmp_path / "artifacts")
    result = diagnose("2", KanbanAdapter(home, "stillroom-research"), HermesUsage(home), store)
    assert store.save(result.record).path == result.path  # saving the same observation is idempotent
    result.path.chmod(0o644)  # simulate external tampering, not an application write
    result.path.write_text("{}")
    with pytest.raises(DiagnosisError, match="digest mismatch"):
        store.load(result.path)
    with pytest.raises(DiagnosisError, match="does not match"):
        store.save(result.record)
    assert result.path.read_text() == "{}"


def test_store_rejects_a_workflow_directory_redirected_outside_the_store(tmp_path):
    home = make_hermes(tmp_path)
    store = DiagnosisStore(tmp_path / "artifacts", protected_roots=(home,))
    result = diagnose("2", KanbanAdapter(home, "stillroom-research"), HermesUsage(home), store)
    workflow = result.path.parent.parent
    workflow.rename(tmp_path / "saved-workflow")
    workflow.symlink_to(home, target_is_directory=True)
    with pytest.raises(DiagnosisError, match="outside"):
        diagnose("2", KanbanAdapter(home, "stillroom-research"), HermesUsage(home), store)
    assert not (home / "diagnoses").exists()


def test_store_rejects_redirect_into_hermes_even_when_hermes_is_inside_store(tmp_path):
    home = make_hermes(tmp_path)
    store = DiagnosisStore(tmp_path, protected_roots=(home,))
    result = diagnose("2", KanbanAdapter(home, "stillroom-research"), HermesUsage(home), store)
    workflow = result.path.parent.parent
    workflow.rename(tmp_path / "saved-workflow")
    workflow.symlink_to(home, target_is_directory=True)
    with pytest.raises(DiagnosisError, match="outside Hermes"):
        diagnose("2", KanbanAdapter(home, "stillroom-research"), HermesUsage(home), store)
    assert not (home / "diagnoses").exists()
