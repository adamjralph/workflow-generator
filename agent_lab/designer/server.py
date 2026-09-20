"""Loopback-only browser adapter; executable bindings never come from HTTP."""
from __future__ import annotations

import json
import secrets
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from agent_lab.designer import Design, author_design, check_design, validate_evidence_root

_STATIC = Path(__file__).with_name("static")
_MAX_BODY = 4096


def create_server(
    evidence_dir: Path,
    port: int = 0,
    candidate_factory: Callable[[Design], object] | None = None,
) -> HTTPServer:
    """Create a local server with an operator-selected, validated evidence root."""
    root = validate_evidence_root(evidence_dir)
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
            self.json(status, {"passed": False, "findings": [
                {"code": "request_error", "path": "request", "message": message}],
                "cases": [], "completed_cases": [], "evidence": []})

        def same_host(self) -> bool:
            return self.headers.get_all("Host") == [f"127.0.0.1:{self.server.server_port}"]

        def do_GET(self) -> None:
            if not self.same_host():
                self.error(403, "Exact loopback Host required")
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
            if self.path not in ("/api/design", "/api/check"):
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
                raw = json.loads(self.rfile.read(int(lengths[0])))
                # Validate before either endpoint can execute anything.
                design = author_design(raw)
            except (ValueError, OSError, RecursionError) as exc:
                self.error(400, str(exc))
                return
            try:
                if self.path == "/api/design":
                    result = design.view()
                elif candidate_factory is None:
                    result = check_design(raw, evidence_dir=root)
                else:
                    result = check_design(raw, evidence_dir=root, candidate_factory=candidate_factory)
                self.json(200, result)
            except Exception as exc:
                # Generation, checking and audit errors must never resemble a pass.
                self.error(500, f"Operation failed: {exc}")

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)
