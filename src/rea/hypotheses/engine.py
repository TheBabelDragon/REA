"""Hypothesis formation."""

from __future__ import annotations

from datetime import datetime, timezone

from rea.core.models import (
    ConfidenceRank, EvidenceRelation, Hypothesis, HypothesisStatus,
    Investigation, InvestigationStatus, ObservationType,
)
from rea.evidence.graph import link_evidence_to_hypothesis


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def form_hypotheses(investigation: Investigation) -> Investigation:
    lang_ev, struct_ev, dep_ev = [], [], []
    obs_by_id = {o.id: o for o in investigation.observations}
    for ev in investigation.evidence:
        for oid in ev.source_observation_ids:
            obs = obs_by_id.get(oid)
            if not obs:
                continue
            if obs.observation_type == ObservationType.LANGUAGE_DETECTION:
                lang_ev.append(ev.id)
            elif obs.observation_type == ObservationType.STRUCTURE:
                struct_ev.append(ev.id)
            elif obs.observation_type == ObservationType.DEPENDENCY:
                dep_ev.append(ev.id)

    hypotheses: list[Hypothesis] = []
    languages = {
        o.payload.get("language", "unknown")
        for o in investigation.observations
        if o.observation_type == ObservationType.LANGUAGE_DETECTION
    }
    if languages:
        primary = sorted(languages)[0]
        conf = ConfidenceRank.HIGH if len(languages) == 1 else ConfidenceRank.MEDIUM
        hypotheses.append(Hypothesis(
            claim=f"Primary implementation language is {primary}",
            status=HypothesisStatus.SUPPORTED if conf == ConfidenceRank.HIGH else HypothesisStatus.OPEN,
            confidence=conf,
        ))

    all_funcs, all_classes = [], []
    for o in investigation.observations:
        if o.observation_type == ObservationType.STRUCTURE:
            all_funcs.extend(o.payload.get("functions") or [])
            all_classes.extend(o.payload.get("classes") or [])
    if all_funcs or all_classes:
        hypotheses.append(Hypothesis(
            claim=f"Artifact exposes {len(set(all_funcs))} function(s) and {len(set(all_classes))} class(es)",
            status=HypothesisStatus.SUPPORTED,
            confidence=ConfidenceRank.HIGH,
            unresolved_assumptions=["Heuristic extraction may miss nested symbols"],
        ))

    all_deps = []
    for o in investigation.observations:
        if o.observation_type == ObservationType.DEPENDENCY:
            all_deps.extend(o.payload.get("dependencies") or [])
    unique_deps = sorted(set(all_deps))
    if unique_deps:
        hypotheses.append(Hypothesis(
            claim=f"Artifact depends on: {', '.join(unique_deps[:15])}",
            status=HypothesisStatus.OPEN,
            confidence=ConfidenceRank.MEDIUM,
            unresolved_assumptions=["Runtime dependencies may differ from static imports"],
        ))

    if not hypotheses:
        hypotheses.append(Hypothesis(
            claim="Insufficient static signals to form specific structural claims",
            status=HypothesisStatus.INCONCLUSIVE,
            confidence=ConfidenceRank.UNKNOWN,
        ))

    investigation.hypotheses.extend(hypotheses)
    for h in hypotheses:
        if "language" in h.claim.lower() and lang_ev:
            link_evidence_to_hypothesis(investigation, h.id, lang_ev)
        elif "function" in h.claim.lower() and struct_ev:
            link_evidence_to_hypothesis(investigation, h.id, struct_ev)
        elif "depends on" in h.claim.lower() and dep_ev:
            link_evidence_to_hypothesis(investigation, h.id, dep_ev)

    investigation.status = InvestigationStatus.HYPOTHESES_FORMED
    investigation.updated_at = _utcnow()
    return investigation
