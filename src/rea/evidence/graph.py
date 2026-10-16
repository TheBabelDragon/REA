"""Provenance-tracked evidence records and evidence graph construction."""

from __future__ import annotations

from rea.core.models import (
    Evidence,
    EvidenceRelation,
    Investigation,
    Observation,
    ObservationType,
)


def observations_to_evidence(observations: list[Observation]) -> list[Evidence]:
    """Convert raw observations into evidence records with provenance."""
    evidence: list[Evidence] = []
    for obs in observations:
        summary = _summarize_observation(obs)
        evidence.append(
            Evidence(
                source_observation_ids=[obs.id],
                relation=EvidenceRelation.DERIVED_FROM,
                summary=summary,
                provenance={
                    "observation_type": obs.observation_type.value,
                    "adapter": obs.provenance.get("adapter"),
                    "capability_id": obs.provenance.get("capability_id"),
                },
            )
        )
    return evidence


def _summarize_observation(obs: Observation) -> str:
    t = obs.observation_type
    p = obs.payload
    if t == ObservationType.LANGUAGE_DETECTION:
        return f"Detected language: {p.get('language', 'unknown')}"
    if t == ObservationType.STRUCTURE:
        funcs = p.get("functions") or []
        classes = p.get("classes") or []
        return (
            f"Structure: {len(funcs)} function(s), {len(classes)} class(es); "
            f"language={p.get('language', '?')}"
        )
    if t == ObservationType.DEPENDENCY:
        deps = p.get("dependencies") or []
        return f"Dependencies: {', '.join(deps[:10])}" + (
            f" (+{len(deps) - 10} more)" if len(deps) > 10 else ""
        )
    if t == ObservationType.CONTENT_SUMMARY:
        return (
            f"Content: {p.get('line_count', '?')} lines, "
            f"{p.get('char_count', '?')} chars"
        )
    if t == ObservationType.FILE_INVENTORY:
        return f"Inventory: {p.get('entry_count', 0)} entries under {p.get('root', '?')}"
    if t == ObservationType.METADATA:
        return f"Metadata for {p.get('path', '?')}"
    return f"Observation of type {t.value}"


def build_evidence_graph(investigation: Investigation) -> Investigation:
    """Populate investigation.evidence from observations."""
    new_ev = observations_to_evidence(investigation.observations)
    existing_obs_links = {
        tuple(e.source_observation_ids) for e in investigation.evidence
    }
    for e in new_ev:
        key = tuple(e.source_observation_ids)
        if key not in existing_obs_links:
            investigation.evidence.append(e)
    return investigation


def link_evidence_to_hypothesis(
    investigation: Investigation,
    hypothesis_id: str,
    evidence_ids: list[str],
    *,
    relation: EvidenceRelation = EvidenceRelation.SUPPORTS,
) -> Investigation:
    """Attach evidence to a hypothesis and update the evidence claim_ref."""
    hyp = investigation.hypothesis_by_id(hypothesis_id)
    if hyp is None:
        raise ValueError(f"hypothesis not found: {hypothesis_id}")

    for eid in evidence_ids:
        ev = investigation.evidence_by_id(eid)
        if ev is None:
            continue
        ev.claim_ref = hypothesis_id
        ev.relation = relation
        if relation == EvidenceRelation.SUPPORTS:
            if eid not in hyp.supporting_evidence_ids:
                hyp.supporting_evidence_ids.append(eid)
        elif relation == EvidenceRelation.CONTRADICTS:
            if eid not in hyp.contradicting_evidence_ids:
                hyp.contradicting_evidence_ids.append(eid)
    return investigation
