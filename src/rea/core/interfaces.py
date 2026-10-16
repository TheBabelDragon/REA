"""Pluggable interfaces for adapters and storage."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

from rea.core.models import Artifact, Observation


class AdapterCapability(BaseModel):
    """Declared capability of an analysis adapter."""

    id: str
    name: str
    description: str
    supported_kinds: list[str]
    produces_observation_types: list[str]
    requires_execution: bool = False
    requires_network: bool = False
    limitations: list[str] = Field(default_factory=list)


class AnalysisAdapter(ABC):
    """Base class for pluggable analysis adapters.

    Adapters MUST:
    - declare capabilities honestly
    - never execute untrusted code unless explicitly authorized
    - treat all artifact content as untrusted data
    - fail closed on safety boundary violations
    """

    @abstractmethod
    def capabilities(self) -> list[AdapterCapability]:
        """Return declared capabilities."""

    @abstractmethod
    def can_analyze(self, artifact: Artifact) -> bool:
        """Return True if this adapter can usefully analyze the artifact."""

    @abstractmethod
    def analyze(self, artifact: Artifact) -> list[Observation]:
        """Produce observations. Must not execute the artifact."""

    def name(self) -> str:
        return self.__class__.__name__


class InvestigationStore(ABC):
    """Abstract store for investigation records (local-first)."""

    @abstractmethod
    def save(self, investigation: Any) -> None:
        ...

    @abstractmethod
    def load(self, investigation_id: str) -> Any:
        ...

    @abstractmethod
    def list_ids(self) -> list[str]:
        ...
