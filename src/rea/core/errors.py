"""REA error hierarchy."""

from __future__ import annotations


class REAError(Exception):
    def __init__(self, message: str, *, code: str = "REA_ERROR") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class IntakeError(REAError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="INTAKE_ERROR")


class AdapterError(REAError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="ADAPTER_ERROR")


class SafetyBoundaryError(REAError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="SAFETY_BOUNDARY")


class ReferenceError(REAError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="REFERENCE_ERROR")


class UnsupportedArtifactError(REAError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="UNSUPPORTED_ARTIFACT")


class InvestigationNotFoundError(REAError):
    def __init__(self, investigation_id: str) -> None:
        super().__init__(f"investigation not found: {investigation_id}", code="INVESTIGATION_NOT_FOUND")
        self.investigation_id = investigation_id
