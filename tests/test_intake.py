"""Tests for artifact intake."""

from __future__ import annotations

from pathlib import Path

import pytest

from rea.core.errors import IntakeError, SafetyBoundaryError
from rea.core.models import ArtifactKind
from rea.intake.registry import detect_kind, register_artifact


SAMPLES = Path(__file__).resolve().parent.parent / "samples"


def test_register_source_file() -> None:
    path = SAMPLES / "hello_calc.py"
    art = register_artifact(path)
    assert art.kind == ArtifactKind.SOURCE_CODE
    assert art.content_digest is not None
    assert art.size_bytes is not None
    assert art.size_bytes > 0
    assert "hello_calc.py" in art.origin


def test_detect_kind_python() -> None:
    assert detect_kind(SAMPLES / "hello_calc.py") == ArtifactKind.SOURCE_CODE


def test_register_missing_path() -> None:
    with pytest.raises(IntakeError):
        register_artifact("/nonexistent/path/xyz.py")


def test_register_directory(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("x = 1\n")
    (tmp_path / "b.txt").write_text("hello\n")
    art = register_artifact(tmp_path)
    assert art.kind == ArtifactKind.DIRECTORY
    assert art.metadata["entry_count"] >= 2
