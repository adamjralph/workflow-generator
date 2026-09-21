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
from agent_lab.designer.vertex import VertexError, VertexUncertain, VertexSource
from agent_lab.designer import linkedin, linkedin_review
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


class AttemptBudget:
    """Separate generation allowance, never refunded after reservation or failure."""
    def __init__(self) -> None:
        self.operations: list[str] = []

    def reserve(self, operation: str) -> int:
        if len(self.operations) >= 2 or operation in self.operations:
            raise ValueError("Run model-attempt allowance exhausted")
        expected = ("draft_linkedin", "review_linkedin")[len(self.operations)]
        if operation != expected:
            raise ValueError("Model operations must run Generator then Guardian")
        self.operations.append(operation)
        return len(self.operations)


class AttemptSource:
    """Durable reservation and exact sanitized exchange BEFORE response application."""
    def __init__(self, source: ModelSource, evidence: Evidence, identity: dict[str, Any],
                 budget: AttemptBudget | None = None) -> None:
        self.source, self.evidence, self.identity = source, evidence, identity
        self.budget = budget
        self.auth_requests: int | None = 0
        self.reservation: str | None = None
        self.response: ModelResponse | None = None
        self.exchange: Path | None = None
        self.failure: ModelFailure | None = None
        self.used = False

    @property
    def mode(self) -> Literal["live", "fixture", "recorded"]:
        return self.source.mode

    def invoke(self, request: ModelRequest) -> ModelResponse:
        if self.used:
            raise ValueError("Role attempt exhausted")
        ordinal = self.budget.reserve(request.operation) if self.budget else 1
        self.used = True
        attempt = {"format_version": 2 if self.budget else 1, **self.identity, "ordinal": ordinal,
                   "request": request.model_dump(), "request_digest": request.digest,
                   "source_mode": self.mode, "limits": {"attempts": 2 if self.budget else 1,
                   "attempts_per_role": 1, "deadline_seconds": 180,
                   "response_bytes": 65536, "post_code_points": 3000,
                   "remote_token_cap": None, "remote_cancellation": False}}
        self.reservation = "attempt.json" if ordinal == 1 else "guardian-attempt.json"
        self.evidence.publish(self.reservation, canonical(attempt).encode())
        if ordinal == 2:
            # The first driver's transition must be recorded before another paid role.
            events = [json.loads(line) for line in self.evidence.read("run.jsonl").splitlines()]
            previous = json.loads(self.evidence.read("attempt.json"))
            if (len(events) != 1 or events[0].get("run_id") != self.identity["run_request"]
                    or events[0].get("node") != "generator" or events[0].get("transition") != "draft"
                    or events[0].get("detail", {}).get("target") != "guardian"
                    or events[0]["detail"].get("request_digest") != previous["request_digest"]
                    or events[0]["detail"].get("used_steps") != 1):
                raise ValueError("Generator audit evidence is incomplete")
        start = time.monotonic()
        try:
            response = validate_response(self.source.invoke(request))
            if len(response.body.encode("utf-8")) > 65536:
                raise ValueError("Oversized response")
        except Exception as exc:
            status = "uncertain" if isinstance(exc, TimeoutError) else "failed"
            code = "deadline_exceeded" if isinstance(exc, TimeoutError) else "source_failure"
            provider_status = None
            if isinstance(exc, (CodexError, CodexUncertain, VertexError, VertexUncertain)):
                code, provider_status = exc.code, exc.provider_status
            self.auth_requests = (exc.auth_requests if isinstance(exc, (VertexError, VertexUncertain))
                                  else None if self.mode == "live" and request.operation == "review_linkedin" else 0)
            self.failure = ModelFailure.model_validate({"status": status, "code": code,
                                                        "provider_status": provider_status})
            self.exchange = self.evidence.record({**attempt, "response": None,
                "failure": self.failure.model_dump(), "auth_requests": self.auth_requests,
                "elapsed_seconds": time.monotonic() - start})
            raise ValueError("Model source failed") from None
        self.auth_requests = response.auth_requests
        # Keep provenance separate from the semantic request/response, for exact replay.
        self.exchange = self.evidence.record({**attempt, "response": response.model_dump(),
            "response_digest": digest(response.body.encode("utf-8")), "failure": None,
            "elapsed_seconds": time.monotonic() - start})
        self.response = response
        return response


class DraftRuns:
    def __init__(self, source: DraftSource, evidence_dir: Path, model_source: ModelSource,
                 protected_roots: tuple[Path, ...] = (), *, guardian_source: ModelSource | None = None) -> None:
        self.source, self.model_source = source, model_source
        self.guardian_source = guardian_source
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

    def _execution_options(self) -> dict[str, Any]:
        return {"operations": {"draft_linkedin": [linkedin.VERSION, linkedin.SCHEMA_VERSION],
                               "review_linkedin": [linkedin_review.VERSION, linkedin_review.SCHEMA_VERSION]},
                "limits": {"workflow_steps": 2, "generation_attempts": 2, "attempts_per_role": 1,
                           "deadline_seconds_per_role": 180, "response_bytes": 65536,
                           "post_code_points": 3000, "provider_token_cap": None,
                           "remote_cancellation": False},
                "generator_mode": self.model_source.mode,
                "guardian_mode": self.guardian_source.mode if self.guardian_source else None,
                "guardian": (self.guardian_source.execution_options
                             if isinstance(self.guardian_source, VertexSource) else {})}

    def create_request(self, snapshot: str) -> dict[str, Any]:
        self.source.load(snapshot)
        identity: dict[str, Any] = {"snapshot": snapshot, "run_request": secrets.token_hex(32), "status": "ready"}
        if self.guardian_source is not None:
            identity["workflow_version"] = "linkedin-pair-v1"
            identity["execution_options"] = self._execution_options()
        root = self._directory()
        previously_attempted = False
        for prior in root.iterdir():
            if re.fullmatch("[0-9a-f]{64}", prior.name) and (prior / "claimed.json").exists():
                saved = json.loads(Evidence(prior).read("claimed.json"))
                if saved.get("snapshot") == snapshot:
                    previously_attempted = True
                    break
        directory = root / identity["run_request"]
        directory.mkdir(mode=0o700)
        _sync(root)
        store = Evidence(directory)
        store.publish("request.json", canonical(identity).encode())
        store.publish("claim.lock", b"")
        return {**identity, "previously_attempted": previously_attempted}

    def _view(self, snapshot: str, run_request: str, status: str) -> dict[str, Any]:
        messages = {"running": "Workflow request is running; repeat submissions do not send again.",
                    "completed": "Completed editorial review. No verdict authorizes publication or scheduling.",
                    "uncertain": "Incomplete evidence or timeout. Remote completion and usage may be unknown. No automatic retry.",
                    "failed": "Workflow failed validation, authentication or execution. Check the configured login/model and evidence; operator action required.",
                    "blocked": "Generator blocked before review; no review was performed.",
                    "not_reviewed": "Not reviewed. No Guardian review or publication permission."}
        return {"snapshot": snapshot, "run_request": run_request, "status": status,
                "succeeded": status in ("not_reviewed", "completed"), "result": None,
                "usage": dict.fromkeys(_USAGE), "evidence": [], "message": messages[status],
                "failure": (ModelFailure(status="uncertain", code="evidence_failure").model_dump()
                            if status == "uncertain" else None)}

    def run(self, snapshot: str, run_request: str) -> dict[str, Any]:
        _identifier(snapshot)
        _identifier(run_request)
        store = Evidence(self._directory() / run_request)
        identity = json.loads(store.read("request.json"))
        expected: dict[str, Any] = {"snapshot": snapshot, "run_request": run_request, "status": "ready"}
        paired = identity.get("workflow_version") == "linkedin-pair-v1"
        if paired:
            expected["workflow_version"] = "linkedin-pair-v1"
            expected["execution_options"] = identity.get("execution_options")
        if identity != expected:
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
            return (self._execute_pair(store, snapshot, run_request) if paired
                    else self._execute(store, snapshot, run_request))
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

    def _execute_pair(self, store: Evidence, snapshot: str, run_request: str) -> dict[str, Any]:
        """Fresh pairs only; legacy identities retain their original one-role path."""
        budget = AttemptBudget()
        identity = json.loads(store.read("request.json"))
        generator = AttemptSource(self.model_source, store, identity, budget)
        guardian = (AttemptSource(self.guardian_source, store, identity, budget)
                    if self.guardian_source is not None else None)
        attempts = {"generator": generator, **({"guardian": guardian} if guardian else {})}
        view = self._view(snapshot, run_request, "failed")
        view.update(review=None, draft_digest=None, attribution=[], used_steps=0,
                    generation_attempts=0, role_usage={}, auth_requests=0)
        state: linkedin_review.ReviewState | None = None
        log_path: Path | None = None
        try:
            if guardian is None or identity["execution_options"] != self._execution_options():
                raise ValueError("This pair requires unchanged explicit execution configuration")
            captured = self.source.load(snapshot)
            models = {item["role"]: item for item in captured["models"]}
            for role, provider in (("generator", "openai-codex"), ("guardian", "vertex")):
                if attempts[role].mode == "live" and models[role]["provider"] != provider:
                    raise ValueError("Captured provider differs; no substitution")
            if ((models["generator"]["provider"], models["generator"]["model"]) ==
                    (models["guardian"]["provider"], models["guardian"]["model"])):
                raise ValueError("Guardian must use a different model")
            for role, op, version, schema in (
                    ("generator", "draft_linkedin", linkedin.VERSION, linkedin.SCHEMA_VERSION),
                    ("guardian", "review_linkedin", linkedin_review.VERSION, linkedin_review.SCHEMA_VERSION)):
                view["attribution"].append({**models[role], "operation": op,
                    "operation_version": version, "schema_version": schema})
            state = linkedin_review.ReviewState(snapshot=snapshot, captured_json=canonical({
                key: captured[key] for key in ("selected", "guidance", "models", "instruction_version")}))
            compiled = generate_graph(linkedin_review.SPEC, state_type=linkedin_review.ReviewState,
                bindings={}, model_operations=linkedin_review.operations(generator, guardian))
            if compiled.candidate is None:
                raise ValueError("Unsupported reviewed workflow")
            store.publish("run.jsonl", b"")
            result = compiled.candidate.run(state, run_id=run_request, log=RunLog(store.directory / "run.jsonl"))
            state = result.state
            view["used_steps"] = result.used_steps
            log_bytes = store.read("run.jsonl")
            events = [json.loads(line) for line in log_bytes.splitlines()]
            if (len(events) != result.used_steps or not events
                    or [event["node"] for event in events] != ["generator", "guardian"][:result.used_steps]
                    or [event["seq"] for event in events] != list(range(result.used_steps))
                    or [event["detail"]["used_steps"] for event in events] != list(range(1, result.used_steps + 1))
                    or events[-1]["terminal"] != result.terminal):
                raise ValueError("Workflow audit evidence is incomplete")
            log_path = store.publish(digest(log_bytes) + ".jsonl", log_bytes)
            failure = guardian.failure or generator.failure
            status = ({"COMPLETED": "completed", "BLOCKED": "blocked"}.get(result.terminal)
                      or (failure.status if failure else "failed"))
            if any(item.used and item.exchange is None for item in attempts.values()):
                status = "uncertain"
            view.update({key: value for key, value in self._view(snapshot, run_request, status).items()
                         if key not in ("result", "usage", "evidence")})
            if failure is not None:
                view["failure"] = failure.model_dump()
                view["message"] += " Failure code: " + failure.code
            elif status == "failed":
                view["failure"] = ModelFailure(status="failed", code="invalid_output").model_dump()
        except Exception:
            status = "uncertain" if budget.operations else "failed"
            view.update({key: value for key, value in self._view(snapshot, run_request, status).items()
                         if key not in ("result", "usage", "evidence")})
            view["failure"] = ModelFailure.model_validate({"status": status, "code": (
                "evidence_failure" if budget.operations else "preflight_failed")}).model_dump()
        # Retain validated partial state and provenance even when Guardian or audit fails.
        if state is not None and state.result is not None:
            view["result"] = state.result.model_dump(mode="json")
            if state.result.post is not None:
                view["draft_digest"] = linkedin_review.draft_digest(state.result.post)
            if state.review is not None:
                view["review"] = state.review.model_dump(mode="json")
        view["generation_attempts"] = len(budget.operations)
        for role, item in attempts.items():
            view["role_usage"][role] = {key: getattr(item.response, key, None) for key in _USAGE}
            view["role_usage"][role]["auth_requests"] = item.auth_requests
        auth = [item.auth_requests for item in attempts.values()]
        view["auth_requests"] = None if None in auth else sum(count for count in auth if count is not None)
        # Legacy usage key remains Generator provenance, not a fabricated pair total.
        view["usage"] = {key: getattr(generator.response, key, None) for key in _USAGE}
        exchanges = [item.exchange.name for item in attempts.values() if item.exchange is not None]
        names = ["request.json", "claimed.json"]
        names += [item.reservation for item in attempts.values() if item.reservation is not None
                  and (store.directory / item.reservation).exists()]
        names += exchanges
        if log_path is not None:
            names.append(log_path.name)
        elif (store.directory / "run.jsonl").exists():
            names.append("run.jsonl")
        view["evidence"] = [str(store.directory / name) for name in names]
        view["evidence"].append(str(store.directory / "receipt.json"))
        try:
            receipt = {"format_version": 2, "view": view, "snapshot": snapshot,
                "draft_digest": view["draft_digest"], "review_digest": (
                    digest(canonical(view["review"]).encode()) if view["review"] is not None else None),
                "exchanges": exchanges, "digests": {name: digest(store.read(name)) for name in names}}
            store.publish("receipt.json", canonical(receipt).encode())
        except Exception:
            view.update(status="uncertain", succeeded=False,
                        message="Receipt publication failed; evidence is incomplete. No automatic retry.",
                        failure=ModelFailure(status="uncertain", code="evidence_failure").model_dump())
        return view
