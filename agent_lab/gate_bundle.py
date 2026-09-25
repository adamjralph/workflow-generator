"""Linux-only retained executable closure for the restricted Gate runtime.

The trusted bootstrap is the local emitter/launcher, OS and bubblewrap.
This is not a sandbox against a malicious same-UID controller. Every file visible as executable runtime input inside the worker is a
verified copy of retained bytes on a private, read-only tmpfs. No host /usr,
site-packages, project directory, import cache, or network is exposed.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import importlib.metadata
import stat
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import sysconfig
from typing import Any, Mapping


from .gate_identity import GateIdentityError, RegisteredOperation, _canonical, _parse_canonical, read_spec, freeze_operations
from .gate_store import GateArtifactStore
from .spec import WorkflowSpec


@dataclass(frozen=True)
class GateVersion:
    directory: Path
    spec_digest: str
    bundle_digest: str


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _dependencies() -> dict[str, bytes]:
    if sys.platform != "linux" or sys.implementation.name != "cpython" or not shutil.which("bwrap"):
        raise GateIdentityError("Verified closure requires Linux CPython and bubblewrap")
    executable = Path(sys.executable).resolve()
    site = sysconfig.get_path("purelib")
    probe = subprocess.run([str(executable), "-I", "-S", "-B",
                            str(Path(__file__).with_name("gate_capture.py")), site],
                           capture_output=True, text=True, timeout=30,
                           env={"PATH": "/usr/bin", "LC_ALL": "C", "PYTHONHASHSEED": "0"})
    if probe.returncode:
        raise GateIdentityError("Dependency rehearsal failed: " + probe.stderr)
    import json
    files: dict[str, bytes] = {}
    native: list[Path] = [executable]
    for origin in json.loads(probe.stdout):
        path = Path(origin)
        raw = path.read_bytes()
        name = "/deps/" + str(path.relative_to(site)) if path.is_relative_to(site) else str(path)
        files[name] = raw
        if raw.startswith(b"\x7fELF"):
            native.append(path)
    seen: set[Path] = set()
    while native:
        path = native.pop().resolve()
        if path in seen:
            continue
        seen.add(path)
        headers = subprocess.run(["readelf", "-l", str(path)], capture_output=True, text=True, timeout=10)
        if headers.returncode:
            raise GateIdentityError("Cannot inspect native loader")
        interpreter = re.search(r"Requesting program interpreter: ([^\]]+)\]", headers.stdout)
        if interpreter:
            loader = Path(interpreter.group(1))
            files[str(loader)] = loader.read_bytes()
            native.append(loader)
        result = subprocess.run(["ldd", str(path)], capture_output=True, text=True, timeout=10)
        if result.returncode or "not found" in result.stdout:
            raise GateIdentityError("Native closure refused: " + str(path) + "\n" + result.stdout + result.stderr)
        for line in result.stdout.splitlines():
            match = re.search(r"(?:=>\s+)?(/[^\s]+)\s+\(", line)
            if match:
                dependency = Path(match.group(1))
                files[str(dependency)] = dependency.read_bytes()
                files[str(dependency.resolve())] = dependency.read_bytes()
                native.append(dependency)
    files["/runtime-python"] = executable.read_bytes()
    return files

def emit_bundle(spec: WorkflowSpec, operations: Mapping[str, RegisteredOperation], *, store: Path) -> GateVersion:
    artifact_store = GateArtifactStore(store)
    inputs = artifact_store.freeze_inputs(spec, operations)
    files = _dependencies()
    files["/app/gate_worker.py"] = Path(__file__).with_name("gate_worker.py").read_bytes()
    files["/app/spec.json"] = (inputs.directory / "spec.json").read_bytes()
    files["/app/operations.json"] = (inputs.directory / "operations.json").read_bytes()
    manifest = {
        "format": "gate-bundle/v1", "target": "pydantic-graph", "emitter": "restricted-gate/v1",
        "spec_digest": inputs.spec_digest, "operations_digest": inputs.operations_digest,
        "state_schema": {"value": "strict-int"},
        "target_version": importlib.metadata.version("pydantic-graph"),
        "graph_configuration": {"scheduler": "GraphBuilder", "validate_graph_structure": False, "concurrency": 1},
        "runtime": {"implementation": sys.implementation.name, "version": sys.version,
                    "stdlib": sysconfig.get_path("stdlib"), "executable": "/runtime-python"},
        "files": {name: {"sha256": _sha(raw), "size": len(raw)} for name, raw in sorted(files.items())},
    }
    raw = _canonical(manifest)
    digest = _sha(b"workflow-generator/gate-bundle/v1\0" + raw)
    directory = artifact_store._directory(digest)
    blobs = directory / "blobs"
    blobs.mkdir(mode=0o700, exist_ok=True)
    info = blobs.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise GateIdentityError("Unsafe bundle directory or symlink")
    for blob_digest, value in {_sha(raw): raw for raw in files.values()}.items():
        artifact_store._publish(blobs / blob_digest, value)
    artifact_store._publish(directory / "manifest.json", raw)
    version = GateVersion(directory, inputs.spec_digest, digest)
    verify_bundle(version)
    return version


def verify_bundle(version: GateVersion) -> tuple[dict[str, Any], dict[str, bytes]]:
    if type(version) is not GateVersion:
        raise GateIdentityError("Invalid executable version")
    store = GateArtifactStore(version.directory.parent)
    if version.directory != store.root / version.bundle_digest or version.directory.is_symlink():
        raise GateIdentityError("Wrong executable version directory")
    for directory in (version.directory, version.directory / "blobs"):
        info = directory.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise GateIdentityError("Unsafe bundle directory")
    def read(path: Path, bound: int) -> bytes:
        return GateArtifactStore._read(path, bound=bound)
    raw = read(version.directory / "manifest.json", 2_000_000)
    if _sha(b"workflow-generator/gate-bundle/v1\0" + raw) != version.bundle_digest:
        raise GateIdentityError("Bundle identity mismatch")
    manifest = _parse_canonical(raw)
    if (type(manifest) is not dict or set(manifest) != {
            "format", "target", "target_version", "emitter", "spec_digest", "operations_digest",
            "state_schema", "graph_configuration", "runtime", "files"}
            or manifest.get("format") != "gate-bundle/v1"
            or manifest.get("target") != "pydantic-graph" or manifest.get("emitter") != "restricted-gate/v1"
            or type(manifest.get("target_version")) is not str or not manifest["target_version"]
            or manifest.get("state_schema") != {"value": "strict-int"}
            or manifest.get("graph_configuration") != {
                "scheduler": "GraphBuilder", "validate_graph_structure": False, "concurrency": 1}
            or type(manifest.get("files")) is not dict
            or manifest.get("spec_digest") != version.spec_digest):
        raise GateIdentityError("Invalid executable manifest")
    runtime = manifest["runtime"]
    if (type(runtime) is not dict or set(runtime) != {"implementation", "version", "stdlib", "executable"}
            or runtime["implementation"] != "cpython" or runtime["executable"] != "/runtime-python"
            or not all(type(v) is str for v in runtime.values())):
        raise GateIdentityError("Unknown runtime configuration")
    files: dict[str, bytes] = {}
    for name, row in manifest["files"].items():
        if (type(row) is not dict or set(row) != {"sha256", "size"}
                or type(row["size"]) is not int or not 0 <= row["size"] <= 100_000_000):
            raise GateIdentityError("Unknown executable file record")
        path = Path(name)
        if (not path.is_absolute() or str(path) != name or ".." in path.parts
                or path.suffix == ".pyc" or name.startswith(("/proc/", "/run/", "/dev/"))):
            raise GateIdentityError("Unsafe runtime artifact path")
        digest = row["sha256"]
        if type(digest) is not str or not re.fullmatch("[0-9a-f]{64}", digest):
            raise GateIdentityError("Invalid executable digest")
        value = read(version.directory / "blobs" / digest, 100_000_000)
        if len(value) != row["size"] or _sha(value) != digest:
            raise GateIdentityError("Executable closure changed")
        files[name] = value
    required = {"/runtime-python", "/app/gate_worker.py", "/app/spec.json", "/app/operations.json"}
    if not required <= files.keys():
        raise GateIdentityError("Incomplete executable closure")
    read_spec(files["/app/spec.json"], expected_digest=version.spec_digest)
    operations = _parse_canonical(files["/app/operations.json"])
    if type(operations) is not dict or set(operations) != {"version", "operations"} or operations["version"] != 1:
        raise GateIdentityError("Unknown operation configuration")
    try:
        admitted = {key: RegisteredOperation(**row) for key, row in operations["operations"].items()}
        if freeze_operations(admitted) != (files["/app/operations.json"], manifest["operations_digest"]):
            raise GateIdentityError("Operation identity mismatch")
    except (TypeError, AttributeError) as exc:
        raise GateIdentityError("Invalid operation configuration") from exc
    return manifest, files


def launch_worker(version: GateVersion, run_directory: Path, driver: str) -> subprocess.Popen[str]:
    manifest, files = verify_bundle(version)
    files["/app/manifest.json"] = _canonical(manifest)
    args = ["bwrap", "--unshare-all", "--die-with-parent", "--new-session", "--clearenv",
            "--tmpfs", "/", "--proc", "/proc", "--dev", "/dev",
            "--setenv", "LC_ALL", "C", "--setenv", "PYTHONHASHSEED", "0"]
    fds: list[int] = []
    try:
        for name, raw in sorted(files.items()):
            fd = os.memfd_create("gate-artifact", 0)
            fds.append(fd)
            os.write(fd, raw)
            os.lseek(fd, 0, os.SEEK_SET)
            args += ["--perms", "0500" if raw.startswith(b"\x7fELF") else "0400", "--file", str(fd), name]
        args += ["--dir", "/run", "--bind", str(run_directory), "/run",
                 "--remount-ro", "/", "--chdir", "/app", "--",
                 "/runtime-python", "-I", "-S", "-B", "/app/gate_worker.py", driver]
        return subprocess.Popen(args, pass_fds=fds, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True, env={"PATH": "/usr/bin", "LC_ALL": "C"})
    finally:
        for fd in fds:
            os.close(fd)
