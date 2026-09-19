"""Runtime-neutral single-run diagnosis contracts."""
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Protocol
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class DiagnosisError(ValueError):
    """Attribution or measurement is unavailable; never report it as zero."""


class RunAttribution(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str = Field(min_length=1)
    runtime: str = Field(min_length=1)
    role: str = Field(min_length=1)
    session_ids: tuple[str, ...] = Field(min_length=1)
    workflow_identity: str = Field(min_length=1)


class RunAttributionAdapter(Protocol):
    def attribute(self, run_id: str) -> RunAttribution: ...


class TokenCounts(BaseModel):
    """Separate counters, not an additive billable total (provider semantics vary)."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    input_tokens: int = Field(ge=0, strict=True)
    output_tokens: int = Field(ge=0, strict=True)
    cache_read_tokens: int = Field(ge=0, strict=True)
    cache_write_tokens: int = Field(ge=0, strict=True)
    reasoning_tokens: int = Field(ge=0, strict=True)


def sum_tokens(counts: Iterable[TokenCounts]) -> TokenCounts:
    totals = dict.fromkeys(TokenCounts.model_fields, 0)
    for count in counts:
        for name in totals:
            totals[name] += getattr(count, name)
    return TokenCounts(**totals)


class UsageRow(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    session_id: str = Field(min_length=1)
    task: str | None
    calls: int = Field(ge=0, strict=True)
    tokens: TokenCounts


class UsageSource(Protocol):
    def usage(self, session_ids: tuple[str, ...]) -> tuple[UsageRow, ...]: ...


class Measurements(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    calls_per_run: int = Field(ge=0, strict=True)
    context_per_call: float | None = Field(ge=0)
    tokens_per_run: TokenCounts
    cache_hit_rate: float | None = Field(ge=0, le=1)

    @classmethod
    def from_rows(cls, rows: tuple[UsageRow, ...]) -> "Measurements":
        calls = sum(row.calls for row in rows)
        tokens = sum_tokens(row.tokens for row in rows)
        context = tokens.input_tokens + tokens.cache_read_tokens
        return cls(calls_per_run=calls, tokens_per_run=tokens,
                   context_per_call=context / calls if calls else None,
                   cache_hit_rate=tokens.cache_read_tokens / context if context else None)


class TrafficMeasurement(Measurements):
    task: str | None
    kind: Literal["worker", "auxiliary", "review"]


class DiagnosisRecord(Measurements):
    """One attributed run, in the baseline's four measurement units."""
    schema_version: Literal[2] = 2
    observation_id: str
    observed_at: datetime
    attribution: RunAttribution
    traffic: tuple[TrafficMeasurement, ...]


class LegacyDiagnosisRecord(BaseModel):
    """Read-only compatibility for immutable, calls-only ticket-03 artifacts."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal[1] = 1
    observation_id: str
    observed_at: datetime
    attribution: RunAttribution
    calls_per_run: int = Field(ge=0, strict=True)


class StoredDiagnosis(BaseModel):
    model_config = ConfigDict(frozen=True)

    record: DiagnosisRecord
    path: Path


class RecordStore(Protocol):
    def save(self, record: DiagnosisRecord) -> StoredDiagnosis: ...


def diagnose(run_id: str, adapter: RunAttributionAdapter, usage: UsageSource,
             store: RecordStore) -> StoredDiagnosis:
    attribution = adapter.attribute(run_id)
    sessions = attribution.session_ids
    if attribution.run_id != run_id or len(set(sessions)) != len(sessions) or not all(sessions):
        raise DiagnosisError("Invalid run attribution")
    rows = usage.usage(sessions)
    if {row.session_id for row in rows} != set(sessions):
        raise DiagnosisError("Usage must cover exactly the attributed sessions")
    tasks = sorted({row.task or "" for row in rows})
    traffic = tuple(TrafficMeasurement(
        task=task or None,
        kind="worker" if not task else "review" if task == "background_review" else "auxiliary",
        **Measurements.from_rows(tuple(r for r in rows if (r.task or "") == task)).model_dump(),
    ) for task in tasks)
    record = DiagnosisRecord(
        observation_id=str(uuid4()), observed_at=datetime.now(timezone.utc),
        attribution=attribution, traffic=traffic, **Measurements.from_rows(rows).model_dump(),
    )
    return store.save(record)
