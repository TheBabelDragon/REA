"""Project-level evidence graph construction."""
from __future__ import annotations

import hashlib
from typing import Any

from rea.core.models import (
    EvidenceGraph,
    GraphEdge,
    GraphEdgeKind,
    GraphNode,
    GraphNodeKind,
    Investigation,
    Observation,
    ObservationType,
    RelationCertainty,
    _new_id,
)


def _stable_hash(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]


def _edge_id(kind: str, source_id: str, target_id: str, extra: str = "") -> str:
    return f"edge_{_stable_hash(f'{kind}|{source_id}|{target_id}|{extra}')}"


def _path_to_module(relative_path: str) -> str:
    p = relative_path.replace("\\", "/")
    if p.endswith(".py"):
        p = p[:-3]
    if p.endswith("/__init__"):
        p = p[: -len("/__init__")]
    elif p == "__init__":
        p = ""
    return p.replace("/", ".")


def build_project_evidence_graph(investigation: Investigation) -> Investigation:
    graph = EvidenceGraph()
    node_ids: dict[str, str] = {}

    def ensure_node(
        key: str,
        kind: GraphNodeKind,
        label: str,
        *,
        attributes: dict[str, Any] | None = None,
        source_location: dict[str, Any] | None = None,
        evidence_ids: list[str] | None = None,
    ) -> str:
        if key in node_ids:
            return node_ids[key]
        nid = f"node_{kind.value}_{_stable_hash(key)}"
        node_ids[key] = nid
        graph.nodes.append(
            GraphNode(
                id=nid,
                kind=kind,
                label=label,
                attributes=attributes or {},
                source_location=source_location,
                evidence_ids=evidence_ids or [],
            )
        )
        return nid

    obs_to_ev: dict[str, str] = {}
    for e in investigation.evidence:
        for oid in e.source_observation_ids:
            obs_to_ev[oid] = e.id

    for rec in investigation.project_files:
        if rec.status.value in ("unsupported", "skipped") and not rec.content_digest:
            continue
        file_key = f"file:{rec.relative_path}"
        ensure_node(
            file_key,
            GraphNodeKind.FILE,
            rec.relative_path,
            attributes={
                "digest": rec.content_digest,
                "language": rec.language,
                "status": rec.status.value,
            },
            source_location={"path": rec.relative_path},
        )
        if rec.language == "python":
            mod = _path_to_module(rec.relative_path)
            mod_key = f"module:{mod}"
            mod_nid = ensure_node(
                mod_key,
                GraphNodeKind.MODULE,
                mod or "(root)",
                attributes={"relative_path": rec.relative_path},
                source_location={"path": rec.relative_path},
            )
            graph.edges.append(
                GraphEdge(
                    id=_edge_id("contains", node_ids[file_key], mod_nid),
                    kind=GraphEdgeKind.CONTAINS,
                    source_id=node_ids[file_key],
                    target_id=mod_nid,
                    certainty=RelationCertainty.INFERRED,
                    provenance={"source": "project_intake"},
                    evidence_ids=[],
                    notes="file hosts module",
                )
            )

    for obs in investigation.observations:
        ev_id = obs_to_ev.get(obs.id)
        ev_ids = [ev_id] if ev_id else []
        if obs.observation_type == ObservationType.STRUCTURE:
            _add_structure(graph, obs, ensure_node, node_ids, ev_ids)
        elif obs.observation_type == ObservationType.DEPENDENCY:
            _add_deps(graph, obs, ensure_node, node_ids, ev_ids)

    for obs in investigation.observations:
        ensure_node(
            f"obs:{obs.id}",
            GraphNodeKind.OBSERVATION,
            obs.observation_type.value,
            attributes={"observation_id": obs.id},
        )
    for e in investigation.evidence:
        ek = f"ev:{e.id}"
        ensure_node(
            ek,
            GraphNodeKind.EVIDENCE,
            e.summary[:80],
            attributes={"evidence_id": e.id},
            evidence_ids=[e.id],
        )
        for oid in e.source_observation_ids:
            ok = f"obs:{oid}"
            if ok in node_ids:
                graph.edges.append(
                    GraphEdge(
                        id=_edge_id("derived_from", node_ids[ek], node_ids[ok]),
                        kind=GraphEdgeKind.DERIVED_FROM,
                        source_id=node_ids[ek],
                        target_id=node_ids[ok],
                        certainty=RelationCertainty.OBSERVED,
                        provenance={"source": "evidence_pipeline"},
                        evidence_ids=[e.id],
                    )
                )

    unresolved: list[str] = []
    for edge in graph.edges:
        if edge.kind == GraphEdgeKind.UNRESOLVED_REF or edge.certainty == RelationCertainty.UNRESOLVED:
            unresolved.append(f"{edge.kind.value}:{edge.source_id}->{edge.target_id}")
    for obs in investigation.observations:
        if obs.observation_type == ObservationType.DEPENDENCY:
            for u in obs.payload.get("unresolved_imports") or []:
                unresolved.append(
                    f"unresolved_import:{obs.payload.get('module')}:{u.get('module')}"
                )
        if obs.observation_type == ObservationType.STRUCTURE:
            for d in obs.payload.get("dynamic_uncertainty") or []:
                unresolved.append(f"dynamic:{obs.payload.get('module')}:{d.get('name')}")
    graph.unresolved_references = sorted(set(unresolved))
    graph.validate_integrity()
    investigation.evidence_graph = graph
    return investigation


def _add_structure(graph, obs, ensure_node, node_ids, ev_ids) -> None:
    module = obs.payload.get("module") or ""
    rel = obs.payload.get("relative_path") or ""
    mod_nid = ensure_node(
        f"module:{module}",
        GraphNodeKind.MODULE,
        module or "(root)",
        attributes={"relative_path": rel},
        source_location={"path": rel},
        evidence_ids=ev_ids,
    )
    for d in obs.payload.get("definitions") or []:
        name = d.get("name")
        if not name:
            continue
        sym_key = f"symbol:{module}.{name}"
        sym_nid = ensure_node(
            sym_key,
            GraphNodeKind.SYMBOL,
            f"{module}.{name}" if module else name,
            attributes={"def_kind": d.get("kind")},
            source_location={"path": rel, "line": d.get("lineno")},
            evidence_ids=ev_ids,
        )
        graph.edges.append(
            GraphEdge(
                id=_edge_id("defines", mod_nid, sym_nid, str(d.get("lineno") or "")),
                kind=GraphEdgeKind.DEFINES,
                source_id=mod_nid,
                target_id=sym_nid,
                certainty=RelationCertainty.OBSERVED,
                provenance={"observation_id": obs.id},
                evidence_ids=ev_ids,
                source_location={"path": rel, "line": d.get("lineno")},
            )
        )
    for dyn in obs.payload.get("dynamic_uncertainty") or []:
        name = dyn.get("name") or "dynamic"
        unres_key = f"unresolved:dynamic:{module}.{name}:{dyn.get('lineno')}"
        unres_nid = ensure_node(
            unres_key,
            GraphNodeKind.UNRESOLVED,
            name,
            attributes={"kind": dyn.get("kind")},
            source_location={"path": rel, "line": dyn.get("lineno")},
        )
        graph.edges.append(
            GraphEdge(
                id=_edge_id("unresolved_ref", mod_nid, unres_nid, "dynamic"),
                kind=GraphEdgeKind.UNRESOLVED_REF,
                source_id=mod_nid,
                target_id=unres_nid,
                certainty=RelationCertainty.UNRESOLVED,
                provenance={"observation_id": obs.id},
                evidence_ids=ev_ids,
                notes="dynamic import or reflection",
            )
        )


def _add_deps(graph, obs, ensure_node, node_ids, ev_ids) -> None:
    module = obs.payload.get("module") or ""
    rel = obs.payload.get("relative_path") or ""
    mod_nid = ensure_node(
        f"module:{module}",
        GraphNodeKind.MODULE,
        module or "(root)",
        attributes={"relative_path": rel},
        source_location={"path": rel},
        evidence_ids=ev_ids,
    )
    for imp in obs.payload.get("resolved_imports") or []:
        target_mod = imp.get("module") or ""
        if imp.get("external"):
            tid = ensure_node(
                f"external:{target_mod}",
                GraphNodeKind.EXTERNAL,
                target_mod,
                attributes={"external": True},
            )
        elif imp.get("resolved") and imp.get("resolved_path"):
            tmod = _path_to_module(imp["resolved_path"])
            tid = ensure_node(
                f"module:{tmod}",
                GraphNodeKind.MODULE,
                tmod,
                attributes={"relative_path": imp["resolved_path"]},
            )
        else:
            continue
        graph.edges.append(
            GraphEdge(
                id=_edge_id("imports", mod_nid, tid, str(imp.get("lineno") or "")),
                kind=GraphEdgeKind.IMPORTS,
                source_id=mod_nid,
                target_id=tid,
                certainty=RelationCertainty.OBSERVED,
                provenance={"observation_id": obs.id},
                evidence_ids=ev_ids,
                source_location={"path": rel, "line": imp.get("lineno")},
            )
        )
    for imp in obs.payload.get("unresolved_imports") or []:
        target_mod = imp.get("module") or "?"
        unres_nid = ensure_node(
            f"unresolved:import:{module}:{target_mod}",
            GraphNodeKind.UNRESOLVED,
            target_mod,
            attributes={"kind": "missing_import", "from_module": module},
            source_location={"path": rel, "line": imp.get("lineno")},
        )
        graph.edges.append(
            GraphEdge(
                id=_edge_id("unresolved_ref", mod_nid, unres_nid, str(imp.get("lineno") or "")),
                kind=GraphEdgeKind.UNRESOLVED_REF,
                source_id=mod_nid,
                target_id=unres_nid,
                certainty=RelationCertainty.UNRESOLVED,
                provenance={"observation_id": obs.id},
                evidence_ids=ev_ids,
                notes="missing or ambiguous import",
            )
        )
