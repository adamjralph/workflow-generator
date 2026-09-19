"""Subprocess audit guard for the agreed adapter seam, not a production sandbox."""
import os
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit


root = Path(os.environ["READ_ONLY_ROOT"]).resolve()


def protected(value):
    if isinstance(value, int):
        return False
    value = os.fsdecode(value)
    if value.startswith("file:"):
        value = unquote(urlsplit(value).path)
    return Path(value).resolve().is_relative_to(root)


def guard(event, args):
    if event == "open" and protected(args[0]):
        if args[2] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
            raise PermissionError("write to protected Hermes tree")
    # Even a read-only SQLite connection can write -shm: forbid all live connects.
    if event == "sqlite3.connect" and protected(args[0]):
        raise PermissionError("SQLite must not open a live Hermes database")
    if event in {"os.remove", "os.rmdir", "os.mkdir", "os.chmod", "os.truncate"}:
        if protected(args[0]):
            raise PermissionError("mutation of protected Hermes tree")
    if event in {"os.rename", "os.link", "os.symlink"}:
        if any(protected(arg) for arg in args[:2]):
            raise PermissionError("mutation of protected Hermes tree")


sys.addaudithook(guard)
