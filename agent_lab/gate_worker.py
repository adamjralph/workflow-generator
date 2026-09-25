"""Owned Gate worker. Executed only from the retained read-only runtime.

No caller functions, pickles, expressions, or user-selected schemas are loaded.
The plain and graph schedulers below intentionally do not call one another.
"""
import sys
sys.path.insert(0, "/deps")

import hashlib
import hmac
import fcntl
import stat
import json
import os
from pathlib import Path
import secrets
from typing import Any, cast

from pydantic_graph import GraphBuilder, StepContext


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def attest(request: dict[str, Any] | None = None) -> dict[str, Any]:
    manifest = json.loads(Path("/app/manifest.json").read_bytes())
    spec_digest = sha(b"workflow-generator/gate-spec/v1\0" + Path("/app/spec.json").read_bytes())
    ops_digest = sha(b"workflow-generator/gate-operations/v1\0" + Path("/app/operations.json").read_bytes())
    bundle_digest = sha(b"workflow-generator/gate-bundle/v1\0" + canonical(manifest))
    if (spec_digest != manifest["spec_digest"] or ops_digest != manifest["operations_digest"]
            or (request is not None and (request["spec_digest"] != spec_digest or request["bundle_digest"] != bundle_digest))):
        raise ValueError("Runtime spec/bundle identity mismatch")
    excluded = []
    for name in ("_tkinter", "tkinter"):
        try:
            __import__(name)
        except ModuleNotFoundError:
            excluded.append(name)
        else:
            raise ValueError("Unadmitted optional import is available")
    known = manifest["files"]
    for name, row in known.items():
        raw = Path(name).read_bytes()
        if sha(raw) != row["sha256"] or len(raw) != row["size"]:
            raise ValueError("Executable runtime bytes changed")
    unknown = []
    modules = {}
    native = {}
    for module in list(sys.modules.values()):
        origin = getattr(getattr(module, "__spec__", None), "origin", None)
        if origin is None:
            origin = getattr(module, "__file__", None)
        if origin and origin not in {"built-in", "frozen"}:
            if origin not in known:
                unknown.append(origin)
            else:
                modules[origin] = sha(Path(origin).read_bytes())
    for line in Path("/proc/self/maps").read_text().splitlines():
        fields = line.split()
        if len(fields) >= 6 and fields[5].startswith("/"):
            origin = fields[5]
            if origin not in known:
                unknown.append(origin)
            else:
                native[origin] = sha(Path(origin).read_bytes())
    if unknown:
        raise ValueError("Unverified loaded origins: " + repr(sorted(set(unknown))))
    return {"retained_runtime": True, "unverified_origins": [], "pid": os.getpid(),
            "modules": modules, "native": native, "excluded_imports": excluded,
            "spec_digest": spec_digest, "bundle_digest": bundle_digest}


class Execution:
    def __init__(self, request: dict[str, Any]) -> None:
        self.spec = json.loads(Path("/app/spec.json").read_bytes())["spec"]
        self.ops = json.loads(Path("/app/operations.json").read_bytes())["operations"]
        attest(request)
        self.request = request
        recovering = request.get("recovery", False)
        if type(recovering) is not bool:
            raise ValueError("Invalid recovery mode")
        self.operator_key = (self.read_operator_key() if recovering else secrets.token_bytes(32)) if request["mode"] == "operator" else None
        if self.operator_key is not None and not recovering:
            fd = os.open("/run/operator.key", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o400)
            with os.fdopen(fd, "wb") as stream:
                stream.write(self.operator_key)
                stream.flush()
                os.fsync(stream.fileno())
        self.value = 0
        self.used = 0
        self.events: list[dict[str, Any]] = []
        self.checkpoint: dict[str, Any] | None = None
        self.decision: dict[str, Any] | None = None
        self.resolved = False
        self.terminal = "PENDING"
        self.journal: list[bytes] = []
        self.sequence = 0
        self.head = "0" * 64
        self.event_head = "0" * 64
        self.nodes = {node["id"]: node for node in self.spec["nodes"]}
        self.routes = {(edge["source"], edge["outcome"]): edge["target"] for edge in self.spec["edges"]}

    @staticmethod
    def read_operator_key() -> bytes:
        fd = os.open("/run/operator.key", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
                raise ValueError("Unsafe operator authority")
            key = stream.read(33)
        if len(key) != 32:
            raise ValueError("Invalid operator authority")
        return key

    def load_pause(self) -> None:
        """Reconstruct only the committed prefix; host separately checks semantics."""
        if self.request["mode"] != "operator" or self.operator_key is None:
            raise ValueError("Only operator pauses can restart")
        paths = sorted(Path("/run").glob("[0-9]*.json"))
        if (not 2 <= len(paths) <= 2 * self.spec["budget"] or len(paths) % 2
                or [p.name for p in paths] != [f"{i:08}.json" for i in range(len(paths))]):
            raise ValueError("Not an untouched committed pause")
        previous = "0" * 64
        event_head = "0" * 64
        for i, path in enumerate(paths):
            raw = path.read_bytes()
            row = json.loads(raw)
            if (raw != canonical(row) or set(row) != {"version", "sequence", "previous", "kind", "run_id", "data"}
                    or row["version"] != 1 or row["sequence"] != i
                    or row["run_id"] != self.request["run_id"] or row["previous"] != previous
                    or row["kind"] != ("claim" if i % 2 == 0 else "completed")):
                raise ValueError("Altered recovery event chain")
            if i % 2:
                data = row["data"]
                event = data["event"]
                event_head = sha(b"workflow-generator/gate-event/v1\0" + event_head.encode() + canonical(event))
                if data["completed_head"] != event_head:
                    raise ValueError("Altered event head")
                self.events.append(event)
            self.journal.append(raw)
            previous = sha(raw)
        pending = json.loads(self.journal[-1])["data"]
        unsigned = {key: value for key, value in pending.items() if key != "pause_proof"}
        proof = hmac.digest(self.operator_key, b"workflow-generator/gate-pause/v1\0" +
                            canonical({"previous": json.loads(self.journal[-1])["previous"],
                                       "data": unsigned}), "sha256").hex()
        if not hmac.compare_digest(pending["pause_proof"], proof):
            raise ValueError("Altered committed pause proof")
        checkpoint = pending["checkpoint"]
        if (self.events[-1]["outcome"] != "pending" or checkpoint["completed_head"] != event_head
                or checkpoint["run_id"] != self.request["run_id"]
                or checkpoint["spec_digest"] != self.request["spec_digest"]
                or checkpoint["bundle_digest"] != self.request["bundle_digest"]
                or checkpoint["prior_head"] != json.loads(self.journal[-1])["previous"]):
            raise ValueError("Altered committed checkpoint")
        self.checkpoint = checkpoint
        self.value, self.used = checkpoint["value"], checkpoint["used"]
        self.head, self.sequence, self.event_head = previous, len(paths), event_head
        self.verify_journal()

    def commit(self, kind: str, data: dict[str, Any]) -> None:
        envelope = {"version": 1, "sequence": self.sequence, "previous": self.head,
                    "kind": kind, "run_id": self.request["run_id"], "data": data}
        raw = canonical(envelope)
        path = Path("/run") / (f"{self.sequence:08}.json")
        temporary = Path("/run") / f".pending-{self.sequence:08}"
        self.crash("before_file")
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400)
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        self.crash("after_file")
        os.link(temporary, path, follow_symlinks=False)
        self.crash("after_link")
        directory = os.open("/run", os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
            self.crash("after_dirsync")
            os.unlink(temporary)
            self.crash("after_unlink")
            os.fsync(directory)
        finally:
            os.close(directory)
        self.head = sha(raw)
        self.sequence += 1
        self.journal.append(raw)

    def crash(self, boundary: str) -> None:
        # Deterministic offline fault injection. A lost acknowledgement never
        # turns an ambiguous publication into permission to replay a step.
        if self.request.get("crash_at") == [self.sequence, boundary]:
            os._exit(73)

    def record_event(self, kind: str, event: dict[str, Any], checkpoint: dict[str, Any] | None) -> None:
        head = sha(b"workflow-generator/gate-event/v1\0" + self.event_head.encode() + canonical(event))
        if event["outcome"] == "pending" and checkpoint is not None:
            checkpoint["completed_head"] = head
        data = {"event": event, "checkpoint": checkpoint,
                "completed_head": head, "attestation": attest(self.request)}
        if event["outcome"] == "pending" and self.operator_key is not None:
            # Bind every prior journal byte (via head) and the entire pause data.
            data["pause_proof"] = hmac.digest(
                self.operator_key, b"workflow-generator/gate-pause/v1\0" +
                canonical({"previous": self.head, "data": data}), "sha256").hex()
        self.commit(kind, data)
        self.events.append(event)
        self.event_head = head

    def visit(self, identity: str) -> str:
        node = self.nodes[identity]
        if self.used >= self.spec["budget"]:
            event = {"node": identity, "outcome": "FAILED_BUDGET", "used": self.used,
                     "value": self.value, "target": "FAILED_BUDGET"}
            self.record_event("completed", event, None)
            return "FAILED_BUDGET"
        # A durable pre-dispatch claim precedes arithmetic or Gate charging.
        self.commit("claim", {"node": identity, "used_before": self.used, "value_before": self.value})
        self.used += 1
        if node["kind"] == "gate":
            attest(self.request)
            outcome = "pending"
            self.checkpoint = {"version": 1, "run_id": self.request["run_id"], "gate": identity,
                               "pause": secrets.token_hex(16), "value": self.value,
                               "used": self.used, "remaining": self.spec["budget"] - self.used,
                               "spec_digest": self.request["spec_digest"],
                               "bundle_digest": self.request["bundle_digest"],
                               "prior_head": self.head}
        else:
            operation = self.ops[node["operation"]]
            if operation["opcode"] != "add_int_v1" or type(operation["delta"]) is not int:
                raise ValueError("Unknown executable opcode")
            self.value += operation["delta"]
            outcome = "done"
        target = self.routes[(identity, outcome)]
        event = {"node": identity, "outcome": outcome, "used": self.used,
                 "value": self.value, "target": target}
        self.record_event("completed", event, self.checkpoint)
        return target

    def reference(self, entry: str | None = None) -> str:
        node = entry if entry is not None else self.spec["entry"]
        while node not in self.spec["terminals"]:
            node = self.visit(node)
        return node

    def graph(self, entry: str | None = None) -> str:
        builder = GraphBuilder(state_type=Execution, deps_type=type(None), input_type=type(None), output_type=str)
        def step(identity: str):
            async def invoke(ctx: StepContext) -> str:
                state = cast(Execution, ctx.state)
                return state.visit(identity)
            return invoke
        steps = {node["id"]: builder.step(step(node["id"]), node_id=f"node_{i}")
                 for i, node in enumerate(self.spec["nodes"])}
        builder.add(builder.edge_from(builder.start_node).to(steps[entry if entry is not None else self.spec["entry"]]))
        for i, node in enumerate(self.spec["nodes"]):
            decision = builder.decision(node_id=f"route_{i}")
            targets = {edge["target"] for edge in self.spec["edges"] if edge["source"] == node["id"]}
            targets.add("FAILED_BUDGET")
            for target in sorted(targets):
                def matches(value: str, selected: str = target) -> bool:
                    return value == selected
                decision = decision.branch(builder.match(str, matches=matches).to(
                    builder.end_node if target in self.spec["terminals"] else steps[target]))
            builder.add(builder.edge_from(steps[node["id"]]).to(decision))
        graph = builder.build(validate_graph_structure=False)
        return graph.run_sync(state=self, deps=None, inputs=None)

    def verify_journal(self) -> None:
        paths = sorted(Path("/run").glob("[0-9]*.json"))
        if len(paths) != len(self.journal):
            raise ValueError("Unexpected journal extent")
        for index, (path, raw) in enumerate(zip(paths, self.journal)):
            if path.is_symlink() or path.name != f"{index:08}.json" or path.read_bytes() != raw:
                raise ValueError("Journal/checkpoint evidence changed")

    def submit(self, checkpoint: object, decision: object) -> None:
        self.verify_journal()
        attest(self.request)
        if self.request["mode"] != "fixture":
            raise ValueError("Fixture decisions cannot authorize an operator run")
        if self.resolved or self.terminal != "PENDING" or canonical(checkpoint) != canonical(self.checkpoint) or self.checkpoint is None:
            raise ValueError("Wrong or late pause decision")
        if decision not in {"approved", "rejected"}:
            raise ValueError("Invalid decision")
        row = {"checkpoint": checkpoint, "decision": decision, "authority": "fixture"}
        if self.decision is not None:
            if self.decision != row:
                raise ValueError("Conflicting decision")
            return
        self.commit("decision", row)
        self.decision = row

    def consume_operator(self) -> None:
        if self.operator_key is None or self.checkpoint is None:
            raise ValueError("Not an operator pause")
        # Share the CLI's publication lock. A linked-but-unsynced decision
        # cannot be consumed between its link and the ambiguity marker check.
        authority = os.open("/run/operator.key", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(authority, "rb") as key_stream:
            info = os.fstat(key_stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
                raise ValueError("Unsafe operator authority")
            fcntl.flock(key_stream.fileno(), fcntl.LOCK_EX)
            if key_stream.read(33) != self.operator_key:
                raise ValueError("Changed operator authority")
            if any(Path("/run").glob(".pending-*")):
                raise ValueError("Incomplete decision or journal publication")
            fd = os.open("/run/decision.json", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            with os.fdopen(fd, "rb") as stream:
                info = os.fstat(stream.fileno())
                if info.st_uid != os.getuid() or info.st_mode & 0o077 or not stat.S_ISREG(info.st_mode):
                    raise ValueError("Unsafe decision file")
                raw = stream.read(65537)
            envelope = json.loads(raw)
            if len(raw) > 65536 or canonical(envelope) != raw or set(envelope) != {"record", "mac"}:
                raise ValueError("Noncanonical decision")
            row = envelope["record"]
            if not hmac.compare_digest(envelope["mac"], hmac.digest(self.operator_key, canonical(row), "sha256").hex()):
                raise ValueError("Forged operator decision")
            if (set(row) != {"version", "checkpoint", "decision", "authority", "uid", "recorded_ns"}
                    or type(row["version"]) is not int or row["version"] != 1
                    or canonical(row["checkpoint"]) != canonical(self.checkpoint)
                    or row["decision"] not in {"approved", "rejected"}
                    or row["authority"] != "local-os-account" or type(row["uid"]) is not int
                    or row["uid"] != os.getuid() or type(row["recorded_ns"]) is not int or row["recorded_ns"] <= 0):
                raise ValueError("Wrong operator decision scope")
            self.commit("decision", row)
            self.decision = row

    def resume(self, driver: str) -> str:
        self.verify_journal()
        attest(self.request)
        if self.resolved:
            return self.terminal
        if self.request["mode"] == "operator" and self.decision is None:
            self.consume_operator()
        if self.decision is None or self.checkpoint is None:
            raise ValueError("No scoped decision")
        # Load state from committed checkpoint, never from a caller's replacement.
        completed = [json.loads(raw) for raw in self.journal if json.loads(raw)["kind"] == "completed"]
        checkpoint = completed[-1]["data"]["checkpoint"]
        if canonical(checkpoint) != canonical(self.checkpoint):
            raise ValueError("Checkpoint changed")
        self.value, self.used = checkpoint["value"], checkpoint["used"]
        outcome = self.decision["decision"]
        target = self.routes[(checkpoint["gate"], outcome)]
        event = {"node": checkpoint["gate"], "outcome": outcome, "target": target,
                 "used": self.used, "value": self.value}
        self.record_event("resolved", event, checkpoint)
        self.resolved = True
        if target in self.spec["terminals"]:
            self.terminal = target
        else:
            self.terminal = self.reference(target) if driver == "reference" else self.graph(target)
        return self.terminal

    def result(self, terminal: str) -> dict[str, Any]:
        return {"terminal": terminal, "value": self.value, "used": self.used,
                "remaining": self.spec["budget"] - self.used, "events": self.events,
                "checkpoint": self.checkpoint, "head": self.head}


def main() -> None:
    attest()
    request = json.loads(sys.stdin.readline())
    execution = Execution(request)
    if request.get("recovery"):
        execution.load_pause()
        execution.terminal = execution.resume(sys.argv[1])
    else:
        execution.terminal = execution.reference() if sys.argv[1] == "reference" else execution.graph()
    print(json.dumps({"result": execution.result(execution.terminal), "attestation": attest(request)}), flush=True)
    # EOF/close never resumes implicitly. A failed command poisons this worker.
    for line in sys.stdin:
        try:
            command = json.loads(line)
            if command == {"command": "close"}:
                break
            if command.get("command") == "fixture" and set(command) == {"command", "checkpoint", "decision"}:
                execution.submit(command["checkpoint"], command["decision"])
            elif command == {"command": "continue"}:
                execution.resume(sys.argv[1])
            else:
                raise ValueError("Unsupported command")
            print(json.dumps({"result": execution.result(execution.terminal), "attestation": attest(request)}), flush=True)
        except Exception as exc:
            print(json.dumps({"error": type(exc).__name__ + ": " + str(exc)}), flush=True)
            break


if __name__ == "__main__":
    main()
