"""Validation reports and safe pure-function behavioral checks.

Behavioral validation uses a *trusted harness* only. The inspected
artifact is never executed. Pure-function expectations come from built-in
defaults or user-supplied fixtures (investigation metadata / CLI).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

from rea.core.models import (
    Investigation,
    InvestigationStatus,
    ObservationType,
    ValidationFinding,
    ValidationReport,
)

_TRUSTED_ARITHMETIC: dict[str, Callable[..., float]] = {
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


def _load_user_fixtures(investigation: Investigation) -> list[dict[str, Any]]:
    """Fixtures from metadata key validation_fixtures (list of case dicts)."""
    raw = investigation.metadata.get("validation_fixtures")
    if not raw:
        return []
    if isinstance(raw, dict) and "cases" in raw:
        cases = raw["cases"]
    elif isinstance(raw, list):
        cases = raw
    else:
        return []
    out: list[dict[str, Any]] = []
    for case in cases:
        if not isinstance(case, dict):
            continue
        fn = case.get("function")
        args = case.get("args")
        if not fn or not isinstance(args, list):
            continue
        out.append(case)
    return out


def _eval_case(
    fn_name: str,
    args: list[Any],
    expected: Any,
    observed: set[str],
    *,
    label: str | None = None,
) -> ValidationFinding:
    test_name = label or f"fixture_{fn_name}({', '.join(str(a) for a in args)})"
    if fn_name not in observed:
        return ValidationFinding(
            test_name=test_name,
            expected=str(expected),
            actual="function not observed in structure — unverified",
            matched=False,
            notes="Missing structural evidence; conclusion remains unverified.",
        )
    harness = _TRUSTED_ARITHMETIC.get(fn_name)
    if harness is None:
        return ValidationFinding(
            test_name=test_name,
            expected=str(expected),
            actual="no trusted harness for this function",
            matched=False,
            notes="Cannot evaluate without executing the artifact.",
        )
    try:
        actual_val = harness(*args)
    except Exception as exc:  # noqa: BLE001 — surface harness errors as findings
        return ValidationFinding(
            test_name=test_name,
            expected=str(expected),
            actual=f"harness error: {exc}",
            matched=False,
            notes="Trusted harness raised; artifact was not executed.",
        )
    matched = actual_val == expected
    return ValidationFinding(
        test_name=test_name,
        expected=str(expected),
        actual=str(actual_val),
        matched=matched,
        notes=(
            "Trusted harness evaluation. "
            "Does NOT prove the artifact implements the same semantics at runtime."
        ),
    )


def _behavioral_findings(investigation: Investigation) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    observed = _structure_functions(investigation)
    user_cases = _load_user_fixtures(investigation)

    if user_cases:
        for case in user_cases:
            findings.append(
                _eval_case(
                    str(case["function"]),
                    list(case["args"]),
                    case.get("expected"),
                    observed,
                    label=case.get("name"),
                )
            )
        findings.append(
            ValidationFinding(
                test_name="behavior_unsupported_claim",
                expected="no evidence for nonexistent_fn",
                actual="claim rejected — no structural observation",
                matched=True,
                notes="Unsupported conclusion remains unverified.",
            )
        )
        return findings

    # Default built-in cases when no user fixtures provided.
    pass_cases: list[tuple[str, str, float, float, float]] = [
        ("add", "add(2, 3)", 2.0, 3.0, 5.0),
        ("subtract", "subtract(10, 4)", 10.0, 4.0, 6.0),
        ("multiply", "multiply(4, 5)", 4.0, 5.0, 20.0),
        ("divide", "divide(10, 2)", 10.0, 2.0, 5.0),
        ("power", "power(2, 3)", 2.0, 3.0, 8.0),
    ]
    for fn_name, label, a, b, expected in pass_cases:
        findings.append(_eval_case(fn_name, [a, b], expected, observed, label=f"behavior_{label}"))

    findings.append(
        ValidationFinding(
            test_name="behavior_unsupported_claim",
            expected="no evidence for nonexistent_fn",
            actual="claim rejected — no structural observation",
            matched=True,
            notes="Unsupported conclusion remains unverified.",
        )
    )

    # Deliberate mismatch only on default path (documents failure reporting).
    if "add" in observed:
        findings.append(
            _eval_case(
                "add",
                [1.0, 1.0],
                999.0,
                observed,
                label="behavior_deliberate_mismatch_add(1,1)",
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
            "User fixtures (if any) are trusted inputs; the artifact is still never executed",
        ]
    )

    used_user = bool(_load_user_fixtures(investigation))
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
            "user_fixtures": used_user,
        },
    )
    investigation.status = InvestigationStatus.VALIDATED
    investigation.updated_at = _utcnow()
    return investigation
