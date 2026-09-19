"""Fresh-process, read-only Hermes bridge. No Hermes imports or initialization."""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from contextlib import closing, contextmanager
from pathlib import Path
from typing import Any

from . import DiagnosisError, RunAttribution, SessionCalls


def _signature(path: Path) -> tuple[int, int, int, int, int] | None:
    try:
        info = path.stat()
    except FileNotFoundError:
        return None
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


@contextmanager
def _read_db(path: Path, home: Path, protected_roots: tuple[Path, ...]) -> Iterator[sqlite3.Connection]:
    # mode=ro still writes SQLite's WAL shared-memory bookkeeping. Never hand
    # SQLite a live path: copy DB + WAL using ordinary read-only file access.
    path = path.resolve()
    # Do not call gettempdir(): it probes candidates by writing before validation.
    temporary_root = Path(os.environ.get("TMPDIR") or os.environ.get("TEMP")
                          or os.environ.get("TMP") or "/tmp").resolve()
    protected: tuple[Path, ...] = (home.resolve(), path.parent, (Path.home() / ".hermes").resolve(),
                 Path(__file__).resolve().parents[2], *protected_roots)
    if configured := os.environ.get("HERMES_HOME"):
        protected += (Path(configured).resolve(),)
    if any(temporary_root.is_relative_to(root) for root in protected):
        raise DiagnosisError("Snapshot temporary directory must be outside Hermes and source")
    wal = Path(str(path) + "-wal")
    journal = Path(str(path) + "-journal")
    for _ in range(3):
        before = tuple(_signature(p) for p in (path, wal, journal))
        if before[0] is None:
            raise DiagnosisError(f"Database does not exist: {path}")
        if before[2] is not None and before[2][2]:
            raise DiagnosisError("Database has a rollback journal; retry after recovery by Hermes")
        with tempfile.TemporaryDirectory(prefix="workflow-diagnosis-", dir=temporary_root) as directory:
            snapshot = Path(directory) / "snapshot.db"
            try:
                shutil.copyfile(path, snapshot)
                if before[1] is not None:
                    shutil.copyfile(wal, Path(str(snapshot) + "-wal"))
            except FileNotFoundError:
                continue  # a writer/checkpoint changed the source during the copy
            if before != tuple(_signature(p) for p in (path, wal, journal)):
                continue
            with closing(sqlite3.connect(snapshot.as_uri() + "?mode=ro", uri=True)) as db:
                db.row_factory = sqlite3.Row
                db.execute("PRAGMA query_only=ON")
                yield db
            return
    raise DiagnosisError("Database changed during snapshot; retry diagnosis")


def _attribute(home: Path, board: str, run_id: str, protected: tuple[Path, ...]) -> RunAttribution:
    if not board or board in {".", ".."} or Path(board).name != board:
        raise DiagnosisError("Board must be a single directory name")
    with _read_db(home / "kanban" / "boards" / board / "kanban.db", home, protected) as db:
        row = db.execute(
            """SELECT r.profile, r.metadata, r.task_id, t.workflow_template_id
               FROM task_runs r JOIN tasks t ON t.id = r.task_id WHERE r.id = ?""",
            (run_id,),
        ).fetchone()
    if row is None:
        raise DiagnosisError(f"Run {run_id!r} not found on board {board!r}")
    metadata = json.loads(row["metadata"] or "{}")
    if not isinstance(metadata, dict):
        raise DiagnosisError("Run metadata must be an object")
    session = metadata.get("worker_session_id") or metadata.get("session_id")
    if not isinstance(session, str) or not session.strip():
        raise DiagnosisError("Run has no recorded worker session")
    template = row["workflow_template_id"]
    identity = f"board:{board}/template:{template}" if template else f"board:{board}/task:{row['task_id']}"
    return RunAttribution(run_id=run_id, runtime="kanban", role=row["profile"],
                          session_ids=(session,), workflow_identity=identity)


def _calls(home: Path, sessions: tuple[str, ...], protected: tuple[Path, ...]) -> tuple[SessionCalls, ...]:
    totals: dict[str, int] = {}
    for path in sorted((home / "profiles").glob("*/state.db")):
        with _read_db(path, home, protected) as db:
            for session in sessions:
                rows = db.execute(
                    "SELECT api_call_count FROM session_model_usage WHERE session_id = ?",
                    (session,),
                ).fetchall()
                for row in rows:
                    # A missing/null counter is not evidence of zero cost.
                    count = SessionCalls(session_id=session, calls=row["api_call_count"])
                    totals[session] = totals.get(session, 0) + count.calls
    if set(totals) != set(sessions):
        raise DiagnosisError("No usage rows for one or more attributed sessions")
    return tuple(SessionCalls(session_id=s, calls=totals[s]) for s in sessions)


def _bridge(request: dict[str, Any]) -> Any:
    result = subprocess.run(
        [sys.executable, "-B", "-m", "agent_lab.diagnosis.hermes"],
        input=json.dumps(request), text=True, capture_output=True, timeout=30,
    )
    if result.returncode:
        raise DiagnosisError(result.stderr.strip() or "Hermes reader failed")
    return json.loads(result.stdout)


class KanbanAdapter:
    def __init__(self, hermes_home: Path, board: str, *, protected_roots: tuple[Path, ...] = ()):
        self.home = hermes_home.resolve()
        self.board = board
        self.protected_roots = [str(path.resolve()) for path in protected_roots]

    def attribute(self, run_id: str) -> RunAttribution:
        return RunAttribution.model_validate(_bridge({
            "operation": "attribute", "home": str(self.home), "board": self.board, "run_id": run_id,
            "protected_roots": self.protected_roots,
        }))


class HermesUsage:
    def __init__(self, hermes_home: Path, *, protected_roots: tuple[Path, ...] = ()):
        self.home = hermes_home.resolve()
        self.protected_roots = [str(path.resolve()) for path in protected_roots]

    def calls(self, session_ids: tuple[str, ...]) -> tuple[SessionCalls, ...]:
        rows = _bridge({"operation": "calls", "home": str(self.home), "sessions": session_ids,
                        "protected_roots": self.protected_roots})
        return tuple(SessionCalls.model_validate(row) for row in rows)


def main() -> None:
    try:
        request = json.load(sys.stdin)
        home = Path(request["home"])
        protected = tuple(Path(p).resolve() for p in request.get("protected_roots", []))
        if request["operation"] == "attribute":
            result = _attribute(home, request["board"], request["run_id"], protected)
            print(result.model_dump_json())
        elif request["operation"] == "calls":
            print(json.dumps([r.model_dump() for r in _calls(home, tuple(request["sessions"]), protected)]))
        else:
            raise DiagnosisError("Unknown read operation")
    except (ValueError, sqlite3.Error, OSError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
