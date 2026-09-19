"""Measured cohorts, role breakdowns and before/after evidence.

The Kanban entry point pins the attribution/usage join and metric semantics. A
baseline is another digest-verified report from this entry point, never caller-
supplied counters. A cohort may span boards and historical task identities.
"""
import hashlib
import json
from pathlib import Path
from typing import Literal, Protocol, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationError, computed_field, model_validator

from . import (DiagnosisError, DiagnosisRecord, RunAttributionAdapter, TokenCounts,
               UsageSource, diagnose, sum_tokens)
from .hermes import HermesUsage, KanbanAdapter
from .store import DiagnosisStore


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    @model_validator(mode="before")
    @classmethod
    def derive_computed_fields(cls, value: object) -> object:
        # Rendered summaries never override the underlying measured evidence.
        if isinstance(value, dict):
            return {key: item for key, item in value.items() if key not in cls.model_computed_fields}
        return value


class RunSelection(FrozenModel):
    """Source-qualified run id; the source is interpreted by the adapter provider."""
    source: str = Field(min_length=1)
    run_id: str = Field(min_length=1)


class ReportSource(Protocol):
    @property
    def measurement_method(self) -> str:
        """Stable version of attribution, usage selection and measurement semantics."""
        ...

    @property
    def usage_source(self) -> UsageSource: ...

    def adapter(self, selection: RunSelection) -> RunAttributionAdapter: ...


class KanbanRun(FrozenModel):
    board: str = Field(min_length=1)
    run_id: str = Field(min_length=1)


class TokenRates(FrozenModel):
    input_tokens: float
    output_tokens: float
    cache_read_tokens: float
    cache_write_tokens: float
    reasoning_tokens: float


class Aggregate(FrozenModel):
    run_count: int = Field(gt=0)
    calls: int = Field(ge=0)
    tokens: TokenCounts

    @computed_field  # type: ignore[prop-decorator]  # Pydantic computed property
    @property
    def calls_per_run(self) -> float:
        return self.calls / self.run_count

    @computed_field  # type: ignore[prop-decorator]  # Pydantic computed property
    @property
    def tokens_per_run(self) -> TokenRates:
        return TokenRates(**{name: getattr(self.tokens, name) / self.run_count
                             for name in TokenCounts.model_fields})

    @computed_field  # type: ignore[prop-decorator]  # Pydantic computed property
    @property
    def context_per_call(self) -> float | None:
        return self.tokens.context_per_call(self.calls)

    @computed_field  # type: ignore[prop-decorator]  # Pydantic computed property
    @property
    def cache_hit_rate(self) -> float | None:
        return self.tokens.cache_hit_rate


class TrafficAggregate(FrozenModel):
    task: str | None
    kind: Literal["worker", "auxiliary", "review"]
    measurements: Aggregate


class RoleBreakdown(FrozenModel):
    role: str
    measurements: Aggregate
    traffic: tuple[TrafficAggregate, ...]


def aggregate(runs: tuple[DiagnosisRecord, ...]) -> Aggregate:
    return Aggregate(run_count=len(runs), calls=sum(r.calls_per_run for r in runs),
                     tokens=sum_tokens(r.tokens_per_run for r in runs))


def traffic_breakdown(runs: tuple[DiagnosisRecord, ...]) -> tuple[TrafficAggregate, ...]:
    traffic = [t for run in runs for t in run.traffic]
    return tuple(TrafficAggregate(
        task=task or None, kind=next(t.kind for t in traffic if (t.task or "") == task),
        measurements=Aggregate(
            run_count=len(runs),
            calls=sum(t.calls_per_run for t in traffic if (t.task or "") == task),
            tokens=sum_tokens(t.tokens_per_run for t in traffic if (t.task or "") == task),
        ),
    ) for task in sorted({t.task or "" for t in traffic}))


class Cohort(FrozenModel):
    selections: tuple[RunSelection, ...] = Field(min_length=1)
    runs: tuple[DiagnosisRecord, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_attribution(self) -> Self:
        if len(self.selections) != len(self.runs) or len(set(self.selections)) != len(self.selections):
            raise ValueError("A cohort requires distinct run selections")
        sessions: set[str] = set()
        for selection, run in zip(self.selections, self.runs):
            attribution = run.attribution
            if selection.run_id != attribution.run_id:
                raise ValueError("Run does not match its selection")
            ids = attribution.session_ids
            if len(set(ids)) != len(ids) or sessions.intersection(ids):
                raise ValueError("A session may be counted only once in a cohort")
            sessions.update(ids)
        return self

    @computed_field  # type: ignore[prop-decorator]  # Pydantic computed property
    @property
    def total(self) -> Aggregate:
        return aggregate(self.runs)

    @computed_field  # type: ignore[prop-decorator]  # Pydantic computed property
    @property
    def traffic(self) -> tuple[TrafficAggregate, ...]:
        return traffic_breakdown(self.runs)

    @computed_field  # type: ignore[prop-decorator]  # Pydantic computed property
    @property
    def roles(self) -> tuple[RoleBreakdown, ...]:
        return tuple(RoleBreakdown(
            role=role,
            measurements=aggregate(group), traffic=traffic_breakdown(group),
        ) for role in sorted({r.attribution.role for r in self.runs})
            for group in [tuple(r for r in self.runs if r.attribution.role == role)])


class MeasurementDelta(FrozenModel):
    """After minus before; cache-rate deltas are fractions, not percentages."""
    calls_per_run: float
    context_per_call: float | None
    tokens_per_run: TokenRates
    cache_hit_rate: float | None

    @classmethod
    def between(cls, before: Aggregate, after: Aggregate) -> "MeasurementDelta":
        def difference(old: float | None, new: float | None) -> float | None:
            return None if old is None or new is None else new - old

        old_tokens, new_tokens = before.tokens_per_run, after.tokens_per_run
        return cls(
            calls_per_run=after.calls_per_run - before.calls_per_run,
            context_per_call=difference(before.context_per_call, after.context_per_call),
            tokens_per_run=TokenRates(**{
                name: getattr(new_tokens, name) - getattr(old_tokens, name)
                for name in TokenCounts.model_fields
            }),
            cache_hit_rate=difference(before.cache_hit_rate, after.cache_hit_rate),
        )


class RoleComparison(FrozenModel):
    role: str
    delta: MeasurementDelta


class DiagnosisReport(FrozenModel):
    schema_version: Literal[1] = 1
    # Change this when attribution, usage selection or metric semantics change.
    measurement_method: str = Field(min_length=1)
    workflow_identity: str = Field(min_length=1)
    current: Cohort
    before: Cohort | None = None
    baseline_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_baseline(self) -> Self:
        if (self.before is None) != (self.baseline_digest is None):
            raise ValueError("Before measurements require a baseline artifact digest")
        return self

    @computed_field  # type: ignore[prop-decorator]  # Pydantic computed property
    @property
    def comparison(self) -> MeasurementDelta | None:
        return (MeasurementDelta.between(self.before.total, self.current.total)
                if self.before is not None else None)

    @computed_field  # type: ignore[prop-decorator]  # Pydantic computed property
    @property
    def role_comparisons(self) -> tuple[RoleComparison, ...]:
        if self.before is None:
            return ()
        before = {role.role: role.measurements for role in self.before.roles}
        return tuple(RoleComparison(role=role.role,
                                    delta=MeasurementDelta.between(before[role.role], role.measurements))
                     for role in self.current.roles if role.role in before)


class StoredReport(FrozenModel):
    report: DiagnosisReport
    path: Path


def save_report(report: DiagnosisReport, store: DiagnosisStore) -> StoredReport:
    workflow = hashlib.sha256(f"report:{report.workflow_identity}".encode()).hexdigest()
    raw = report.model_dump_json().encode()
    return StoredReport(report=report, path=store.save_bytes(workflow, "reports", raw))


def load_report(path: Path, store: DiagnosisStore) -> DiagnosisReport:
    try:
        raw = store.load_bytes(path)
        report = DiagnosisReport.model_validate_json(raw)
        if json.loads(raw) != report.model_dump(mode="json"):
            raise DiagnosisError("Report summaries do not match their measured evidence")
        return report
    except ValidationError as exc:
        raise DiagnosisError(f"Invalid baseline report: {exc}") from exc


def measure_report(runs: tuple[RunSelection, ...], source: ReportSource,
                   workflow_identity: str, store: DiagnosisStore, *,
                   baseline: Path | None = None) -> StoredReport:
    if not runs or len(set(runs)) != len(runs):
        raise DiagnosisError("A report requires distinct, nonempty run selections")
    before = load_report(baseline, store) if baseline is not None else None
    if before is not None and before.workflow_identity != workflow_identity:
        raise DiagnosisError("Baseline belongs to a different report workflow")
    if before is not None and before.measurement_method != source.measurement_method:
        raise DiagnosisError("Baseline uses a different measurement method")
    records = tuple(diagnose(run.run_id, source.adapter(run), source.usage_source, store).record
                    for run in runs)
    try:
        report = DiagnosisReport(
            measurement_method=source.measurement_method,
            workflow_identity=workflow_identity, current=Cohort(selections=runs, runs=records),
            before=before.current if before is not None else None,
            baseline_digest=baseline.resolve().stem if baseline is not None else None,
        )
    except ValidationError as exc:
        raise DiagnosisError(f"Invalid report: {exc}") from exc
    return save_report(report, store)


class KanbanReportSource:
    measurement_method = "kanban-worker-session/summed-usage/four-units-v1"

    def __init__(self, home: Path, protected_roots: tuple[Path, ...]):
        self.home = home
        self.protected_roots = protected_roots
        self.usage_source = HermesUsage(home, protected_roots=protected_roots)

    def adapter(self, selection: RunSelection) -> KanbanAdapter:
        return KanbanAdapter(self.home, selection.source, protected_roots=self.protected_roots)


def diagnose_report(hermes_home: Path, runs: tuple[KanbanRun, ...], workflow_identity: str,
                    store: DiagnosisStore, *, baseline: Path | None = None,
                    protected_roots: tuple[Path, ...] = ()) -> StoredReport:
    """Kanban front door to the runtime-neutral report pipeline."""
    # Bind the write boundary to this source home even for direct Python callers.
    store = DiagnosisStore(store.root, protected_roots=(
        hermes_home, *protected_roots, *store.protected_roots,
    ))
    selections = tuple(RunSelection(source=run.board, run_id=run.run_id) for run in runs)
    return measure_report(selections, KanbanReportSource(hermes_home, protected_roots),
                          workflow_identity, store, baseline=baseline)
