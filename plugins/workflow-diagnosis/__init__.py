"""Local Hermes directory plugin. Symlink this directory; do not copy the core."""
from collections.abc import Callable
from pathlib import Path
import shlex
import subprocess
import sys
from typing import Protocol


class CommandRegistry(Protocol):
    def register_command(self, name: str, handler: Callable[[str], str], *,
                         description: str, args_hint: str) -> object: ...


def invoke_cli(home: str, store: str, options: list[str], input_text: str = "") -> str:
    root = Path(__file__).resolve().parents[2]
    command = [str(root / ".venv/bin/python"), "-B", "-m", "agent_lab.diagnosis",
               "--hermes-home", str(Path(home).expanduser().resolve()),
               "--store", str(Path(store).expanduser().resolve()), *options]
    # Read the loaded host location without importing or initializing Hermes.
    host_file = getattr(sys.modules.get("hermes_cli"), "__file__", None)
    if host_file:
        command += ["--protected-root", str(Path(host_file).resolve().parents[1])]
    result = subprocess.run(command, cwd=root, input=input_text, text=True,
                            capture_output=True, timeout=90)
    return result.stdout.strip() if result.returncode == 0 else result.stderr.strip()


def diagnose_command(raw_args: str) -> str:
    try:
        args = shlex.split(raw_args)
        if len(args) != 4 or any(not arg.strip() or "\n" in arg or "\r" in arg for arg in args):
            return "Usage: /workflow-diagnose HERMES_HOME BOARD RUN_ID STORE (quote paths with spaces)"
        home, board, run_id, store = args
        return invoke_cli(home, store, [], f"{board}\n{run_id}\n")
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        return f"Diagnosis failed: {exc}"


def report_command(raw_args: str) -> str:
    try:
        args = shlex.split(raw_args)
        if len(args) not in {4, 5} or any(not arg.strip() or "\n" in arg or "\r" in arg for arg in args):
            return "Usage: /workflow-report HERMES_HOME RUNS_JSON WORKFLOW STORE [BASELINE_ARTIFACT]"
        home, manifest, workflow, store = args[:4]
        options = ["--report", str(Path(manifest).expanduser().resolve()), "--workflow", workflow]
        if len(args) == 5:
            options += ["--baseline", str(Path(args[4]).expanduser().resolve())]
        return invoke_cli(home, store, options)
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        return f"Diagnosis failed: {exc}"


def register(ctx: CommandRegistry) -> None:
    ctx.register_command("workflow-diagnose", diagnose_command,
                         description="Diagnose one Kanban run without modifying Hermes",
                         args_hint="HERMES_HOME BOARD RUN_ID STORE")
    ctx.register_command("workflow-report", report_command,
                         description="Measure a Kanban cohort and compare a measured baseline",
                         args_hint="HERMES_HOME RUNS_JSON WORKFLOW STORE [BASELINE_ARTIFACT]")
