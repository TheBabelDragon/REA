"""Observation collection."""

from __future__ import annotations

from rea.adapters.registry import adapters_for, default_adapters
from rea.core.errors import AdapterError, UnsupportedArtifactError
from rea.core.interfaces import AnalysisAdapter
from rea.core.models import Artifact, Investigation, InvestigationStatus, Observation


def collect_observations(
    artifact: Artifact, *, adapters: list[AnalysisAdapter] | None = None
) -> list[Observation]:
    selected = adapters_for(artifact, adapters)
    if not selected:
        raise UnsupportedArtifactError(
            f"no adapter supports kind={artifact.kind.value} for {artifact.origin}"
        )
    observations: list[Observation] = []
    errors: list[str] = []
    for adapter in selected:
        try:
            observations.extend(adapter.analyze(artifact))
        except AdapterError as exc:
            errors.append(f"{adapter.name()}: {exc}")
        except Exception as exc:
            errors.append(f"{adapter.name()} unexpected: {exc}")
    if not observations and errors:
        raise AdapterError("; ".join(errors))
    return observations


def analyze_investigation(
    investigation: Investigation, *, adapters: list[AnalysisAdapter] | None = None
) -> Investigation:
    pool = adapters if adapters is not None else default_adapters()
    for artifact in investigation.artifacts:
        investigation.observations.extend(collect_observations(artifact, adapters=pool))
    investigation.status = InvestigationStatus.ANALYZED
    return investigation
