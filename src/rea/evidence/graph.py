"""Evidence graph construction."""

from __future__ import annotations

from rea.core.models import Evidence, EvidenceRelation, Investigation, Observation, ObservationType


def observations_to_evidence(observations: list[Observation]) -> list[Evidence]:
    evidence: list[Evidence] = []
    for obs in observations:
        evidence.append(
            Evidence(
                source_observation_ids=[obs.id],
                relation=EvidenceRelation.DERIVED_FROM,
                summary=_summarize_observation(obs),
                provenance={
                    "observation_type": obs.observation_type.value,
                    "adapter": obs.provenance.get("adapter"),
                    "capability_id": obs.provenance.get("capability_id"),
                },
            )
        )
    return evidence


def _summarize_observation(obs: Observation) -> str:
    t, p = obs.observation_type, obs.payload
    if t == ObservationType.LANGUAGE_DETECTION:
        return f"Detected language: {p.get('language', 'unknown')}"
    if t == ObservationType.STRUCTURE:
        return f"Structure: {len(p.get('functions') or [])} function(s), {len(p.get('classes') or [])} class(es)"
    if t == ObservationType.DEPENDENCY:
        deps = p.get("dependencies") or []
        return f"Dependencies: {', '.join(deps[:10])}"
    if t == ObservationType.CONTENT_SUMMARY:
        return f"Content: {p.get('line_count', '?')} lines"
    if t == ObservationType.FILE_INVENTORY:
        return f"Inventory: {p.get('entry_count', 0)} entries"
    if t == ObservationType.METADATA:
        return f"Metadata for {p.get('path', '?')}"
    return f"Observation of type {t.value}"


def build_evidence_graph(investigation: Investigation) -> Investigation:
    existing = {tuple(e.source_observation_ids) for e in investigation.evidence}
    for e in observations_to_evidence(investigation.observations):
        if tuple(e.source_observation_ids) not in existing:
            investigation.evidence.append(e)
    return investigation


def link_evidence_to_hypothesis(
    investigation: Investigation, hypothesis_id: str, evidence_ids: list[str],
    *, relation: EvidenceRelation = EvidenceRelation.SUPPORTS,
) -> Investigation:
    hyp = investigation.hypothesis_by_id(hypothesis_id)
    if hyp is None:
        raise ValueError(f"hypothesis not found: {hypothesis_id}")
    for eid in evidence_ids:
        ev = investigation.evidence_by_id(eid)
        if ev is None:
            continue
        ev.claim_ref = hypothesis_id
        ev.relation = relation
        if relation == EvidenceRelation.SUPPORTS and eid not in hyp.supporting_evidence_ids:
            hyp.supporting_evidence_ids.append(eid)
        elif relation == EvidenceRelation.CONTRADICTS and eid not in hyp.contradicting_evidence_ids:
            hyp.contradicting_evidence_ids.append(eid)
    return investigation
