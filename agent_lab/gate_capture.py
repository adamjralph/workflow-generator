"""Build-time rehearsal: discover loaded files, never a runtime fallback.

Invoked with isolated CPython, no site initialization, one explicit dependency
root. Only observed imports/native mappings are retained. Unobserved dependencies
remain absent in the worker and cause refusal, not ambient resolution.
"""
import sys
sys.path.insert(0, sys.argv[1])

import hashlib
import hmac
import stat
import json
import os
from pathlib import Path
import secrets
from typing import Any

from pydantic_graph import GraphBuilder, StepContext

builder = GraphBuilder(state_type=dict, deps_type=type(None), input_type=type(None), output_type=str)

@builder.step
async def rehearsal(ctx: StepContext) -> str:
    return "done"

builder.add(builder.edge_from(builder.start_node).to(rehearsal))
decision = builder.decision(node_id="route").branch(builder.match(str).to(builder.end_node))
builder.add(builder.edge_from(rehearsal).to(decision))
assert builder.build().run_sync(state={}, deps=None, inputs=None) == "done"
secrets.token_hex(16)
hashlib.sha256(b"rehearsal").hexdigest()
paths = set()
for module in list(sys.modules.values()):
    origin = getattr(getattr(module, "__spec__", None), "origin", None)
    if origin and origin not in {"frozen", "built-in"}:
        paths.add(origin)
for line in Path("/proc/self/maps").read_text().splitlines():
    fields = line.split()
    if len(fields) >= 6 and fields[5].startswith("/"):
        paths.add(fields[5])
print(json.dumps(sorted(paths)))
