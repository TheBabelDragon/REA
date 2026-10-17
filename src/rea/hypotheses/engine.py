"""Hypothesis formation from evidence-linked observations.

Distinguishes directly observed facts from inferred conclusions.
Missing evidence never silently becomes a verified fact.
"""

from __future__ import annotations

from datetime import datetime, timezone

from rea.core.models import (
    ConfidenceRank,
    Hypothesis,
    HypothesisStatus,
    Investigation,
    InvestigationStatus,
    ObservationType,
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
        hypotheses.append(
            Hypothesis(
                claim=f"Primary implementation language is {primary}",
                status=HypothesisStatus.SUPPORTED
                if conf == ConfidenceRank.HIGH
                else HypothesisStatus.OPEN,
                confidence=conf,
            )
        )

    all_funcs: list[str] = []
    all_classes: list[str] = []
    for o in investigation.observations:
        if o.observation_type == ObservationType.STRUCTURE:
            all_funcs.extend(o.payload.get("functions") or [])
            all_classes.extend(o.payload.get("classes") or [])
    unique_funcs = sorted(set(all_funcs))
    unique_classes = sorted(set(all_classes))
    if unique_funcs or unique_classes:
        hypotheses.append(
            Hypothesis(
                claim=(
                    f"Artifact exposes {len(unique_funcs)} function(s) and "
                    f"{len(unique_classes)} class(es)"
                ),
                status=HypothesisStatus.SUPPORTED,
                confidence=ConfidenceRank.HIGH,
                unresolved_assumptions=[
                    "Heuristic extraction may miss nested or dynamically defined symbols"
                ],
            )
        )

    pure_candidates = {"add", "subtract", "multiply", "divide", "power"}
    observed_pure = [f for f in unique_funcs if f in pure_candidates]
    if observed_pure:
        hypotheses.append(
            Hypothesis(
                claim=(
                    "Observed pure-function symbols "
                    f"({', '.join(observed_pure)}) are intended as deterministic "
                    "arithmetic operations (inferred from naming and structure only)"
                ),
                status=HypothesisStatus.OPEN,
                confidence=ConfidenceRank.MEDIUM,
                unresolved_assumptions=[
                    "Naming convention does not prove runtime semantics",
                    "Static analysis cannot confirm exception handling or edge cases",
                    "Runtime equivalence requires independent behavioral validation",
                ],
            )
        )

    all_deps: list[str] = []
    for o in investigation.observations:
        if o.observation_type == ObservationType.DEPENDENCY:
            all_deps.extend(o.payload.get("dependencies") or [])
    unique_deps = sorted(set(all_deps))
    if unique_deps:
        hypotheses.append(
            Hypothesis(
                claim=f"Artifact depends on: {', '.join(unique_deps[:15])}",
                status=HypothesisStatus.OPEN,
                confidence=ConfidenceRank.MEDIUM,
                unresolved_assumptions=[
                    "Runtime dependencies may differ from static imports"
                ],
            )
        )

    if not hypotheses:
        hypotheses.append(
            Hypothesis(
                claim="Insufficient static signals to form specific structural claims",
                status=HypothesisStatus.INCONCLUSIVE,
                confidence=ConfidenceRank.UNKNOWN,
            )
        )

    investigation.hypotheses.extend(hypotheses)
    for h in hypotheses:
        claim_l = h.claim.lower()
        if "language" in claim_l and lang_ev:
            link_evidence_to_hypothesis(investigation, h.id, lang_ev)
        elif (
            "function" in claim_l or "pure-function" in claim_l or "exposes" in claim_l
        ) and struct_ev:
            link_evidence_to_hypothesis(investigation, h.id, struct_ev)
        elif "depends on" in claim_l and dep_ev:
            link_evidence_to_hypothesis(investigation, h.id, dep_ev)

    investigation.status = InvestigationStatus.HYPOTHESES_FORMED
    investigation.updated_at = _utcnow()
    return investigation
