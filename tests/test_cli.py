"""CLI command and exit-code tests."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from rea.cli.main import app

SAMPLES = Path(__file__).resolve().parent.parent / "samples"
HELLO = SAMPLES / "hello_calc.py"
FIXTURES = SAMPLES / "hello_calc_fixtures.json"

runner = CliRunner()


def test_inspect_exit_0() -> None:
    result = runner.invoke(app, ["inspect", str(HELLO)])
    assert result.exit_code == 0
    assert "source_code" in result.stdout or "Artifact" in result.stdout


def test_inspect_missing_exit_2() -> None:
    result = runner.invoke(app, ["inspect", "/nonexistent/rea_xyz.py"])
    assert result.exit_code == 2


def test_analyze_exit_0() -> None:
    result = runner.invoke(app, ["analyze", str(HELLO)])
    assert result.exit_code == 0
    assert "observation" in result.stdout.lower() or "language" in result.stdout.lower()


def test_investigate_report_validate_export(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    result = runner.invoke(app, ["investigate", str(HELLO)])
    assert result.exit_code == 0
    assert "inv_" in result.stdout
    inv_id = None
    for token in result.stdout.replace("\n", " ").split():
        if token.startswith("inv_"):
            inv_id = token.strip()
            break
    assert inv_id is not None

    report = runner.invoke(app, ["report", inv_id])
    assert report.exit_code == 0

    validate = runner.invoke(app, ["validate", inv_id])
    assert validate.exit_code in (0, 1)

    out_file = tmp_path / "out.json"
    export = runner.invoke(app, ["export", inv_id, "--format", "json", "-o", str(out_file)])
    assert export.exit_code == 0
    assert out_file.exists()
    data = json.loads(out_file.read_text(encoding="utf-8"))
    assert data["id"] == inv_id
    assert "schema_version" in data


def test_investigate_with_fixtures(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    result = runner.invoke(
        app, ["investigate", str(HELLO), "--fixtures", str(FIXTURES)]
    )
    assert result.exit_code == 0
    inv_id = None
    for token in result.stdout.replace("\n", " ").split():
        if token.startswith("inv_"):
            inv_id = token.strip()
            break
    assert inv_id is not None
    validate = runner.invoke(app, ["validate", inv_id])
    # With user fixtures, deliberate mismatch is skipped — expect success.
    assert validate.exit_code == 0


def test_report_missing_exit_4() -> None:
    result = runner.invoke(app, ["report", "inv_doesnotexist000"])
    assert result.exit_code == 4


def test_version() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "0.2" in result.stdout
