"""End-to-end investigation lifecycle tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from rea.core.config import REAConfig, SafetyConfig, StorageConfig
from rea.core.errors import IntakeError, InvestigationNotFoundError, SafetyBoundaryError
from rea.core.models import (
    ArtifactKind,
    ConfidenceRank,
    HypothesisStatus,
    InvestigationStatus,
    ObservationType,
)
from rea.core.store import JsonInvestigationStore
from rea.intake.registry import register_artifact
from rea.pipeline import run_full_pipeline
from rea.validation.reporter import validate_investigation

SAMPLES = Path(__file__).resolve().parent.parent / "samples"
HELLO = SAMPLES / "hello_calc.py"


@pytest.fixture
def store(tmp_path: Path) -> JsonInvestigationStore:
    cfg = REAConfig(storage=StorageConfig(data_dir=tmp_path / "rea_data"))
    return JsonInvestigationStore(cfg)


def test_full_pipeline_hello_calc(store: JsonInvestigationStore) -> None:
    inv = run_full_pipeline(HELLO, store=store)
    assert inv.id.startswith("inv_")
    assert inv.status == InvestigationStatus.VALIDATED
    assert len(inv.artifacts) == 1
    art = inv.artifacts[0]
    assert art.kind == ArtifactKind.SOURCE_CODE
    assert art.content_digest is not None
    assert art.size_bytes and art.size_bytes > 0

    types = {o.observation_type for o in inv.observations}
    assert ObservationType.LANGUAGE_DETECTION in types
    assert ObservationType.STRUCTURE in types
    assert ObservationType.DEPENDENCY in types

    assert len(inv.evidence) >= 1
    for e in inv.evidence:
        assert e.source_observation_ids

    assert len(inv.hypotheses) >= 2
    lang_h = next(h for h in inv.hypotheses if "language" in h.claim.lower())
    assert lang_h.status == HypothesisStatus.SUPPORTED
    assert lang_h.confidence == ConfidenceRank.HIGH
    assert lang_h.supporting_evidence_ids

    assert inv.system_model is not None
    assert inv.system_model.unresolved_areas

    assert inv.validation_report is not None
    vr = inv.validation_report
    assert vr.match_count >= 1
    assert any(f.test_name == "reference_integrity" and f.matched for f in vr.findings)
    assert any(
        f.test_name.startswith("behavior_deliberate_mismatch") and not f.matched
        for f in vr.findings
    )
    assert any("artifact" in lim.lower() or "runtime" in lim.lower() for lim in vr.limitations)
    assert vr.reproducibility.get("artifact_executed") is False

    loaded = store.load(inv.id)
    assert loaded.id == inv.id
    assert len(loaded.observations) == len(inv.observations)
    assert loaded.validation_report is not None


def test_export_deterministic_and_readback(store: JsonInvestigationStore, tmp_path: Path) -> None:
    inv = run_full_pipeline(HELLO, store=store)
    data1 = inv.model_dump(mode="json")
    text1 = json.dumps(data1, indent=2, sort_keys=True, default=str)
    text2 = json.dumps(data1, indent=2, sort_keys=True, default=str)
    assert text1 == text2

    out_path = tmp_path / "export.json"
    out_path.write_text(text1, encoding="utf-8")
    reloaded = json.loads(out_path.read_text(encoding="utf-8"))
    assert reloaded["id"] == inv.id
    assert reloaded["schema_version"] == inv.schema_version


def test_intake_digest_stable() -> None:
    a1 = register_artifact(HELLO)
    a2 = register_artifact(HELLO)
    assert a1.content_digest == a2.content_digest
    assert a1.size_bytes == a2.size_bytes


def test_missing_file() -> None:
    with pytest.raises(IntakeError, match="does not exist"):
        register_artifact("/nonexistent/rea_artifact_xyz.py")


def test_oversized_artifact(tmp_path: Path) -> None:
    big = tmp_path / "big.py"
    big.write_bytes(b"x" * 100)
    cfg = REAConfig(safety=SafetyConfig(max_artifact_size_bytes=50))
    with pytest.raises(SafetyBoundaryError, match="exceeds limit"):
        register_artifact(big, config=cfg)


def test_path_traversal_store(store: JsonInvestigationStore) -> None:
    with pytest.raises(InvestigationNotFoundError):
        store.load("../etc/passwd")
    with pytest.raises(InvestigationNotFoundError):
        store.load("inv_abc/../../secret")


def test_validate_idempotent(store: JsonInvestigationStore) -> None:
    inv = run_full_pipeline(HELLO, store=store)
    inv2 = validate_investigation(inv)
    assert inv2.status == InvestigationStatus.VALIDATED
    assert inv2.validation_report is not None


def test_unsupported_binary(tmp_path: Path) -> None:
    bin_path = tmp_path / "blob.bin"
    bin_path.write_bytes(b"\x00\x01\x02\x03")
    from rea.core.errors import UnsupportedArtifactError
    from rea.analysis.pipeline import collect_observations

    art = register_artifact(bin_path)
    assert art.kind.value in {"binary", "unknown"}
    with pytest.raises(UnsupportedArtifactError):
        collect_observations(art)
