"""Read-only proof at the diagnosis entry point, using isolated Hermes homes."""
import hashlib
import importlib.util
import json
import os
import shutil
import sqlite3
import subprocess
import sys

import pytest
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace

from agent_lab.diagnosis import diagnose
from agent_lab.diagnosis.hermes import HermesUsage, KanbanAdapter
from agent_lab.diagnosis.store import DiagnosisStore
from test_diagnosis import make_hermes


def tree_digest(root: Path) -> dict[str, str]:
    """Include names and empty directories, not only known application files."""
    return {
        str(path.relative_to(root)): (
            hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "directory"
        )
        for path in sorted(root.rglob("*"))
    }


def protect_fixture(home: Path) -> None:
    for name, content in {
        "hermes-agent/source.py": "raise RuntimeError('must not import Hermes')\n",
        "config.yaml": "model: sentinel\n",
        "auth.json": '{"fake": "credential"}\n',
        "profiles/stillroom-media-analyst/config.yaml": "model: sentinel\n",
        "profiles/stillroom-media-analyst/SOUL.md": "Untouched role\n",
    }.items():
        path = home / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)


def test_fresh_home_diagnosis_preserves_every_byte_including_uncheckpointed_wal(tmp_path):
    home = make_hermes(tmp_path)
    protect_fixture(home)
    profile = home / "profiles/stillroom-media-analyst/state.db"
    # Produce a valid DB + committed WAL without a shared-memory file, as may
    # remain after another process exits. Connecting mode=ro creates -shm here.
    writer_path = tmp_path / "writer.db"
    shutil.copyfile(profile, writer_path)
    with closing(sqlite3.connect(writer_path)) as writer:
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute("UPDATE session_model_usage SET api_call_count=12 WHERE task=''")
        writer.commit()
        shutil.copyfile(writer_path, profile)
        shutil.copyfile(Path(str(writer_path) + "-wal"), Path(str(profile) + "-wal"))
        before = tree_digest(home)
        store = DiagnosisStore(tmp_path / "new-store", protected_roots=(home,))
        assert not store.root.exists()
        result = diagnose("2", KanbanAdapter(home, "stillroom-research"), HermesUsage(home), store)
        assert result.record.calls_per_run == 13  # WAL's 12 + auxiliary 1, not stale 10
        assert store.load(result.path) == result.record
        assert tree_digest(home) == before


@pytest.mark.parametrize("operation", ["attribute", "usage", "write"])
def test_adapter_has_no_live_write_path_with_open_wal_databases(tmp_path, operation):
    home = make_hermes(tmp_path)
    protect_fixture(home)
    guard_dir = tmp_path / "guard"
    guard_dir.mkdir()
    shutil.copyfile(Path(__file__).with_name("read_only_guard.py"), guard_dir / "sitecustomize.py")
    env = dict(os.environ, READ_ONLY_ROOT=str(home), PYTHONDONTWRITEBYTECODE="1",
               PYTHONPATH=os.pathsep.join((str(guard_dir), str(Path.cwd()))))
    profile = home / "profiles/stillroom-media-analyst/state.db"
    with closing(sqlite3.connect(profile)) as writer:
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute("UPDATE session_model_usage SET api_call_count=12 WHERE task=''")
        writer.commit()
        before = tree_digest(home)
        request = {"operation": operation, "home": str(home), "board": "stillroom-research",
                   "run_id": "2", "sessions": ["20260914_093544_993097"]}
        result = subprocess.run(
            [sys.executable, "-B", "-m", "agent_lab.diagnosis.hermes"],
            input=json.dumps(request), text=True, capture_output=True, env=env, timeout=30,
        )
        if operation == "write":
            assert result.returncode != 0
            assert "Unknown read operation" in result.stderr
        else:
            assert result.returncode == 0, result.stderr
            record = json.loads(result.stdout)
            if operation == "usage":
                assert {row["session_id"] for row in record} == {"20260914_093544_993097"}
                assert sum(row["calls"] for row in record) == 13
                assert sum(row["tokens"]["input_tokens"] for row in record) == 39103
            else:
                assert record["run_id"] == "2"
        assert tree_digest(home) == before
        # Negative controls prove the guard is installed and catches both kinds
        # of source-write path, rather than merely observing a successful read.
        for attempt in [
            "from pathlib import Path; Path('auth.json').write_text('bad')",
            "import sqlite3; sqlite3.connect('file:profiles/stillroom-media-analyst/state.db?mode=ro', uri=True)",
        ]:
            denied = subprocess.run([sys.executable, "-B", "-c", attempt], cwd=home,
                                    env=env, capture_output=True, text=True, timeout=30)
            assert denied.returncode != 0
            assert "PermissionError" in denied.stderr
        assert tree_digest(home) == before


def test_local_plugin_install_registration_and_invocation_leave_protected_tree_unchanged(tmp_path, monkeypatch):
    home = make_hermes(tmp_path)
    protect_fixture(home)
    before_install = tree_digest(home)
    source = tmp_path / "separate-hermes-source"
    source.mkdir()
    monkeypatch.setitem(sys.modules, "hermes_cli", SimpleNamespace(__file__=str(source / "hermes_cli/__init__.py")))
    # Local directory plugins are linked into the supported discovery location;
    # no pip install, config edits, credentials, or copied core implementation.
    plugins = home / "plugins"
    plugins.mkdir()
    installed = plugins / "workflow-diagnosis"
    installed.symlink_to(Path(__file__).resolve().parents[1] / "plugins/workflow-diagnosis",
                         target_is_directory=True)
    spec = importlib.util.spec_from_file_location("diagnosis_plugin", installed / "__init__.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    registered = {}

    def register_command(name, handler, **metadata):
        registered[name] = handler

    module.register(SimpleNamespace(register_command=register_command))
    assert set(registered) == {"workflow-diagnose", "workflow-report"}
    before_run = tree_digest(home)
    import shlex
    store = tmp_path / "new artifacts"
    output = registered["workflow-diagnose"](shlex.join([
        str(home), "stillroom-research", "2", str(store),
    ]))
    assert "Calls/run: 10" in output
    assert "Context/call: 17683.1" in output
    assert "reasoning=656" in output
    assert "auxiliary (title_generation)" in output
    assert "Cache hit rate: 77.9%" in output
    assert len(list(store.rglob("*.json"))) == 1
    manifest = tmp_path / "runs.json"
    manifest.write_text('[{"board":"stillroom-research","run_id":"2"}]')
    report = registered["workflow-report"](shlex.join([
        str(home), str(manifest), "team", str(store),
    ]))
    assert "Role: stillroom-media-analyst" in report
    assert "No measured baseline" in report
    assert len(list(store.rglob("*.json"))) == 3
    assert tree_digest(home) == before_run
    assert {k: v for k, v in tree_digest(home).items() if not k.startswith("plugins")} == before_install
    refused = registered["workflow-diagnose"](shlex.join([
        str(home), "stillroom-research", "2", str(source / "artifacts"),
    ]))
    assert "outside Hermes" in refused
    assert not (source / "artifacts").exists()
    refused_report = registered["workflow-report"](shlex.join([
        str(home), str(manifest), "team", str(source / "artifacts"),
    ]))
    assert "outside Hermes" in refused_report
    assert not (source / "artifacts").exists()


def test_unsafe_temporary_directory_is_rejected_without_even_probing_it(tmp_path):
    home = make_hermes(tmp_path)
    temporary = home / "temporary"
    temporary.mkdir()
    before = temporary.stat().st_mtime_ns
    result = subprocess.run(
        [sys.executable, "-B", "-m", "agent_lab.diagnosis.hermes"],
        input=json.dumps({"operation": "attribute", "home": str(home),
                          "board": "stillroom-research", "run_id": "2"}),
        env=dict(os.environ, TMPDIR=str(temporary)), capture_output=True, text=True, timeout=30,
    )
    assert result.returncode != 0
    assert "outside Hermes" in result.stderr
    assert temporary.stat().st_mtime_ns == before


def test_terminal_protects_a_separately_installed_hermes_source_tree(tmp_path):
    home = make_hermes(tmp_path)
    source = tmp_path / "hermes-source"
    source.mkdir()
    (source / "sentinel.py").write_text("# Hermes source\n")
    before = tree_digest(source)
    result = subprocess.run(
        [sys.executable, "-B", "-m", "agent_lab.diagnosis", "--hermes-home", str(home),
         "--protected-root", str(source), "--store", str(source / "artifacts")],
        input="stillroom-research\n2\n", capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 1
    assert "outside Hermes" in result.stderr
    assert tree_digest(source) == before


def test_store_refuses_the_tool_source_tree():
    from agent_lab.diagnosis import DiagnosisError
    with pytest.raises(DiagnosisError, match="outside Hermes"):
        DiagnosisStore(Path(__file__).resolve().parents[1] / "artifacts")


@pytest.mark.parametrize("problem", ["rollback-journal", "changing-source"])
def test_unstable_database_fails_closed_and_cleans_temporary_copies(tmp_path, problem):
    home = make_hermes(tmp_path)
    temporary = tmp_path / "snapshots"
    temporary.mkdir()
    source = home / "kanban/boards/stillroom-research/kanban.db"
    if problem == "rollback-journal":
        Path(str(source) + "-journal").write_bytes(b"unrecovered journal")
    # Simulate a writer changing metadata during every copy, at the filesystem
    # boundary. No diagnosis internals are patched or called by this test.
    script = """
import os
import runpy
import sys
from pathlib import Path
source = Path(sys.argv[1])
def concurrent_writer(event, args):
    if event == 'shutil.copyfile' and Path(args[0]) == source:
        info = source.stat()
        os.utime(source, ns=(info.st_atime_ns, info.st_mtime_ns + 1000000))
if sys.argv[2] == 'changing-source':
    sys.addaudithook(concurrent_writer)
runpy.run_module('agent_lab.diagnosis.hermes', run_name='__main__')
"""
    result = subprocess.run(
        [sys.executable, "-B", "-c", script, str(source), problem],
        input=json.dumps({"operation": "attribute", "home": str(home),
                          "board": "stillroom-research", "run_id": "2"}),
        env=dict(os.environ, TMPDIR=str(temporary)), capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 1
    assert ("rollback journal" if problem == "rollback-journal" else "changed during snapshot") in result.stderr
    assert list(temporary.iterdir()) == []
