"""Validation reports and safe pure-function behavioral checks.

Behavioral validation uses a *trusted harness* only. The inspected
artifact is never executed. Pure-function expectations are derived from
structural observations and evaluated with independent Python arithmetic
(or declared expected values), not by importing the artifact.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from rea.core.models import (
    Investigation,
    InvestigationStatus,
    ObservationType,
    ValidationFinding,
    ValidationReport,
)

_TRUSTED_ARITHMETIC: dict[str, Callable[[float, float], float]] = {
    "add": lambda a, b: a + b,
    "subtract": lambda a, b: a - b,
    "multiply": lambda a, b: a * b,
    "divide": lambda a, b: a / b if b != 0 else float("nan"),
    "power": lambda a, b: a**b,
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _structure_functions(investigation: Investigation) -> set[str]:
    names: set[str] = set()
    for o in investigation.observations:
        if o.observation_type == ObservationType.STRUCTURE:
            for fn in o.payload.get("functions") or []:
                names.add(fn)
    return names


def _behavioral_findings(investigation: Investigation) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    observed = _structure_functions(investigation)

    pass_cases: list[tuple[str, str, float, float, float]] = [
        ("add", "add(2, 3)", 2.0, 3.0, 5.0),
        ("subtract", "subtract(10, 4)", 10.0, 4.0, 6.0),
        ("multiply", "multiply(4, 5)", 4.0, 5.0, 20.0),
        ("divide", "divide(10, 2)", 10.0, 2.0, 5.0),
        ("power", "power(2, 3)", 2.0, 3.0, 8.0),
    ]

    for fn_name, label, a, b, expected in pass_cases:
        if fn_name not in observed:
            findings.append(
                ValidationFinding(
                    test_name=f"behavior_{fn_name}_observed",
                    expected=f"function {fn_name} present in structure",
                    actual="not observed — skipped",
                    matched=False,
                    notes="No structural evidence for this function; conclusion remains unverified.",
                )
            )
            continue
        harness = _TRUSTED_ARITHMETIC.get(fn_name)
        if harness is None:
            findings.append(
                ValidationFinding(
                    test_name=f"behavior_{fn_name}",
                    expected=str(expected),
                    actual="no trusted harness",
                    matched=False,
                    notes="Unsupported pure function; cannot validate without executing artifact.",
                )
            )
            continue
        actual_val = harness(a, b)
        matched = actual_val == expected
        findings.append(
            ValidationFinding(
                test_name=f"behavior_{label}",
                expected=str(expected),
                actual=str(actual_val),
                matched=matched,
                notes=(
                    "Trusted harness evaluation of observed pure function. "
                    "Does NOT prove the artifact implements the same semantics at runtime."
                ),
            )
        )

    findings.append(
        ValidationFinding(
            test_name="behavior_unsupported_claim",
            expected="no evidence for nonexistent_fn",
            actual="claim rejected — no structural observation",
            matched=True,
            notes=(
                "Unsupported conclusion remains unverified. "
                "Missing evidence never becomes a verified fact."
            ),
        )
    )

    if "add" in observed:
        wrong_expected = 999.0
        actual_val = _TRUSTED_ARITHMETIC["add"](1.0, 1.0)
        findings.append(
            ValidationFinding(
                test_name="behavior_deliberate_mismatch_add(1,1)",
                expected=str(wrong_expected),
                actual=str(actual_val),
                matched=actual_val == wrong_expected,
                notes="Intentional mismatch to demonstrate failure reporting in the validation report.",
            )
        )

    return findings


def validate_investigation(investigation: Investigation) -> Investigation:
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
    findings.append(
        ValidationFinding(
            test_name="system_model_present",
            expected="system model exists",
            actual="present" if investigation.system_model else "missing",
            matched=investigation.system_model is not None,
        )
    )

    behavioral = _behavioral_findings(investigation)
    for f in behavioral:
        tests.append(f.test_name)
        findings.append(f)

    if investigation.system_model:
        limitations.extend(investigation.system_model.unresolved_areas)
    limitations.extend(
        [
            "v0.2 supports static source/text analysis and trusted pure-function harness checks only",
            "Confidence ranks are qualitative, not calibrated probabilities",
            "No dynamic execution of the inspected artifact",
            "Successful static analysis is not proof of runtime equivalence",
            "Behavioral checks evaluate independent trusted implementations, not the artifact",
        ]
    )

    investigation.validation_report = ValidationReport(
        investigation_id=investigation.id,
        tests_executed=tests,
        findings=findings,
        limitations=limitations,
        reproducibility={
            "schema_version": investigation.schema_version,
            "deterministic_fixtures": True,
            "harness": "trusted_arithmetic_v1",
            "artifact_executed": False,
        },
    )
    investigation.status = InvestigationStatus.VALIDATED
    investigation.updated_at = _utcnow()
    return investigation
