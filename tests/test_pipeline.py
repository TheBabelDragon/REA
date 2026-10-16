"""Unit and integration tests for the investigation pipeline."""

from __future__ import annotations

from pathlib import Path

import pytest

from rea.core.models import (
    ConfidenceRank,
    InvestigationStatus,
    SafetyClass,
)
from rea.core.store import JsonInvestigationStore
from rea.pipeline import create_investigation, run_full_pipeline

SAMPLES = Path(__file__).resolve().parent.parent / "samples"


def test_create_investigation() -> None:
    inv = create_investigation(SAMPLES / "hello_calc.py")
    assert inv.status == InvestigationStatus.INTAKE_COMPLETE
    assert len(inv.artifacts) == 1
    assert inv.artifacts[0].kind.value == "source_code"


def test_full_pipeline(tmp_path: Path) -> None:
    from rea.core.config import REAConfig, StorageConfig

    cfg = REAConfig(storage=StorageConfig(data_dir=tmp_path / "rea_data"))
    inv = run_full_pipeline(SAMPLES / "hello_calc.py", config=cfg)

    assert inv.status == InvestigationStatus.VALIDATED
    assert len(inv.observations) >= 3
    assert len(inv.evidence) >= 1
    assert len(inv.hypotheses) >= 1
    assert inv.system_model is not None
    assert inv.validation_report is not None
    assert inv.validation_report.match_count >= 1

    errors = inv.validate_references()
    assert errors == []

    for exp in inv.experiments:
        assert exp.safety_class == SafetyClass.STATIC_ONLY
        assert exp.executed is True

    for h in inv.hypotheses:
        assert h.confidence in ConfidenceRank

    store = JsonInvestigationStore(cfg)
    loaded = store.load(inv.id)
    assert loaded.id == inv.id


def test_export_roundtrip(tmp_path: Path) -> None:
    from rea.core.config import REAConfig, StorageConfig
    import json

    cfg = REAConfig(storage=StorageConfig(data_dir=tmp_path / "rea_data"))
    inv = run_full_pipeline(SAMPLES / "hello_calc.py", config=cfg)
    data = inv.model_dump(mode="json")
    text = json.dumps(data)
    restored = type(inv).model_validate(json.loads(text))
    assert restored.id == inv.id


def test_malformed_references() -> None:
    from rea.core.models import Investigation, Observation, ObservationType

    inv = Investigation()
    inv.observations.append(
        Observation(
            artifact_id="missing_art",
            observation_type=ObservationType.METADATA,
            payload={},
        )
    )
    errors = inv.validate_references()
    assert any("missing artifact" in e for e in errors)


def test_unsupported_binary(tmp_path: Path) -> None:
    from rea.core.errors import UnsupportedArtifactError
    from rea.analysis.pipeline import collect_observations
    from rea.intake.registry import register_artifact

    bin_path = tmp_path / "fake.bin"
    bin_path.write_bytes(b"\x00\x01\x02\x03\x04\x05")
    art = register_artifact(bin_path)
    with pytest.raises(UnsupportedArtifactError):
        collect_observations(art)
