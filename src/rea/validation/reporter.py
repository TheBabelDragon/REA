"""Validation reports."""

from __future__ import annotations

from datetime import datetime, timezone

from rea.core.models import Investigation, InvestigationStatus, ObservationType, ValidationFinding, ValidationReport


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def validate_investigation(investigation: Investigation) -> Investigation:
    findings: list[ValidationFinding] = []
    tests: list[str] = []
    limitations: list[str] = []

    tests.append("reference_integrity")
    ref_errors = investigation.validate_references()
    findings.append(ValidationFinding(
        test_name="reference_integrity", expected="no dangling references",
        actual=f"{len(ref_errors)} error(s)", matched=len(ref_errors) == 0,
    ))

    tests.append("observations_present")
    findings.append(ValidationFinding(
        test_name="observations_present", expected=">= 1 observation",
        actual=str(len(investigation.observations)), matched=len(investigation.observations) >= 1,
    ))

    tests.append("evidence_grounded")
    ungrounded = [e.id for e in investigation.evidence if not e.source_observation_ids]
    findings.append(ValidationFinding(
        test_name="evidence_grounded", expected="all evidence has source observations",
        actual=f"{len(ungrounded)} ungrounded", matched=len(ungrounded) == 0,
    ))

    tests.append("system_model_present")
    findings.append(ValidationFinding(
        test_name="system_model_present", expected="system model exists",
        actual="present" if investigation.system_model else "missing",
        matched=investigation.system_model is not None,
    ))

    if investigation.system_model:
        limitations.extend(investigation.system_model.unresolved_areas)
    limitations.extend([
        "v0.1 supports static source/text analysis only",
        "Confidence ranks are qualitative, not calibrated probabilities",
        "No dynamic execution or network observation in default pipeline",
    ])

    investigation.validation_report = ValidationReport(
        investigation_id=investigation.id, tests_executed=tests, findings=findings,
        limitations=limitations,
        reproducibility={"schema_version": investigation.schema_version, "deterministic_fixtures": True},
    )
    investigation.status = InvestigationStatus.VALIDATED
    investigation.updated_at = _utcnow()
    return investigation
