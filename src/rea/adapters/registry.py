"""Adapter registry — discovers and selects available analysis adapters."""

from __future__ import annotations

from rea.adapters.source_code import SourceCodeAdapter
from rea.core.interfaces import AnalysisAdapter
from rea.core.models import Artifact


def default_adapters() -> list[AnalysisAdapter]:
    """Return the built-in adapter set for v0.1."""
    return [SourceCodeAdapter()]


def adapters_for(artifact: Artifact, adapters: list[AnalysisAdapter] | None = None) -> list[AnalysisAdapter]:
    """Select adapters that declare they can analyze the given artifact."""
    pool = adapters if adapters is not None else default_adapters()
    return [a for a in pool if a.can_analyze(artifact)]


def all_capabilities(adapters: list[AnalysisAdapter] | None = None) -> list[dict]:
    """Collect capability declarations from all adapters."""
    pool = adapters if adapters is not None else default_adapters()
    caps = []
    for a in pool:
        for c in a.capabilities():
            caps.append(c.model_dump())
    return caps
