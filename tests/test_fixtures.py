"""User-supplied trusted fixture validation tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from rea.core.config import REAConfig, StorageConfig
from rea.core.errors import IntakeError
from rea.core.store import JsonInvestigationStore
from rea.pipeline import run_full_pipeline

SAMPLES = Path(__file__).resolve().parent.parent / "samples"
HELLO = SAMPLES / "hello_calc.py"
FIXTURES = SAMPLES / "hello_calc_fixtures.json"


@pytest.fixture
def store(tmp_path: Path) -> JsonInvestigationStore:
    cfg = REAConfig(storage=StorageConfig(data_dir=tmp_path / "rea_data"))
    return JsonInvestigationStore(cfg)


def test_pipeline_with_user_fixtures(store: JsonInvestigationStore) -> None:
    inv = run_full_pipeline(HELLO, store=store, fixtures_path=FIXTURES)
    assert inv.metadata.get("validation_fixtures") is not None
    vr = inv.validation_report
    assert vr is not None
    assert vr.reproducibility.get("artifact_executed") is False
    assert vr.reproducibility.get("user_fixtures") is True
    # User fixtures path should not include the deliberate mismatch case.
    assert not any("deliberate_mismatch" in f.test_name for f in vr.findings)
    fixture_findings = [f for f in vr.findings if f.test_name.startswith("fixture_")]
    assert len(fixture_findings) >= 5
    assert all(f.matched for f in fixture_findings)


def test_missing_fixtures_file() -> None:
    with pytest.raises(IntakeError, match="fixtures file does not exist"):
        run_full_pipeline(HELLO, fixtures_path="/nonexistent/fixtures.json")


def test_inline_fixtures(store: JsonInvestigationStore) -> None:
    cases = [{"function": "add", "args": [1, 1], "expected": 2.0}]
    inv = run_full_pipeline(HELLO, store=store, fixtures=cases)
    vr = inv.validation_report
    assert vr is not None
    assert any(f.matched and "add" in f.test_name for f in vr.findings)
