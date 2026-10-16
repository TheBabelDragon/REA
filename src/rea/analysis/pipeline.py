"""Structural analysis, dependency extraction, and behavior observations."""

from __future__ import annotations

from rea.adapters.registry import adapters_for, default_adapters
from rea.core.errors import AdapterError, UnsupportedArtifactError
from rea.core.interfaces import AnalysisAdapter
from rea.core.models import Artifact, Investigation, InvestigationStatus, Observation


def collect_observations(
    artifact: Artifact,
    *,
    adapters: list[AnalysisAdapter] | None = None,
) -> list[Observation]:
    """Run all capable adapters against the artifact and collect observations."""
    selected = adapters_for(artifact, adapters)
    if not selected:
        raise UnsupportedArtifactError(
            f"no adapter supports kind={artifact.kind.value} for {artifact.origin}"
        )

    observations: list[Observation] = []
    errors: list[str] = []
    for adapter in selected:
        try:
            obs = adapter.analyze(artifact)
            observations.extend(obs)
        except AdapterError as exc:
            errors.append(f"{adapter.name()}: {exc}")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{adapter.name()} unexpected: {exc}")

    if not observations and errors:
        raise AdapterError("; ".join(errors))
    return observations


def analyze_investigation(
    investigation: Investigation,
    *,
    adapters: list[AnalysisAdapter] | None = None,
) -> Investigation:
    """Append observations for every artifact in the investigation."""
    pool = adapters if adapters is not None else default_adapters()
    for artifact in investigation.artifacts:
        obs = collect_observations(artifact, adapters=pool)
        investigation.observations.extend(obs)
    investigation.status = InvestigationStatus.ANALYZED
    return investigation
