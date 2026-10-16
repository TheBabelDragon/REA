"""Competing explanations, confidence ranking, and evidence linkage."""

from __future__ import annotations

from datetime import datetime, timezone

from rea.core.models import (
    ConfidenceRank,
    EvidenceRelation,
    Hypothesis,
    HypothesisStatus,
    Investigation,
    ObservationType,
)
from rea.evidence.graph import link_evidence_to_hypothesis


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def form_hypotheses(investigation: Investigation) -> Investigation:
    """Generate initial hypotheses from observations and evidence."""
    lang_ev: list[str] = []
    struct_ev: list[str] = []
    dep_ev: list[str] = []

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

    languages = set()
    for o in investigation.observations:
        if o.observation_type == ObservationType.LANGUAGE_DETECTION:
            languages.add(o.payload.get("language", "unknown"))
    if languages:
        primary = sorted(languages)[0]
        conf = ConfidenceRank.HIGH if len(languages) == 1 else ConfidenceRank.MEDIUM
        h = Hypothesis(
            claim=f"Primary implementation language is {primary}",
            status=HypothesisStatus.SUPPORTED if conf == ConfidenceRank.HIGH else HypothesisStatus.OPEN,
            confidence=conf,
            unresolved_assumptions=[] if conf == ConfidenceRank.HIGH else [
                "Multiple language signals may indicate polyglot project"
            ],
        )
        hypotheses.append(h)

    all_funcs: list[str] = []
    all_classes: list[str] = []
    for o in investigation.observations:
        if o.observation_type == ObservationType.STRUCTURE:
            all_funcs.extend(o.payload.get("functions") or [])
            all_classes.extend(o.payload.get("classes") or [])
    if all_funcs or all_classes:
        h = Hypothesis(
            claim=(
                f"Artifact exposes {len(set(all_funcs))} distinct function(s) "
                f"and {len(set(all_classes))} class(es)/type(s)"
            ),
            status=HypothesisStatus.SUPPORTED,
            confidence=ConfidenceRank.HIGH if all_funcs or all_classes else ConfidenceRank.LOW,
            unresolved_assumptions=[
                "Heuristic extraction may miss nested or dynamically generated symbols"
            ],
        )
        hypotheses.append(h)

    all_deps: list[str] = []
    for o in investigation.observations:
        if o.observation_type == ObservationType.DEPENDENCY:
            all_deps.extend(o.payload.get("dependencies") or [])
    unique_deps = sorted(set(all_deps))
    if unique_deps:
        h = Hypothesis(
            claim=f"Artifact depends on: {', '.join(unique_deps[:15])}"
            + (f" (+{len(unique_deps) - 15} more)" if len(unique_deps) > 15 else ""),
            status=HypothesisStatus.OPEN,
            confidence=ConfidenceRank.MEDIUM,
            unresolved_assumptions=[
                "Import names may be relative, aliased, or optional",
                "Runtime dependencies may differ from static imports",
            ],
        )
        hypotheses.append(h)

    if not hypotheses:
        hypotheses.append(
            Hypothesis(
                claim="Insufficient static signals to form specific structural claims",
                status=HypothesisStatus.INCONCLUSIVE,
                confidence=ConfidenceRank.UNKNOWN,
                unresolved_assumptions=["Artifact may require alternative adapters"],
            )
        )

    investigation.hypotheses.extend(hypotheses)

    for h in hypotheses:
        if "language" in h.claim.lower() and lang_ev:
            link_evidence_to_hypothesis(
                investigation, h.id, lang_ev, relation=EvidenceRelation.SUPPORTS
            )
        elif "function" in h.claim.lower() and struct_ev:
            link_evidence_to_hypothesis(
                investigation, h.id, struct_ev, relation=EvidenceRelation.SUPPORTS
            )
        elif "depends on" in h.claim.lower() and dep_ev:
            link_evidence_to_hypothesis(
                investigation, h.id, dep_ev, relation=EvidenceRelation.SUPPORTS
            )

    from rea.core.models import InvestigationStatus

    investigation.status = InvestigationStatus.HYPOTHESES_FORMED
    investigation.updated_at = _utcnow()
    return investigation
