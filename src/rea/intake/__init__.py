"""Intake."""

from rea.intake.project import intake_project
from rea.intake.registry import detect_kind, register_artifact

__all__ = ["detect_kind", "register_artifact", "intake_project"]
