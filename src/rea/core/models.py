"""Core domain models for REA.

All models are versioned, typed, and designed for evidence-backed
investigation pipelines. Confidence values are qualitative ranks,
not calibrated probabilities.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


SCHEMA_VERSION = "1.0.0"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class ArtifactKind(str, Enum):
    SOURCE_CODE = "source_code"
    TEXT = "text"
    DIRECTORY = "directory"
    BINARY = "binary"
    ARCHIVE = "archive"
    UNKNOWN = "unknown"


class ObservationType(str, Enum):
    FILE_INVENTORY = "file_inventory"
    LANGUAGE_DETECTION = "language_detection"
    STRUCTURE = "structure"
    DEPENDENCY = "dependency"
    SYMBOL = "symbol"
    METADATA = "metadata"
    CONTENT_SUMMARY = "content_summary"
    BEHAVIOR = "behavior"
    OTHER = "other"


class EvidenceRelation(str, Enum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    NEUTRAL = "neutral"
    DERIVED_FROM = "derived_from"


class HypothesisStatus(str, Enum):
    PROPOSED = "proposed"
    OPEN = "open"
    SUPPORTED = "supported"
    REFUTED = "refuted"
    INCONCLUSIVE = "inconclusive"


class ConfidenceRank(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class SafetyClass(str, Enum):
    STATIC_ONLY = "static_only"
    SANDBOXED = "sandboxed"
    NETWORK_OPT_IN = "network_opt_in"
    FORBIDDEN = "forbidden"


class InvestigationStatus(str, Enum):
    CREATED = "created"
    INTAKE_COMPLETE = "intake_complete"
    ANALYZED = "analyzed"
    HYPOTHESES_FORMED = "hypotheses_formed"
    EXPERIMENTS_RUN = "experiments_run"
    RECONSTRUCTED = "reconstructed"
    VALIDATED = "validated"
    FAILED = "failed"


class Artifact(BaseModel):
    schema_version: str = SCHEMA_VERSION
    id: str = Field(default_factory=lambda: _new_id("art"))
    kind: ArtifactKind
    origin: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    content_digest: str | None = None
    size_bytes: int | None = None
    acquisition_timestamp: datetime = Field(default_factory=_utcnow)
    notes: str | None = None

    @field_validator("origin")
    @classmethod
    def origin_nonempty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("origin must be a non-empty string")
        return v.strip()


class Observation(BaseModel):
    schema_version: str = SCHEMA_VERSION
    id: str = Field(default_factory=lambda: _new_id("obs"))
    artifact_id: str
    observation_type: ObservationType
    payload: dict[str, Any]
    provenance: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=_utcnow)

    @model_validator(mode="after")
    def require_artifact_ref(self) -> Observation:
        if not self.artifact_id:
            raise ValueError("artifact_id is required")
        return self


class Evidence(BaseModel):
    schema_version: str = SCHEMA_VERSION
    id: str = Field(default_factory=lambda: _new_id("ev"))
    source_observation_ids: list[str]
    relation: EvidenceRelation
    claim_ref: str | None = None
    summary: str
    integrity_digest: str | None = None
    provenance: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=_utcnow)

    @field_validator("source_observation_ids")
    @classmethod
    def nonempty_sources(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("evidence must reference at least one observation")
        return v


class Hypothesis(BaseModel):
    schema_version: str = SCHEMA_VERSION
    id: str = Field(default_factory=lambda: _new_id("hyp"))
    claim: str
    status: HypothesisStatus = HypothesisStatus.PROPOSED
    confidence: ConfidenceRank = ConfidenceRank.UNKNOWN
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    contradicting_evidence_ids: list[str] = Field(default_factory=list)
    unresolved_assumptions: list[str] = Field(default_factory=list)
    notes: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    @field_validator("claim")
    @classmethod
    def claim_nonempty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("claim must be non-empty")
        return v.strip()


class Experiment(BaseModel):
    schema_version: str = SCHEMA_VERSION
    id: str = Field(default_factory=lambda: _new_id("exp"))
    objective: str
    hypothesis_ids: list[str] = Field(default_factory=list)
    procedure: str
    safety_class: SafetyClass = SafetyClass.STATIC_ONLY
    expected_outcomes: list[str] = Field(default_factory=list)
    actual_results: list[str] = Field(default_factory=list)
    comparison: str | None = None
    reproducibility: dict[str, Any] = Field(default_factory=dict)
    authorized: bool = False
    executed: bool = False
    created_at: datetime = Field(default_factory=_utcnow)
    executed_at: datetime | None = None

    @model_validator(mode="after")
    def safety_gate(self) -> Experiment:
        if self.executed and self.safety_class == SafetyClass.FORBIDDEN:
            raise ValueError("forbidden experiments must never be executed")
        if self.executed and self.safety_class == SafetyClass.NETWORK_OPT_IN and not self.authorized:
            raise ValueError("network experiments require explicit authorization")
        return self


class Component(BaseModel):
    id: str = Field(default_factory=lambda: _new_id("cmp"))
    name: str
    kind: str
    description: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    interfaces: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)


class InterfaceSpec(BaseModel):
    id: str = Field(default_factory=lambda: _new_id("ifc"))
    name: str
    direction: str = "unknown"
    description: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)


class SystemModel(BaseModel):
    schema_version: str = SCHEMA_VERSION
    id: str = Field(default_factory=lambda: _new_id("sys"))
    components: list[Component] = Field(default_factory=list)
    interfaces: list[InterfaceSpec] = Field(default_factory=list)
    dependencies: list[dict[str, str]] = Field(default_factory=list)
    data_flows: list[dict[str, Any]] = Field(default_factory=list)
    state_transitions: list[dict[str, Any]] = Field(default_factory=list)
    unresolved_areas: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utcnow)


class ValidationFinding(BaseModel):
    id: str = Field(default_factory=lambda: _new_id("vfd"))
    test_name: str
    expected: str
    actual: str
    matched: bool
    notes: str | None = None


class ValidationReport(BaseModel):
    schema_version: str = SCHEMA_VERSION
    id: str = Field(default_factory=lambda: _new_id("val"))
    investigation_id: str
    tests_executed: list[str] = Field(default_factory=list)
    findings: list[ValidationFinding] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    reproducibility: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_utcnow)

    @property
    def match_count(self) -> int:
        return sum(1 for f in self.findings if f.matched)

    @property
    def mismatch_count(self) -> int:
        return sum(1 for f in self.findings if not f.matched)


class Investigation(BaseModel):
    schema_version: str = SCHEMA_VERSION
    id: str = Field(default_factory=lambda: _new_id("inv"))
    status: InvestigationStatus = InvestigationStatus.CREATED
    artifacts: list[Artifact] = Field(default_factory=list)
    observations: list[Observation] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    experiments: list[Experiment] = Field(default_factory=list)
    system_model: SystemModel | None = None
    validation_report: ValidationReport | None = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def artifact_by_id(self, aid: str) -> Artifact | None:
        return next((a for a in self.artifacts if a.id == aid), None)

    def observation_by_id(self, oid: str) -> Observation | None:
        return next((o for o in self.observations if o.id == oid), None)

    def evidence_by_id(self, eid: str) -> Evidence | None:
        return next((e for e in self.evidence if e.id == eid), None)

    def hypothesis_by_id(self, hid: str) -> Hypothesis | None:
        return next((h for h in self.hypotheses if h.id == hid), None)

    def validate_references(self) -> list[str]:
        errors: list[str] = []
        art_ids = {a.id for a in self.artifacts}
        obs_ids = {o.id for o in self.observations}
        ev_ids = {e.id for e in self.evidence}
        hyp_ids = {h.id for h in self.hypotheses}
        for o in self.observations:
            if o.artifact_id not in art_ids:
                errors.append(f"observation {o.id} references missing artifact {o.artifact_id}")
        for e in self.evidence:
            for oid in e.source_observation_ids:
                if oid not in obs_ids:
                    errors.append(f"evidence {e.id} references missing observation {oid}")
        for h in self.hypotheses:
            for eid in h.supporting_evidence_ids + h.contradicting_evidence_ids:
                if eid not in ev_ids:
                    errors.append(f"hypothesis {h.id} references missing evidence {eid}")
        for exp in self.experiments:
            for hid in exp.hypothesis_ids:
                if hid not in hyp_ids:
                    errors.append(f"experiment {exp.id} references missing hypothesis {hid}")
        return errors


def content_digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
