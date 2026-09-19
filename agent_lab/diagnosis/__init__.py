"""Runtime-neutral single-run diagnosis contracts."""
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


class SessionCalls(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    session_id: str = Field(min_length=1)
    calls: int = Field(ge=0, strict=True)


class UsageSource(Protocol):
    def calls(self, session_ids: tuple[str, ...]) -> tuple[SessionCalls, ...]: ...


class DiagnosisRecord(BaseModel):
    """Version 1 measures calls only; the other units belong to ticket 05."""
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
    rows = usage.calls(sessions)
    if {row.session_id for row in rows} != set(sessions) or len(rows) != len(sessions):
        raise DiagnosisError("Usage must cover exactly the attributed sessions")
    record = DiagnosisRecord(
        observation_id=str(uuid4()), observed_at=datetime.now(timezone.utc),
        attribution=attribution, calls_per_run=sum(row.calls for row in rows),
    )
    return store.save(record)
