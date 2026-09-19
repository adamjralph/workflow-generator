# Recordings

Frozen judgments from real Jev calls, committed on purpose.

`northside-garden-care.json` was produced by an actual live `--live` run against
`cases/northside-garden-care.txt`. It is in the repository so that a fresh clone
can reproduce the full workflow offline: no API key, no network, no spend, and
the same judgment every time.

Each recording is bound to the assessment it was made against (by SHA-256), so a
recording is refused rather than reused if the case file changes.

This fixture was adopted from `agent-workflow-lab` at `ce34093`; its demo scripts
are not part of this product checkout. Ticket 01 does not refresh it or make a
live call. Use `RecordedSource(recording_path=...)` with the case text to replay it.
A live call may return different values, so refreshing is a separate deliberate act.
