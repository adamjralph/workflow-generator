#!/usr/bin/env python3
"""Check fresh-session claims against Git and project documents (offline)."""

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "state.json"
ENTRY = ("HANDOFF.md", "AGENTS.md", "state.json")
ISSUES = ROOT / ".scratch/workflow-generator/issues"


def head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def check() -> list[str]:
    errors = []
    state = json.loads(STATE.read_text(encoding="utf-8"))
    current = (ROOT / "CURRENT.md").read_text(encoding="utf-8")
    # HEAD is an observation from Git, not a claim stored in a tracked file.
    if "head" in state:
        errors.append("state.json: remove recorded HEAD; Git is the source")
    for name in ("CURRENT.md", "HANDOFF.md", "README.md"):
        text = (ROOT / name).read_text(encoding="utf-8")
        if re.search(r"^HEAD: [0-9a-f]{7,40}$|\*\*HEAD `?[0-9a-f]{7,40}`?", text, re.MULTILINE):
            errors.append(f"{name}: remove frozen HEAD; read Git directly")
    action = "python3 scripts/project_state.py check"
    if (state.get("authority") != "CURRENT.md" or state.get("next_action") != action
            or f"Next action: `{action}`" not in (ROOT / "HANDOFF.md").read_text(encoding="utf-8")
            or f"**Next action:** `{action}`" not in current):
        errors.append("Authority or next action disagrees across entry, state and CURRENT.md")
    for path in sorted(ISSUES.glob("[0-9]*.md")):
        text = path.read_text(encoding="utf-8")
        header = "\n".join(text.splitlines()[:10])
        if re.search(r"\*\*Status:\*\*.*\baccepted\b", header, re.I):
            for line in text.splitlines():
                if "**Still missing:**" in line:
                    # Ticket 19 accepts only the operator-pinned path; default mode remains untested.
                    if path.name.startswith("19-") and line == (
                        "**Still missing:** a live test of the **default oldest-draft** selection mode (invalid"
                    ):
                        continue
                    errors.append(f"{path.relative_to(ROOT)}: accepted but still missing")
    for name, phrase in (
        ("README.md", "**Start here → [CONTEXT.md]"),
        ("HANDOFF.md", "**HEAD `f29d4e7`"),
        ("CURRENT.md", "needs its own implementation go"),
    ):
        if phrase in (ROOT / name).read_text(encoding="utf-8"):
            errors.append(f"{name}: superseded phrase {phrase!r}")
    return errors


def measure() -> None:
    for name in ENTRY:
        print(f"{name}: {len((ROOT / name).read_text(encoding='utf-8'))} chars")
    print(f"mandated total: {sum(len((ROOT / name).read_text(encoding='utf-8')) for name in ENTRY)} chars")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("check", "measure"))
    args = parser.parse_args()
    if args.action == "measure":
        measure()
    else:
        errors = check()
        if errors:
            print("\n".join(errors), file=sys.stderr)
            return 1
        print(f"Fresh-session state check passed; Git HEAD: {head()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
