"""Offline role fixture operations; never agents, permissions or a real review."""
from collections.abc import Callable
from dataclasses import dataclass
import json
from pathlib import Path
from types import MappingProxyType
from typing import Annotated, Any, Literal

from pydantic import AfterValidator, BeforeValidator, Field, field_validator, model_validator

from . import Design, StrictAnswer
from agent_lab.reference import TransformResult
from agent_lab.spec import Route, TransformNode, WorkflowSpec


def freeze_list(value: object) -> object:
    return tuple(value) if isinstance(value, list) else value


Names = Annotated[tuple[str, ...], BeforeValidator(freeze_list)]
RoleId = Literal["signal_generator", "studio_producer", "signal_guardian"]


class RoleContract(StrictAnswer):
    id: RoleId
    display_name: str = Field(min_length=1)
    status: Literal["verified"]
    accepts: Names = Field(min_length=1)
    produces: Names = Field(min_length=1)
    reviews: Names
    reviewed_by: Names

    @field_validator("accepts", "produces", "reviews", "reviewed_by")
    @classmethod
    def distinct_names(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not item.strip() for item in value) or len(value) != len(set(value)):
            raise ValueError("Contract names must be nonblank and distinct")
        return value


class Provenance(StrictAnswer):
    source: Literal["specialist-agent-role-registry.yaml"]
    section: str = Field(min_length=1)
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    note: str = Field(min_length=1)


class RoleCatalog(StrictAnswer):
    provenance: Provenance
    roles: Annotated[tuple[RoleContract, ...], BeforeValidator(freeze_list)]

    @model_validator(mode="after")
    def complete(self) -> "RoleCatalog":
        ids = {role.id for role in self.roles}
        if len(self.roles) != 3 or len(ids) != 3:
            raise ValueError("Catalog requires three distinct known roles")
        if any(set(role.reviews + role.reviewed_by) - ids for role in self.roles):
            raise ValueError("Unknown role in review relationship")
        return self


class RoleAnswers(StrictAnswer):
    mode: Literal["roles"]
    producer: str
    output: str
    consumer: str


class FixtureRequest(StrictAnswer):
    fixture: Literal["with_evidence", "without_evidence"]


def nonblank(value: str) -> str:
    if not value.strip():
        raise ValueError("Text must be nonblank")
    return value


ShortText = Annotated[str, Field(min_length=1, max_length=64), AfterValidator(nonblank)]


class WritingBrief(StrictAnswer):
    request_id: ShortText
    text: Annotated[str, Field(min_length=1, max_length=240), AfterValidator(nonblank)]
    evidence_labels: tuple[ShortText, ...] = Field(max_length=3)

    @field_validator("evidence_labels")
    @classmethod
    def distinct_labels(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("Evidence labels must be distinct")
        return value


class EvidenceHandoff(WritingBrief):
    pass


class ReviewVerdict(StrictAnswer):
    request_id: ShortText
    evidence_count: int = Field(ge=0, le=3)
    result: Literal["evidence_present", "evidence_missing"]


class RoleState(StrictAnswer):
    brief: WritingBrief
    handoff: EvidenceHandoff | None = None
    verdict: ReviewVerdict | None = None


@dataclass(frozen=True)
class RoleDesign(Design[RoleState]):
    catalog: RoleCatalog

    def view(self) -> dict[str, Any]:
        return {
            "answers": self.answers.model_dump(),
            "catalog": self.catalog.model_dump(mode="json"),
            "operations": [
                {"role": "signal_generator", "requires": ["bounded_writing_brief"], "produces": "evidence_handoff"},
                {"role": "signal_guardian", "requires": ["evidence_handoff"], "produces": "review_verdict",
                 "reviews": "signal_generator"}],
            "policy": "Exact output/input type equality, available fixture operations and declared review relationship required. No aliases or conversions. Registry lists do not mean all inputs are required or that whole roles are compatible. Verification is historical metadata, not current permission or execution-quality proof. Receipt references are metadata, not executable inputs.",
            "nodes": [{"id": node.id, "kind": node.kind,
                       "label": "fixture → evidence_handoff" if node.id == "generator" else "fixture → review_verdict"}
                      for node in self.spec.nodes],
            "edges": [edge.model_dump() for edge in self.spec.edges],
            "terminals": list(self.spec.terminals), "budget": self.spec.budget,
            "cases": [{"name": name, **state.brief.model_dump(mode="json")}
                      for name, state in self.cases.items()],
            "scope": "Two synthetic fixture cases only. Not agents, approval, correctness or a real review.",
            "infeasible_routes": [],
        }


def generate_handoff(state: RoleState) -> TransformResult[RoleState]:
    handoff = EvidenceHandoff.model_validate(state.brief.model_dump())
    return TransformResult(state.model_copy(update={"handoff": handoff}), "done")


def review_handoff(state: RoleState) -> TransformResult[RoleState]:
    if state.handoff is None:
        raise ValueError("Missing evidence_handoff")
    count = len(state.handoff.evidence_labels)
    verdict = ReviewVerdict(request_id=state.handoff.request_id, evidence_count=count,
                            result="evidence_present" if count else "evidence_missing")
    return TransformResult(state.model_copy(update={"verdict": verdict}), "done")


def author_roles(raw: object, *, catalog: object = None) -> RoleDesign:
    """The optional catalog is trusted Python input, never a browser parameter."""
    answers = RoleAnswers.model_validate(raw)
    if catalog is None:
        catalog = json.loads(Path(__file__).with_name("role_catalog.json").read_text())
    contracts = RoleCatalog.model_validate(catalog)
    roles = {role.id: role for role in contracts.roles}
    if answers.producer not in roles or answers.consumer not in roles:
        raise ValueError("Unknown role")
    producer, consumer = roles[answers.producer], roles[answers.consumer]
    if answers.output not in producer.produces or answers.output not in consumer.accepts:
        raise ValueError("Incompatible connection: exact declared output/input type equality required")
    if (producer.id != "signal_generator" or consumer.id != "signal_guardian"
            or answers.output != "evidence_handoff"
            or "bounded_writing_brief" not in producer.accepts
            or "review_verdict" not in consumer.produces):
        raise ValueError("Unsupported fixture operation: registry type match alone is not executable")
    if producer.id not in consumer.reviews:
        raise ValueError("Required declared review relationship is missing")
    spec = WorkflowSpec(entry="generator", budget=2,
                        nodes=(TransformNode(id="generator", operation="generate_handoff"),
                               TransformNode(id="guardian", operation="review_handoff")),
                        edges=(Route(source="generator", outcome="done", target="guardian"),
                               Route(source="guardian", outcome="done", target="COMPLETED")),
                        terminals=("COMPLETED", "FAILED_VALIDATION", "FAILED_BUDGET"))
    bindings: dict[str, Callable[[RoleState], object]] = {
        "generate_handoff": generate_handoff, "review_handoff": review_handoff}
    cases = {
        "with_evidence": RoleState(brief=WritingBrief(request_id="fixture-with",
            text="Write a synthetic update.", evidence_labels=("synthetic-note",))),
        "without_evidence": RoleState(brief=WritingBrief(request_id="fixture-without",
            text="Write a synthetic update.", evidence_labels=())),
    }
    return RoleDesign(answers, spec, MappingProxyType(bindings), MappingProxyType(cases), (), RoleState, contracts)
