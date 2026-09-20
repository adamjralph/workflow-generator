"""Run with: python -m agent_lab.designer --evidence-dir PATH."""
import argparse
from pathlib import Path

from agent_lab.designer.server import create_server


def main() -> None:
    parser = argparse.ArgumentParser(description="Local offline workflow designer")
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args()
    try:
        server = create_server(args.evidence_dir, port=args.port)
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
