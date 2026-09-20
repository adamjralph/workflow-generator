"""One operator-selected read-only brief and private digest-addressed snapshots."""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from pathlib import Path
from typing import Any, Callable

from agent_lab.conformance import check_conformance

from . import Design, generate_candidate, report_view, validate_evidence_root
from .custom import execute_request
from .roles import RoleState, WritingBrief, author_roles


def _regular_bytes(path: Path) -> bytes:
    # Nonblocking open avoids hanging on FIFOs, even if replaced after stat.
    if not stat.S_ISREG(path.lstat().st_mode):
        raise ValueError("Input must be a regular file, not a symlink or device")
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as handle:
        if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
            raise ValueError("Input must be a regular file")
        data = handle.read(4097)
    if len(data) > 4096:
        raise ValueError("Input exceeds 4 KiB")
    return data


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def _brief(data: bytes) -> WritingBrief:
    text = data.decode("utf-8")
    json.loads(text, object_pairs_hook=_unique_object)
    # JSON validation admits arrays as tuples but retains strict field types.
    return WritingBrief.model_validate_json(text)


class ControlledSource:
    """Paths are trusted operator configuration, never browser input."""

    def __init__(self, source_path: Path, evidence_dir: Path,
                 protected_roots: tuple[Path, ...] = ()) -> None:
        self._source = Path(source_path).expanduser().absolute()
        self._protected = protected_roots
        self._root = validate_evidence_root(Path(evidence_dir), protected_roots=protected_roots)
        self._check_overlap()

    def _check_overlap(self) -> None:
        source = self._source.resolve()
        if source.is_relative_to(self._root) or self._root.is_relative_to(source):
            raise ValueError("Source and evidence destination must not overlap")

    def _snapshot_directory(self) -> Path:
        root = validate_evidence_root(self._root, protected_roots=self._protected)
        directory = self._root / "snapshots"
        if root != self._root or directory.resolve() != directory:
            raise ValueError("Snapshot store must remain inside the protected evidence root")
        return directory

    def run(self, raw_design: object, snapshot: str, *,
            candidate_factory: Callable[[Design], object] = generate_candidate) -> dict[str, Any]:
        """Run the graph only, using a verified snapshot without opening the source."""
        design = author_roles(raw_design)
        brief = self._load(snapshot)
        result = execute_request(design, brief, RoleState(brief=brief),
                                 evidence_dir=self._root, candidate_factory=candidate_factory,
                                 protected_roots=self._protected)
        return {**result, "source": "Local writing brief", "snapshot": snapshot}

    def check(self, raw_design: object, snapshot: str, *,
              candidate_factory: Callable[[Design], object] = generate_candidate) -> dict[str, Any]:
        """Compare independent plain and generated executions of one captured case."""
        design = author_roles(raw_design)
        brief = self._load(snapshot)
        report = check_conformance(design.spec, candidate_factory(design),
                                   state_type=design.state_type, bindings=design.bindings,
                                   cases={"captured_input": RoleState(brief=brief)},
                                   evidence_dir=self._root, protected_roots=self._protected)
        return {**report_view(report, ("captured_input",)), "source": "Local writing brief",
                "snapshot": snapshot, "input": brief.model_dump(mode="json")}

    def _load(self, snapshot: str) -> WritingBrief:
        if not isinstance(snapshot, str) or re.fullmatch(r"[0-9a-f]{64}", snapshot) is None:
            raise ValueError("Invalid snapshot digest")
        data = _regular_bytes(self._snapshot_directory() / f"{snapshot}.json")
        if hashlib.sha256(data).hexdigest() != snapshot:
            raise ValueError("Corrupt snapshot: digest mismatch")
        return _brief(data)

    def capture(self) -> dict[str, Any]:
        """Capture exact bounded UTF-8 bytes; identical recaptures reuse their digest."""
        self._check_overlap()
        directory = self._snapshot_directory()
        data = _regular_bytes(self._source)
        brief = _brief(data)
        digest = hashlib.sha256(data).hexdigest()
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{digest}.json"
        try:
            with path.open("xb") as handle:
                handle.write(data)
        except FileExistsError:
            self._load(digest)
        return {"source": "Local writing brief", "snapshot": digest,
                "input": brief.model_dump(mode="json")}
