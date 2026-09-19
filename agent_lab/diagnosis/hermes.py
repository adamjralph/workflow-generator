"""Fresh-process, read-only Hermes bridge. No Hermes imports or initialization."""
from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from contextlib import closing
from pathlib import Path
from typing import Any

from . import DiagnosisError, RunAttribution, SessionCalls


def _read_db(path: Path) -> sqlite3.Connection:
    db = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA query_only=ON")
    return db


def _attribute(home: Path, board: str, run_id: str) -> RunAttribution:
    if not board or board in {".", ".."} or Path(board).name != board:
        raise DiagnosisError("Board must be a single directory name")
    with closing(_read_db(home / "kanban" / "boards" / board / "kanban.db")) as db:
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


def _calls(home: Path, sessions: tuple[str, ...]) -> tuple[SessionCalls, ...]:
    totals: dict[str, int] = {}
    for path in sorted((home / "profiles").glob("*/state.db")):
        with closing(_read_db(path)) as db:
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
        [sys.executable, "-m", "agent_lab.diagnosis.hermes"],
        input=json.dumps(request), text=True, capture_output=True, timeout=30,
    )
    if result.returncode:
        raise DiagnosisError(result.stderr.strip() or "Hermes reader failed")
    return json.loads(result.stdout)


class KanbanAdapter:
    def __init__(self, hermes_home: Path, board: str):
        self.home = hermes_home.resolve()
        self.board = board

    def attribute(self, run_id: str) -> RunAttribution:
        return RunAttribution.model_validate(_bridge({
            "operation": "attribute", "home": str(self.home), "board": self.board, "run_id": run_id,
        }))


class HermesUsage:
    def __init__(self, hermes_home: Path):
        self.home = hermes_home.resolve()

    def calls(self, session_ids: tuple[str, ...]) -> tuple[SessionCalls, ...]:
        rows = _bridge({"operation": "calls", "home": str(self.home), "sessions": session_ids})
        return tuple(SessionCalls.model_validate(row) for row in rows)


def main() -> None:
    try:
        request = json.load(sys.stdin)
        home = Path(request["home"])
        if request["operation"] == "attribute":
            result = _attribute(home, request["board"], request["run_id"])
            print(result.model_dump_json())
        elif request["operation"] == "calls":
            print(json.dumps([r.model_dump() for r in _calls(home, tuple(request["sessions"]))]))
        else:
            raise DiagnosisError("Unknown read operation")
    except (ValueError, sqlite3.Error, OSError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
