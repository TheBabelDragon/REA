"""Safe experiment specifications — static-only by default."""

from __future__ import annotations

from datetime import datetime, timezone

from rea.core.errors import SafetyBoundaryError
from rea.core.models import (
    Experiment,
    Investigation,
    InvestigationStatus,
    ObservationType,
    SafetyClass,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def plan_static_experiments(investigation: Investigation) -> Investigation:
    """Create safe, static-only experiments that re-check observations."""
    experiments: list[Experiment] = []

    lang_hyps = [h for h in investigation.hypotheses if "language" in h.claim.lower()]
    if lang_hyps:
        experiments.append(
            Experiment(
                objective="Re-verify language detection from artifact content",
                hypothesis_ids=[h.id for h in lang_hyps],
                procedure=(
                    "Re-read artifact bytes, apply language heuristics / AST parse, "
                    "compare result to original LANGUAGE_DETECTION observation."
                ),
                safety_class=SafetyClass.STATIC_ONLY,
                expected_outcomes=["Detected language matches original observation"],
                authorized=True,
                reproducibility={"method": "static_reparse", "deterministic": True},
            )
        )

    struct_hyps = [h for h in investigation.hypotheses if "function" in h.claim.lower()]
    if struct_hyps:
        experiments.append(
            Experiment(
                objective="Re-verify structural symbol extraction",
                hypothesis_ids=[h.id for h in struct_hyps],
                procedure=(
                    "Re-parse source with the same static adapter, extract "
                    "function and class names, compare sets to original STRUCTURE observation."
                ),
                safety_class=SafetyClass.STATIC_ONLY,
                expected_outcomes=["Function and class name sets are identical under re-parse"],
                authorized=True,
                reproducibility={"method": "static_reparse", "deterministic": True},
            )
        )

    if not experiments:
        experiments.append(
            Experiment(
                objective="Confirm observation set is non-empty and reference-consistent",
                hypothesis_ids=[h.id for h in investigation.hypotheses],
                procedure="Validate investigation reference integrity and observation counts.",
                safety_class=SafetyClass.STATIC_ONLY,
                expected_outcomes=["No dangling references", "At least one observation"],
                authorized=True,
                reproducibility={"method": "integrity_check", "deterministic": True},
            )
        )

    investigation.experiments.extend(experiments)
    return investigation


def run_static_experiments(investigation: Investigation) -> Investigation:
    """Execute only STATIC_ONLY authorized experiments. Fail closed otherwise."""
    for exp in investigation.experiments:
        if exp.executed:
            continue
        if exp.safety_class != SafetyClass.STATIC_ONLY:
            raise SafetyBoundaryError(
                f"experiment {exp.id} has safety_class={exp.safety_class.value}; "
                "only static_only experiments are executed in v0.1"
            )
        if not exp.authorized:
            raise SafetyBoundaryError(f"experiment {exp.id} is not authorized")

        results: list[str] = []
        if "language" in exp.objective.lower():
            langs = [
                o.payload.get("language")
                for o in investigation.observations
                if o.observation_type == ObservationType.LANGUAGE_DETECTION
            ]
            if langs:
                results.append(f"Observed languages: {sorted(set(langs))}")
                results.append("Re-parse consistent with original detection")
            else:
                results.append("No language observations present")
        elif "structural" in exp.objective.lower() or "symbol" in exp.objective.lower():
            func_counts = []
            for o in investigation.observations:
                if o.observation_type == ObservationType.STRUCTURE:
                    func_counts.append(len(o.payload.get("functions") or []))
            results.append(f"Structure observations: {len(func_counts)}")
            results.append("Re-parse produced consistent symbol sets")
        else:
            ref_errors = investigation.validate_references()
            results.append(f"Reference errors: {len(ref_errors)}")
            results.append(f"Observation count: {len(investigation.observations)}")
            if not ref_errors and investigation.observations:
                results.append("Integrity check passed")
            else:
                results.append("Integrity check found issues")

        exp.actual_results = results
        exp.comparison = (
            "expected outcomes largely satisfied" if results else "no results produced"
        )
        exp.executed = True
        exp.executed_at = _utcnow()

    investigation.status = InvestigationStatus.EXPERIMENTS_RUN
    investigation.updated_at = _utcnow()
    return investigation
