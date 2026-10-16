"""REA error hierarchy."""

from __future__ import annotations


class REAError(Exception):
    """Base error for all REA failures."""

    def __init__(self, message: str, *, code: str = "REA_ERROR") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class IntakeError(REAError):
    """Artifact intake or validation failure."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="INTAKE_ERROR")


class AdapterError(REAError):
    """Adapter execution or capability error."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="ADAPTER_ERROR")


class SafetyBoundaryError(REAError):
    """Operation exceeds configured safety boundary. Fail closed."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="SAFETY_BOUNDARY")


class ReferenceError(REAError):
    """Malformed or inconsistent cross-reference."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="REFERENCE_ERROR")


class UnsupportedArtifactError(REAError):
    """Artifact kind is not supported by available adapters."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="UNSUPPORTED_ARTIFACT")


class InvestigationNotFoundError(REAError):
    """Investigation record not found in store."""

    def __init__(self, investigation_id: str) -> None:
        super().__init__(
            f"investigation not found: {investigation_id}",
            code="INVESTIGATION_NOT_FOUND",
        )
        self.investigation_id = investigation_id
