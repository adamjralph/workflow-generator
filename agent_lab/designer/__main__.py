"""Run with: python -m agent_lab.designer --evidence-dir PATH."""
import argparse
from pathlib import Path

from agent_lab.designer.server import create_server


def main() -> None:
    parser = argparse.ArgumentParser(description="Local offline workflow designer")
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--source-file", type=Path,
                        help="Optional read-only local JSON writing brief")
    parser.add_argument("--draft-config", type=Path,
                        help="Operator manifest for LinkedIn capture and explicit Generator + Guardian runs")
    parser.add_argument("--codex-auth-file", type=Path,
                        help="Read-only Codex credentials (default: ~/.hermes/auth.json; read only on Run)")
    parser.add_argument("--vertex-auth-file", type=Path,
                        help="Pinned read-only authorized-user ADC file; no discovery (read only on Run)")
    parser.add_argument("--vertex-project", default="project-54e16fcb-7c62-4041-bb1",
                        help="Explicit Vertex project (default: approved Guardian project)")
    parser.add_argument("--vertex-region", default="global",
                        help="Explicit Vertex region (default: global)")
    parser.add_argument("--protected-root", type=Path, action="append", default=[],
                        help="Additional Hermes installation/source root to protect (repeatable)")
    args = parser.parse_args()
    try:
        server = create_server(args.evidence_dir, port=args.port,
                               protected_roots=tuple(args.protected_root),
                               source_file=args.source_file, draft_config=args.draft_config,
                               codex_auth_file=args.codex_auth_file, vertex_auth_file=args.vertex_auth_file,
                               vertex_project=args.vertex_project, vertex_region=args.vertex_region)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(f"Open http://127.0.0.1:{server.server_port}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
