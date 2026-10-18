"""Evidence graph and project intake models (v0.3)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

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


class FileAnalysisStatus(str, Enum):
    PENDING = "pending"
    ANALYZED = "analyzed"
    SKIPPED = "skipped"
    UNSUPPORTED = "unsupported"
    ERROR = "error"
    OVERSIZED = "oversized"
    UNREADABLE = "unreadable"


class GraphNodeKind(str, Enum):
    FILE = "file"
    MODULE = "module"
    SYMBOL = "symbol"
    OBSERVATION = "observation"
    EVIDENCE = "evidence"
    HYPOTHESIS = "hypothesis"
    COMPONENT = "component"
    EXTERNAL = "external"
    UNRESOLVED = "unresolved"


class GraphEdgeKind(str, Enum):
    CONTAINS = "contains"
    IMPORTS = "imports"
    DEFINES = "defines"
    CALLS = "calls"
    REFERENCES = "references"
    DERIVED_FROM = "derived_from"
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    DEPENDS_ON = "depends_on"
    UNRESOLVED_REF = "unresolved_ref"


class RelationCertainty(str, Enum):
    OBSERVED = "observed"
    INFERRED = "inferred"
    UNRESOLVED = "unresolved"


class ProjectFileRecord(BaseModel):
    schema_version: str = SCHEMA_VERSION
    relative_path: str
    absolute_path: str
    content_digest: str | None = None
    size_bytes: int | None = None
    language: str | None = None
    kind: ArtifactKind = ArtifactKind.UNKNOWN
    status: FileAnalysisStatus = FileAnalysisStatus.PENDING
    error: str | None = None
    is_symlink: bool = False
    artifact_id: str | None = None


class GraphNode(BaseModel):
    schema_version: str = SCHEMA_VERSION
    id: str
    kind: GraphNodeKind
    label: str
    attributes: dict[str, Any] = Field(default_factory=dict)
    source_location: dict[str, Any] | None = None
    evidence_ids: list[str] = Field(default_factory=list)


class GraphEdge(BaseModel):
    schema_version: str = SCHEMA_VERSION
    id: str = Field(default_factory=lambda: _new_id("edge"))
    kind: GraphEdgeKind
    source_id: str
    target_id: str
    certainty: RelationCertainty = RelationCertainty.OBSERVED
    provenance: dict[str, Any] = Field(default_factory=dict)
    evidence_ids: list[str] = Field(default_factory=list)
    source_location: dict[str, Any] | None = None
    notes: str | None = None


class EvidenceGraph(BaseModel):
    schema_version: str = SCHEMA_VERSION
    id: str = Field(default_factory=lambda: _new_id("egraph"))
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    integrity_errors: list[str] = Field(default_factory=list)
    unresolved_references: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utcnow)

    def node_by_id(self, nid: str) -> GraphNode | None:
        return next((n for n in self.nodes if n.id == nid), None)

    def edges_from(self, nid: str) -> list[GraphEdge]:
        return [e for e in self.edges if e.source_id == nid]

    def edges_to(self, nid: str) -> list[GraphEdge]:
        return [e for e in self.edges if e.target_id == nid]

    def validate_integrity(self) -> list[str]:
        errors: list[str] = []
        node_ids = [n.id for n in self.nodes]
        seen: set[str] = set()
        for nid in node_ids:
            if nid in seen:
                errors.append(f"duplicate node id: {nid}")
            seen.add(nid)
        node_id_set = set(node_ids)
        edge_ids: set[str] = set()
        for e in self.edges:
            if e.id in edge_ids:
                errors.append(f"duplicate edge id: {e.id}")
            edge_ids.add(e.id)
            if e.source_id not in node_id_set:
                errors.append(f"edge {e.id} source missing: {e.source_id}")
            if e.target_id not in node_id_set:
                errors.append(f"edge {e.id} target missing: {e.target_id}")
            if not e.evidence_ids and e.certainty == RelationCertainty.OBSERVED:
                errors.append(f"edge {e.id} observed but has no evidence_ids")
        self.integrity_errors = errors
        return errors

    def canonical_dict(self) -> dict[str, Any]:
        nodes = sorted(
            [n.model_dump(mode="json") for n in self.nodes], key=lambda d: d["id"]
        )
        edges = sorted(
            [e.model_dump(mode="json") for e in self.edges], key=lambda d: d["id"]
        )
        return {
            "schema_version": self.schema_version,
            "id": self.id,
            "nodes": nodes,
            "edges": edges,
            "integrity_errors": sorted(self.integrity_errors),
            "unresolved_references": sorted(self.unresolved_references),
        }
