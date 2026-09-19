"""Append-only run log — the smallest thing that makes a run inspectable.

One JSON object per line. Never rewritten, only appended. Two consequences
that matter:

* A run can be read back exactly as it happened, including failures.
* A recorded judgment can be replayed later without calling the model again.

This deliberately does NOT try to be Temporal. It records what happened; it
does not drive resumption. That distinction is the whole lesson in report §1.
"""

from __future__ import annotations

import json
import fcntl
from dataclasses import asdict, dataclass, field, replace
from contextlib import contextmanager
from collections.abc import Iterator
from pathlib import Path
from typing import Any


@dataclass
class RunEvent:
    run_id: str
    seq: int
    node: str
    stage: str
    transition: str | None
    terminal: str | None
    detail: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, sort_keys=True)


class RunLog:
    """Append-only JSONL writer/reader.

    `ensure_ascii=False` keeps human-readable text readable; the file is
    always written as UTF-8 with LF endings, so a digest over its bytes is
    stable across platforms.
    """

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    @contextmanager
    def fresh_run(self, run_id: str) -> Iterator[None]:
        """Exclusive single-pass reference execution, not resume or scheduling.

        The sidecar only holds a lock; events still use append_next's allocator.
        Existing foundation callers do not opt into this restriction.
        """
        if not isinstance(run_id, str) or not run_id.strip():
            raise ValueError("run_id must be nonempty")
        path = self.path.resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.with_name(path.name + ".reference.lock").open("a") as handle:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise ValueError("A reference run is already active on this log") from exc
            try:
                if any(event.run_id == run_id for event in self.read()):
                    raise ValueError("Run identity already recorded; resume is unsupported")
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)

    def append(self, event: RunEvent) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(event.to_json() + "\n")

    def append_next(self, event: RunEvent) -> None:
        """Allocate this run's sequence and append in one file-locked operation.

        Allocation happens at completion, not before model work. Separate log
        instances/processes using this method share the same ordering boundary.
        `append` remains the explicit-sequence import/replay primitive.
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a+", encoding="utf-8", newline="\n") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            try:
                handle.seek(0)
                recorded = [json.loads(line) for line in handle.read().split("\n") if line.strip()]
                seq = 1 + max(
                    (row["seq"] for row in recorded if row["run_id"] == event.run_id),
                    default=-1,
                )
                handle.write(replace(event, seq=seq).to_json() + "\n")
                handle.flush()
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)

    def read(self) -> list[RunEvent]:
        """Every recorded event, in file order.

        Split on LF only. The writer pins newline to "\n", while
        `str.splitlines` also breaks on characters such as U+2028 — which are
        legal inside a JSON string, so splitting on them tears valid rows apart.
        """
        if not self.path.is_file():
            return []
        events: list[RunEvent] = []
        for line in self.path.read_text(encoding="utf-8").split("\n"):
            if line.strip():
                events.append(RunEvent(**json.loads(line)))
        return events

    def digest(self) -> str:
        """Digest of the exact recorded bytes — evidence, not interpretation."""
        import hashlib

        if not self.path.is_file():
            return ""
        return hashlib.sha256(self.path.read_bytes()).hexdigest()


def write_recording(
    path: Path,
    *,
    assessment: str,
    intervention: str,
    confidence: float,
    review_gap: float,
    usage: dict[str, int] | None = None,
) -> Path:
    """Freeze one live judgment to disk so it can be replayed deterministically."""
    import hashlib

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "assessment_sha": hashlib.sha256(assessment.encode("utf-8")).hexdigest(),
        "intervention": intervention,
        "confidence": confidence,
        "review_gap": review_gap,
        "usage": usage or {},
    }
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return path
