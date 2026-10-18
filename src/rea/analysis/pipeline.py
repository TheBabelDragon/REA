"""Observation collection."""

from __future__ import annotations

from rea.adapters.registry import adapters_for, default_adapters, default_project_adapters
from rea.core.errors import AdapterError, UnsupportedArtifactError
from rea.core.interfaces import AnalysisAdapter, ProjectAnalysisAdapter
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
    """Analyze artifacts. Project investigations use project adapters for Python files."""
    pool = adapters if adapters is not None else default_adapters()
    is_project = bool(investigation.project_files) or investigation.metadata.get("project_intake")

    if is_project and investigation.project_files:
        project_adapters: list[ProjectAnalysisAdapter] = default_project_adapters()
        root = investigation.metadata.get("source_path") or (
            investigation.artifacts[0].origin if investigation.artifacts else ""
        )
        file_arts = [a for a in investigation.artifacts if a.metadata.get("relative_path")]
        if not file_arts:
            file_arts = [a for a in investigation.artifacts if a.kind.value != "directory"]

        any_obs = False
        errors: list[str] = []
        for padapter in project_adapters:
            if not padapter.can_analyze_project(investigation.project_files):
                continue
            try:
                obs = padapter.analyze_project(root, investigation.project_files, file_arts)
                investigation.observations.extend(obs)
                any_obs = True
            except AdapterError as exc:
                errors.append(f"{padapter.name()}: {exc}")
            except Exception as exc:
                errors.append(f"{padapter.name()} unexpected: {exc}")

        for art in file_arts:
            rel = art.metadata.get("relative_path", "")
            if rel.endswith(".py") or rel.endswith(".pyi"):
                continue
            try:
                investigation.observations.extend(collect_observations(art, adapters=pool))
                any_obs = True
            except UnsupportedArtifactError:
                continue
            except AdapterError as exc:
                errors.append(str(exc))

        for art in investigation.artifacts:
            if art.kind.value == "directory":
                try:
                    investigation.observations.extend(collect_observations(art, adapters=pool))
                    any_obs = True
                except (UnsupportedArtifactError, AdapterError):
                    pass

        if not any_obs and errors:
            raise AdapterError("; ".join(errors))
    else:
        for artifact in investigation.artifacts:
            investigation.observations.extend(collect_observations(artifact, adapters=pool))

    investigation.status = InvestigationStatus.ANALYZED
    return investigation
