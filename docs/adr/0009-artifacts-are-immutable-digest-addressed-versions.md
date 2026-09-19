# Artifacts are immutable, digest-addressed versions

The artifact store holds a per-workflow directory of **immutable, digest-addressed versions**: the
spec, the emitted bundle, run logs, and approval records. Each regeneration produces a new version
rather than overwriting. We chose this over a flat store or ad-hoc paths because immutability plus
digest addressing is what makes two-digest approval (ADR-0005) and byte-identical replay possible; a
mutable path would let an approved artifact change underneath its approval, which is exactly the
failure the gate exists to prevent.

## Considered Options

- **Flat global store keyed by run id** — loses workflow identity and version history.
- **Write wherever the user says each time** — no stable address for an approval to bind to.
