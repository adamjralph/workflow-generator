"""Loopback-only browser adapter; executable bindings never come from HTTP."""
from __future__ import annotations

import json
import secrets
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from agent_lab.designer import Design, author_design, check_design, validate_evidence_root
from agent_lab.designer.custom import run_request
from agent_lab.designer.drafts import DraftSource
from agent_lab.designer.draft_runs import DraftRuns
from agent_lab.designer.codex import CodexSource
from agent_lab.model_operation import ModelSource
from agent_lab.designer.source import ControlledSource
from agent_lab.designer.triage import TriageRequest, author_triage
from agent_lab.designer.roles import FixtureRequest, author_roles

_STATIC = Path(__file__).with_name("static")
_MAX_BODY = 4096


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON keys are not allowed")
        result[key] = value
    return result


def _invalid_constant(value: str) -> Any:
    raise ValueError("Non-finite JSON values are not allowed")


def create_server(
    evidence_dir: Path,
    port: int = 0,
    candidate_factory: Callable[[Design], object] | None = None,
    *, protected_roots: tuple[Path, ...] = (), source_file: Path | None = None,
    draft_config: Path | None = None,
    codex_auth_file: Path | None = None, draft_model_source: ModelSource | None = None,
) -> HTTPServer:
    """Create a local server with operator-selected sources and evidence root."""
    root = validate_evidence_root(evidence_dir, protected_roots=protected_roots)
    source = (ControlledSource(source_file, root, protected_roots=protected_roots)
              if source_file is not None else None)
    drafts = (DraftSource(draft_config, root, protected_roots=protected_roots)
              if draft_config is not None else None)
    runs = (DraftRuns(drafts, root,
                      draft_model_source if draft_model_source is not None else
                      CodexSource(codex_auth_file if codex_auth_file is not None else
                                  Path.home() / ".hermes" / "auth.json"),
                      protected_roots=protected_roots) if drafts is not None else None)
    token = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        server: HTTPServer

        def log_message(self, format: str, *args: Any) -> None:
            pass

        def respond(self, status: int, data: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'self'; "
                             "style-src 'self'; connect-src 'self'; img-src 'self'; "
                             "base-uri 'none'; frame-ancestors 'none'; form-action 'none'")
            self.end_headers()
            self.wfile.write(data)

        def json(self, status: int, data: object) -> None:
            self.respond(status, json.dumps(data, allow_nan=False).encode(), "application/json")

        def error(self, status: int, message: str) -> None:
            self.json(status, {("succeeded" if self.path in ("/api/run", "/api/source/run", "/api/source/capture", "/api/drafts/capture", "/api/drafts/request", "/api/drafts/run") else "passed"): False, "findings": [
                {"code": "request_error", "path": "request", "message": message}],
                "cases": [], "completed_cases": [], "evidence": []})

        def same_host(self) -> bool:
            return self.headers.get_all("Host") == [f"127.0.0.1:{self.server.server_port}"]

        def do_GET(self) -> None:
            if not self.same_host():
                self.error(403, "Exact loopback Host required")
                return
            if self.path == "/api/drafts":
                self.json(200, {"available": drafts is not None, "run_available": runs is not None,
                                "source": "LinkedIn draft capture"})
                return
            if self.path == "/api/source":
                self.json(200, {"available": source is not None, "source": "Local writing brief"})
                return
            files = {"/": ("index.html", "text/html; charset=utf-8"),
                     "/app.js": ("app.js", "text/javascript; charset=utf-8"),
                     "/style.css": ("style.css", "text/css; charset=utf-8")}
            if self.path not in files:
                self.error(404, "Unknown path")
                return
            name, content_type = files[self.path]
            data = (_STATIC / name).read_bytes()
            if self.path == "/":
                data = data.replace(b"__REQUEST_TOKEN__", token.encode())
            self.respond(200, data, content_type)

        def do_POST(self) -> None:
            origin = f"http://127.0.0.1:{self.server.server_port}"
            if (not self.same_host() or self.headers.get_all("Origin") != [origin]
                    or self.headers.get_all("X-Designer-Token") != [token]):
                self.error(403, "Same-origin request and page token required")
                return
            if self.path not in ("/api/design", "/api/check", "/api/run", "/api/source/capture",
                                 "/api/source/run", "/api/source/check", "/api/drafts/capture",
                                 "/api/drafts/request", "/api/drafts/run"):
                self.error(404, "Unknown path")
                return
            if self.headers.get_all("Content-Type") != ["application/json"]:
                self.error(415, "application/json required")
                return
            lengths = self.headers.get_all("Content-Length", [])
            if (self.headers.get("Transfer-Encoding") is not None or len(lengths) != 1
                    or not lengths[0].isdigit() or not 0 < int(lengths[0]) <= _MAX_BODY):
                self.error(400, "A bounded Content-Length is required")
                return
            self.connection.settimeout(5)
            try:
                raw = json.loads(self.rfile.read(int(lengths[0])),
                                 object_pairs_hook=_unique_object, parse_constant=_invalid_constant)
                design: Design
                # Validate before any endpoint can execute anything.
                if self.path == "/api/drafts/capture":
                    if drafts is None:
                        raise ValueError("No draft capture configured")
                    if not isinstance(raw, dict) or raw:
                        raise ValueError("Draft capture requires an empty object")
                elif self.path in ("/api/drafts/request", "/api/drafts/run"):
                    keys = ({"snapshot"} if self.path == "/api/drafts/request" else
                            {"snapshot", "run_request"})
                    if runs is None or not isinstance(raw, dict) or raw.keys() != keys:
                        raise ValueError("Invalid draft request")
                    if any(not isinstance(raw[key], str) or len(raw[key]) != 64 or
                           any(c not in "0123456789abcdef" for c in raw[key]) for key in keys):
                        raise ValueError("Invalid draft identity")
                elif self.path.startswith("/api/source/"):
                    if source is None:
                        raise ValueError("No local writing brief configured")
                    keys = set() if self.path == "/api/source/capture" else {"design", "snapshot"}
                    if not isinstance(raw, dict) or raw.keys() != keys:
                        raise ValueError("Invalid controlled-source request fields")
                    if keys:
                        design = author_roles(raw["design"])
                        if not isinstance(raw["snapshot"], str):
                            raise ValueError("Invalid snapshot digest")
                elif self.path == "/api/run":
                    if not isinstance(raw, dict) or raw.keys() != {"design", "request"}:
                        raise ValueError("Custom run requires only design and request")
                    if isinstance(raw["design"], dict) and raw["design"].get("mode") == "roles":
                        design = author_roles(raw["design"])
                        FixtureRequest.model_validate(raw["request"])
                    else:
                        design = author_triage(raw["design"])
                        TriageRequest.model_validate(raw["request"])
                else:
                    design = author_design(raw)
            except (ValueError, OSError, RecursionError) as exc:
                self.error(400, "Invalid draft request" if self.path.startswith("/api/drafts/") else str(exc))
                return
            try:
                if self.path == "/api/drafts/capture":
                    assert drafts is not None
                    result = drafts.capture()
                    if result.get("succeeded"):
                        assert runs is not None
                        issued = runs.create_request(result["snapshot"])
                        result.update({key: issued[key] for key in ("run_request", "status")})
                elif self.path == "/api/drafts/request":
                    assert runs is not None
                    result = runs.create_request(raw["snapshot"])
                elif self.path == "/api/drafts/run":
                    assert runs is not None
                    result = runs.run(raw["snapshot"], raw["run_request"])
                elif self.path.startswith("/api/source/"):
                    assert source is not None
                    if self.path == "/api/source/capture":
                        result = source.capture()
                    else:
                        operation = source.run if self.path == "/api/source/run" else source.check
                        result = operation(raw["design"], raw["snapshot"],
                                           **({"candidate_factory": candidate_factory}
                                              if candidate_factory is not None else {}))
                elif self.path == "/api/run":
                    result = run_request(raw["design"], raw["request"], evidence_dir=root,
                                         protected_roots=protected_roots,
                                         **({"candidate_factory": candidate_factory}
                                            if candidate_factory is not None else {}))
                elif self.path == "/api/design":
                    result = design.view()
                elif candidate_factory is None:
                    result = check_design(raw, evidence_dir=root, protected_roots=protected_roots)
                else:
                    result = check_design(raw, evidence_dir=root, candidate_factory=candidate_factory,
                                          protected_roots=protected_roots)
                self.json(200, result)
            except Exception as exc:
                # Generation, checking and audit errors must never resemble a pass.
                message = ("Draft operation failed; inspect private evidence before requesting another run"
                           if self.path.startswith("/api/drafts/")
                           else "Local source or snapshot operation failed"
                           if self.path.startswith("/api/source/") and isinstance(exc, OSError)
                           else f"Operation failed: {exc}")
                self.error(500, message)

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)
