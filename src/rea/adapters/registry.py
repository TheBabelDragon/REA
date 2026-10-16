"""Adapter registry."""

from __future__ import annotations

from rea.adapters.source_code import SourceCodeAdapter
from rea.core.interfaces import AnalysisAdapter
from rea.core.models import Artifact


def default_adapters() -> list[AnalysisAdapter]:
    return [SourceCodeAdapter()]


def adapters_for(artifact: Artifact, adapters: list[AnalysisAdapter] | None = None) -> list[AnalysisAdapter]:
    pool = adapters if adapters is not None else default_adapters()
    return [a for a in pool if a.can_analyze(artifact)]


def all_capabilities(adapters: list[AnalysisAdapter] | None = None) -> list[dict]:
    pool = adapters if adapters is not None else default_adapters()
    return [c.model_dump() for a in pool for c in a.capabilities()]
