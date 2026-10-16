"""Tests for core domain models."""
from __future__ import annotations
import pytest
from pydantic import ValidationError
from rea.core.models import (
    Artifact, ArtifactKind, Evidence, EvidenceRelation, Experiment,
    Hypothesis, Observation, ObservationType, SafetyClass,
)

def test_artifact_requires_origin() -> None:
    with pytest.raises(ValidationError):
        Artifact(kind=ArtifactKind.TEXT, origin="")

def test_evidence_requires_sources() -> None:
    with pytest.raises(ValidationError):
        Evidence(source_observation_ids=[], relation=EvidenceRelation.SUPPORTS, summary="empty")

def test_hypothesis_requires_claim() -> None:
    with pytest.raises(ValidationError):
        Hypothesis(claim="")

def test_experiment_forbidden_cannot_execute() -> None:
    with pytest.raises(ValidationError):
        Experiment(objective="bad", procedure="x", safety_class=SafetyClass.FORBIDDEN, executed=True, authorized=True)

def test_experiment_network_requires_auth() -> None:
    with pytest.raises(ValidationError):
        Experiment(objective="net", procedure="x", safety_class=SafetyClass.NETWORK_OPT_IN, executed=True, authorized=False)

def test_observation_ok() -> None:
    o = Observation(artifact_id="art_1", observation_type=ObservationType.METADATA, payload={"k": "v"})
    assert o.id.startswith("obs_")
