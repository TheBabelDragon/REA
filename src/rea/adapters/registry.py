"""Adapter registry."""

from __future__ import annotations

from rea.adapters.python_project import PythonProjectAdapter
from rea.adapters.source_code import SourceCodeAdapter
from rea.core.interfaces import AnalysisAdapter, ProjectAnalysisAdapter
from rea.core.models import Artifact


def default_adapters() -> list[AnalysisAdapter]:
    return [SourceCodeAdapter()]


def default_project_adapters() -> list[ProjectAnalysisAdapter]:
    return [PythonProjectAdapter()]


def adapters_for(artifact: Artifact, adapters: list[AnalysisAdapter] | None = None) -> list[AnalysisAdapter]:
    pool = adapters if adapters is not None else default_adapters()
    return [a for a in pool if a.can_analyze(artifact)]


def all_capabilities(adapters: list[AnalysisAdapter] | None = None) -> list[dict]:
    pool = adapters if adapters is not None else default_adapters()
    caps = [c.model_dump() for a in pool for c in a.capabilities()]
    for pa in default_project_adapters():
        caps.extend(c.model_dump() for c in pa.capabilities())
    return caps
