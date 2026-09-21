"""Strict syntax for unused HTTP metadata and bounded chunk framing.

Transport ownership, byte limits, deadlines and provider status handling remain
with each adapter. These helpers never retain or report response field values.
"""
from __future__ import annotations

import re

# These fields are unused by the adapters and can legitimately occur repeatedly.
REPEATABLE_METADATA = frozenset({
    "set-cookie", "cache-control", "vary", "warning", "link", "server-timing",
    "via", "allow", "accept-ranges", "content-language", "pragma", "accept-patch",
    "accept-post", "alt-svc", "preference-applied",
})
# Only non-routing, non-authentication metadata is accepted in trailers.
_TRAILER_METADATA = frozenset({"server-timing", "digest", "content-digest", "repr-digest", "etag"})
_TOKEN = rb"[!#$%&'*+.^_`|~0-9A-Za-z-]+"
_QUOTED = rb'"(?:[\t !#-\[\]-~\x80-\xff]|\\[\t !-~\x80-\xff])*"'
_EXTENSION = re.compile(rb"[ \t]*;[ \t]*" + _TOKEN + rb"(?:[ \t]*=[ \t]*(?:" + _TOKEN + rb"|" + _QUOTED + rb"))?")


def header_field(line: str) -> tuple[str, str]:
    """Validate one field; reject folding, whitespace in names and controls."""
    key, value = line.split(":", 1)
    if (not re.fullmatch(_TOKEN, key.encode("ascii"))
            or any(ord(c) < 32 and c != "\t" or ord(c) == 127 for c in value)):
        raise ValueError
    return key.lower(), value.strip(" \t")


def chunk_size(line: bytes) -> int:
    """Consume the complete chunk-size line, including optional extensions."""
    match = re.match(rb"[0-9a-fA-F]+", line)
    if match is None or not line.endswith(b"\r\n"):
        raise ValueError
    end = len(line) - 2
    position = match.end()
    while position < end:
        extension = _EXTENSION.match(line, position, end)
        if extension is None:
            raise ValueError
        position = extension.end()
    return int(match[0], 16)


def trailer_field(line: bytes, seen: set[str]) -> None:
    """Validate and discard safe trailers; never let them override framing."""
    if not line.endswith(b"\r\n"):
        raise ValueError
    key, _ = header_field(line[:-2].decode("ascii"))
    if key not in _TRAILER_METADATA or (key in seen and key != "server-timing"):
        raise ValueError
    seen.add(key)
