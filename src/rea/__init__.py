"""REA — Reverse Engineer Anything.

A modular, evidence-driven reverse-engineering framework that turns
observable artifacts and behavior into structured, evidence-backed,
testable reconstructions.
"""

__version__ = "0.1.0"
__schema_version__ = "1.0.0"

from rea.core.models import (
    Artifact,
    Evidence,
    Experiment,
    Hypothesis,
    Observation,
    SystemModel,
    ValidationReport,
)

__all__ = [
    "__version__",
    "__schema_version__",
    "Artifact",
    "Observation",
    "Evidence",
    "Hypothesis",
    "Experiment",
    "SystemModel",
    "ValidationReport",
]
