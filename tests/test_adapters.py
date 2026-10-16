"""Tests for analysis adapters."""

from __future__ import annotations

from pathlib import Path

from rea.adapters.source_code import SourceCodeAdapter
from rea.core.models import ArtifactKind, ObservationType
from rea.intake.registry import register_artifact

SAMPLES = Path(__file__).resolve().parent.parent / "samples"


def test_source_adapter_capabilities() -> None:
    adapter = SourceCodeAdapter()
    caps = adapter.capabilities()
    assert len(caps) == 1
    assert caps[0].requires_execution is False
    assert caps[0].requires_network is False
    assert "source_code" in caps[0].supported_kinds


def test_analyze_hello_calc() -> None:
    art = register_artifact(SAMPLES / "hello_calc.py")
    adapter = SourceCodeAdapter()
    assert adapter.can_analyze(art)
    obs = adapter.analyze(art)
    types = {o.observation_type for o in obs}
    assert ObservationType.LANGUAGE_DETECTION in types
    assert ObservationType.STRUCTURE in types
    assert ObservationType.DEPENDENCY in types

    lang = next(o for o in obs if o.observation_type == ObservationType.LANGUAGE_DETECTION)
    assert lang.payload["language"] == "python"

    struct = next(o for o in obs if o.observation_type == ObservationType.STRUCTURE)
    assert "add" in struct.payload["functions"]
    assert "Calculator" in struct.payload["classes"]


def test_adapter_rejects_binary_kind() -> None:
    from rea.core.models import Artifact

    art = Artifact(kind=ArtifactKind.BINARY, origin="/tmp/fake.bin")
    adapter = SourceCodeAdapter()
    assert not adapter.can_analyze(art)
