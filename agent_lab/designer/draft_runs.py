"""Exclusive input-bound Generator attempts, never automatic retry or resume."""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import stat
import tempfile
import time
from typing import Any, Literal

from agent_lab.designer import validate_evidence_root
from agent_lab.designer.codex import CodexError, CodexUncertain
from agent_lab.designer.drafts import DraftSource
from agent_lab.designer.linkedin import DraftState, SPEC, canonical, operation
from agent_lab.generation import generate_graph
from agent_lab.model_operation import ModelFailure, ModelRequest, ModelResponse, ModelSource, validate_response
from agent_lab.runlog import RunLog

_LIMIT = 8 * 1024 * 1024
_USAGE = ("input_tokens", "output_tokens", "reasoning_tokens", "cache_read_tokens")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _identifier(value: str) -> None:
    if not isinstance(value, str) or re.fullmatch("[0-9a-f]{64}", value) is None:
        raise ValueError("Invalid captured run identity")


def _sync(directory: Path) -> None:
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


class Evidence:
    """Private atomic no-overwrite records under one pinned run directory."""
    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def check(self) -> None:
        info = self.directory.lstat()
        if (self.directory.resolve() != self.directory or not stat.S_ISDIR(info.st_mode)
                or info.st_mode & 0o077 or info.st_uid != os.getuid()):
            raise ValueError("Unsafe run evidence directory")

    def read(self, name: str) -> bytes:
        self.check()
        fd = os.open(self.directory / name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as handle:
            info = os.fstat(handle.fileno())
            if (not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077
                    or info.st_uid != os.getuid() or info.st_size > _LIMIT):
                raise ValueError("Unsafe run evidence record")
            data = handle.read(_LIMIT + 1)
            if len(data) > _LIMIT:
                raise ValueError("Oversized run evidence")
            return data

    def publish(self, name: str, data: bytes) -> Path:
        self.check()
        if len(data) > _LIMIT:
            raise ValueError("Oversized run evidence")
        fd, temporary = tempfile.mkstemp(dir=self.directory, prefix=".pending-")
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            self.check()
            path = self.directory / name
            os.link(temporary, path)
            try:
                _sync(self.directory)
            except OSError:
                # Publication is not complete until its directory entry is durable.
                # Do not leave a visible success receipt after a reported failure.
                os.unlink(path)
                raise
            return path
        finally:
            os.unlink(temporary)

    def record(self, value: object) -> Path:
        data = canonical(value).encode("utf-8")
        return self.publish(digest(data) + ".json", data)


class AttemptSource:
    """Durable reservation and exact sanitized exchange BEFORE response application."""
    def __init__(self, source: ModelSource, evidence: Evidence, identity: dict[str, Any]) -> None:
        self.source, self.evidence, self.identity = source, evidence, identity
        self.response: ModelResponse | None = None
        self.exchange: Path | None = None
        self.failure: ModelFailure | None = None
        self.used = False

    @property
    def mode(self) -> Literal["live", "fixture", "recorded"]:
        return self.source.mode

    def invoke(self, request: ModelRequest) -> ModelResponse:
        if self.used:
            raise ValueError("Generator attempt exhausted")
        self.used = True
        attempt = {"format_version": 1, **self.identity, "ordinal": 1,
                   "request": request.model_dump(), "request_digest": request.digest,
                   "source_mode": self.mode, "limits": {"attempts": 1, "deadline_seconds": 180,
                   "response_bytes": 65536, "post_code_points": 3000,
                   "remote_token_cap": None, "remote_cancellation": False}}
        self.evidence.publish("attempt.json", canonical(attempt).encode())
        start = time.monotonic()
        try:
            response = validate_response(self.source.invoke(request))
            if len(response.body.encode("utf-8")) > 65536:
                raise ValueError("Oversized response")
        except Exception as exc:
            status = "uncertain" if isinstance(exc, TimeoutError) else "failed"
            code = "deadline_exceeded" if isinstance(exc, TimeoutError) else "source_failure"
            provider_status = None
            if isinstance(exc, (CodexError, CodexUncertain)):
                code, provider_status = exc.code, exc.provider_status
            self.failure = ModelFailure.model_validate({"status": status, "code": code,
                                                        "provider_status": provider_status})
            self.exchange = self.evidence.record({**attempt, "response": None,
                "failure": self.failure.model_dump(), "elapsed_seconds": time.monotonic() - start})
            raise ValueError("Generator source failed") from None
        # Keep provenance separate from the semantic request/response, for exact replay.
        self.exchange = self.evidence.record({**attempt, "response": response.model_dump(),
            "response_digest": digest(response.body.encode("utf-8")), "failure": None,
            "elapsed_seconds": time.monotonic() - start})
        self.response = response
        return response


class DraftRuns:
    def __init__(self, source: DraftSource, evidence_dir: Path, model_source: ModelSource,
                 protected_roots: tuple[Path, ...] = ()) -> None:
        self.source, self.model_source = source, model_source
        self._protected = protected_roots
        self._root = validate_evidence_root(evidence_dir, protected_roots=protected_roots)

    def _directory(self) -> Path:
        if validate_evidence_root(self._root, protected_roots=self._protected) != self._root:
            raise ValueError("Evidence root changed")
        path = self._root / "draft-runs"
        if path.resolve() != path:
            raise ValueError("Run directory must not be a symlink")
        self._root.mkdir(parents=True, exist_ok=True, mode=0o700)
        path.mkdir(exist_ok=True, mode=0o700)
        Evidence(path).check()
        return path

    def create_request(self, snapshot: str) -> dict[str, Any]:
        self.source.load(snapshot)
        identity = {"snapshot": snapshot, "run_request": secrets.token_hex(32), "status": "ready"}
        root = self._directory()
        directory = root / identity["run_request"]
        directory.mkdir(mode=0o700)
        _sync(root)
        store = Evidence(directory)
        store.publish("request.json", canonical(identity).encode())
        store.publish("claim.lock", b"")
        return identity

    def _view(self, snapshot: str, run_request: str, status: str) -> dict[str, Any]:
        messages = {"running": "Generator request is running; repeat submissions do not send again.",
                    "uncertain": "Incomplete evidence or timeout. Remote completion and usage may be unknown. No automatic retry.",
                    "failed": "Generator failed validation, authentication or execution. Check the configured login/model and evidence; operator action required.",
                    "blocked": "Generator blocked before review; no review was performed.",
                    "not_reviewed": "Not reviewed. No Guardian review or publication permission."}
        return {"snapshot": snapshot, "run_request": run_request, "status": status,
                "succeeded": status == "not_reviewed", "result": None,
                "usage": dict.fromkeys(_USAGE), "evidence": [], "message": messages[status],
                "failure": (ModelFailure(status="uncertain", code="evidence_failure").model_dump()
                            if status == "uncertain" else None)}

    def run(self, snapshot: str, run_request: str) -> dict[str, Any]:
        _identifier(snapshot)
        _identifier(run_request)
        store = Evidence(self._directory() / run_request)
        identity = json.loads(store.read("request.json"))
        if identity != {"snapshot": snapshot, "run_request": run_request, "status": "ready"}:
            raise ValueError("Run request does not match capture")
        store.read("claim.lock")  # Validate type/ownership before opening the lock.
        fd = os.open(store.directory / "claim.lock", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return self._view(snapshot, run_request, "running")
            receipt_path = store.directory / "receipt.json"
            if receipt_path.exists():
                try:
                    receipt = json.loads(store.read("receipt.json"))
                    for name, expected in receipt["digests"].items():
                        if Path(name).name != name or digest(store.read(name)) != expected:
                            raise ValueError("Changed run evidence")
                    return dict(receipt["view"])
                except (ValueError, OSError, KeyError, TypeError):
                    return self._view(snapshot, run_request, "uncertain")
            if (store.directory / "claimed.json").exists():
                return self._view(snapshot, run_request, "uncertain")
            # Durable exclusive claim precedes even preflight. Never automatically re-enter it.
            store.publish("claimed.json", canonical(identity).encode())
            return self._execute(store, snapshot, run_request)
        finally:
            os.close(fd)

    def _execute(self, store: Evidence, snapshot: str, run_request: str) -> dict[str, Any]:
        view = self._view(snapshot, run_request, "failed")
        attempt = AttemptSource(self.model_source, store, {"snapshot": snapshot, "run_request": run_request})
        try:
            captured = self.source.load(snapshot)
            if self.model_source.mode == "live" and captured["models"][0]["provider"] != "openai-codex":
                raise ValueError("Generator requires configured Codex provider; no substitution")
            initial = DraftState(snapshot=snapshot, captured_json=canonical({key: captured[key] for key in
                ("selected", "guidance", "models", "instruction_version")}))
            compiled = generate_graph(SPEC, state_type=DraftState, bindings={},
                                      model_operations={"draft_linkedin": operation(attempt)})
            if compiled.candidate is None:
                raise ValueError("Unsupported Generator operation")
            # Precreate owner-only log; graph owns accounting and transitions.
            store.publish("run.jsonl", b"")
            log = RunLog(store.directory / "run.jsonl")
            result = compiled.candidate.run(initial, run_id=run_request, log=log)
            # A durable immutable copy binds all deterministic accounting evidence.
            log_bytes = store.read("run.jsonl")
            log_path = store.publish(digest(log_bytes) + ".jsonl", log_bytes)
            status = ({"NOT_REVIEWED": "not_reviewed", "BLOCKED": "blocked"}.get(result.terminal)
                      or (attempt.failure.status if attempt.failure else "failed"))
            # Evidence failure after reservation is uncertain, not successful application.
            if attempt.used and attempt.exchange is None:
                status = "uncertain"
            view = self._view(snapshot, run_request, status)
            if attempt.failure is not None:
                view["failure"] = attempt.failure.model_dump()
                view["message"] += " Failure code: " + attempt.failure.code
            elif status == "failed":
                view["failure"] = ModelFailure(status="failed", code="invalid_output").model_dump()
            if result.state.result is not None and status in ("not_reviewed", "blocked"):
                view["result"] = result.state.result.model_dump(mode="json")
            if attempt.response is not None:
                view["usage"] = {key: getattr(attempt.response, key) for key in _USAGE}
            view["evidence"] = [str(log_path)]
            if attempt.exchange:
                view["evidence"].append(str(attempt.exchange))
        except Exception:
            view = self._view(snapshot, run_request, "uncertain" if attempt.used else "failed")
            if not attempt.used:
                view["failure"] = ModelFailure(status="failed", code="preflight_failed").model_dump()
        try:
            names = ["request.json", "claimed.json"]
            if (store.directory / "attempt.json").exists():
                names.append("attempt.json")
            names += [Path(path).name for path in view["evidence"]]
            view["evidence"] += [str(store.directory / name) for name in names[:2]]
            view["evidence"].append(str(store.directory / "receipt.json"))
            receipt = {"format_version": 1, "view": view,
                       "digests": {name: digest(store.read(name)) for name in names}}
            store.publish("receipt.json", canonical(receipt).encode())
        except Exception:
            return self._view(snapshot, run_request, "uncertain")
        return view
