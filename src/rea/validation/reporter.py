"""Test generation interfaces, behavioral comparisons, and validation reports."""

from __future__ import annotations

from datetime import datetime, timezone

from rea.core.models import (
    Investigation,
    InvestigationStatus,
    ObservationType,
    ValidationFinding,
    ValidationReport,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def validate_investigation(investigation: Investigation) -> Investigation:
    """Run reconstruction checks and produce a validation report."""
    findings: list[ValidationFinding] = []
    tests: list[str] = []
    limitations: list[str] = []

    tests.append("reference_integrity")
    ref_errors = investigation.validate_references()
    findings.append(
        ValidationFinding(
            test_name="reference_integrity",
            expected="no dangling references",
            actual=f"{len(ref_errors)} error(s)",
            matched=len(ref_errors) == 0,
            notes="; ".join(ref_errors[:5]) if ref_errors else None,
        )
    )

    tests.append("observations_present")
    findings.append(
        ValidationFinding(
            test_name="observations_present",
            expected=">= 1 observation",
            actual=str(len(investigation.observations)),
            matched=len(investigation.observations) >= 1,
        )
    )

    tests.append("evidence_grounded")
    ungrounded = [e.id for e in investigation.evidence if not e.source_observation_ids]
    findings.append(
        ValidationFinding(
            test_name="evidence_grounded",
            expected="all evidence has source observations",
            actual=f"{len(ungrounded)} ungrounded",
            matched=len(ungrounded) == 0,
        )
    )

    tests.append("system_model_present")
    has_model = investigation.system_model is not None
    findings.append(
        ValidationFinding(
            test_name="system_model_present",
            expected="system model exists",
            actual="present" if has_model else "missing",
            matched=has_model,
        )
    )

    tests.append("language_consistency")
    langs = [
        o.payload.get("language")
        for o in investigation.observations
        if o.observation_type == ObservationType.LANGUAGE_DETECTION
    ]
    unique = set(langs)
    findings.append(
        ValidationFinding(
            test_name="language_consistency",
            expected="consistent language signals",
            actual=f"{len(unique)} distinct: {sorted(unique)}",
            matched=len(unique) <= 1,
            notes="Multiple languages may be valid for polyglot projects",
        )
    )

    tests.append("hypotheses_evidence_or_unknown")
    weak = []
    for h in investigation.hypotheses:
        if (
            not h.supporting_evidence_ids
            and not h.contradicting_evidence_ids
            and h.confidence.value != "unknown"
            and h.status.value not in {"inconclusive", "proposed"}
        ):
            weak.append(h.id)
    findings.append(
        ValidationFinding(
            test_name="hypotheses_evidence_or_unknown",
            expected="hypotheses with confidence have evidence links",
            actual=f"{len(weak)} weakly linked",
            matched=len(weak) == 0,
        )
    )

    if investigation.system_model:
        limitations.extend(investigation.system_model.unresolved_areas)
    limitations.append("v0.1 supports static source/text analysis only")
    limitations.append("Confidence ranks are qualitative, not calibrated probabilities")
    limitations.append("No dynamic execution or network observation in default pipeline")

    report = ValidationReport(
        investigation_id=investigation.id,
        tests_executed=tests,
        findings=findings,
        limitations=limitations,
        reproducibility={
            "schema_version": investigation.schema_version,
            "deterministic_fixtures": True,
            "pipeline": (
                "Artifact→Intake→Observations→Evidence→Hypotheses→"
                "Experiments→Reconstruction→Validation"
            ),
        },
    )
    investigation.validation_report = report
    investigation.status = InvestigationStatus.VALIDATED
    investigation.updated_at = _utcnow()
    return investigation
