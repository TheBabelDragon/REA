"""Pluggable interfaces for adapters and storage."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

from rea.core.models import Artifact, Observation, ProjectFileRecord


class AdapterCapability(BaseModel):
    id: str
    name: str
    description: str
    supported_kinds: list[str]
    produces_observation_types: list[str]
    requires_execution: bool = False
    requires_network: bool = False
    limitations: list[str] = Field(default_factory=list)


class AnalysisAdapter(ABC):
    @abstractmethod
    def capabilities(self) -> list[AdapterCapability]: ...

    @abstractmethod
    def can_analyze(self, artifact: Artifact) -> bool: ...

    @abstractmethod
    def analyze(self, artifact: Artifact) -> list[Observation]: ...

    def name(self) -> str:
        return self.__class__.__name__


class ProjectAnalysisAdapter(ABC):
    """Project-level analysis interface; compatible with single-file adapters.

    Implementations must never import, execute, or evaluate inspected project code.
    """

    @abstractmethod
    def capabilities(self) -> list[AdapterCapability]: ...

    @abstractmethod
    def can_analyze_project(self, files: list[ProjectFileRecord]) -> bool: ...

    @abstractmethod
    def analyze_project(
        self,
        root: str,
        files: list[ProjectFileRecord],
        artifacts: list[Artifact],
    ) -> list[Observation]: ...

    def name(self) -> str:
        return self.__class__.__name__


class InvestigationStore(ABC):
    @abstractmethod
    def save(self, investigation: Any) -> None: ...

    @abstractmethod
    def load(self, investigation_id: str) -> Any: ...

    @abstractmethod
    def list_ids(self) -> list[str]: ...
