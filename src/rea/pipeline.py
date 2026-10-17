"""End-to-end investigation pipeline orchestration."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rea.analysis.pipeline import analyze_investigation
from rea.core.config import DEFAULT_CONFIG, REAConfig
from rea.core.errors import IntakeError
from rea.core.models import Investigation, InvestigationStatus
from rea.core.store import JsonInvestigationStore
from rea.evidence.graph import build_evidence_graph
from rea.experiments.planner import plan_static_experiments, run_static_experiments
from rea.hypotheses.engine import form_hypotheses
from rea.intake.registry import register_artifact
from rea.reconstruction.builder import reconstruct
from rea.validation.reporter import validate_investigation


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _load_fixtures_file(path: str | Path) -> dict[str, Any] | list[Any]:
    p = Path(path).resolve()
    if not p.is_file():
        raise IntakeError(f"fixtures file does not exist: {p}")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise IntakeError(f"cannot read fixtures file: {exc}") from exc
    if not isinstance(data, (dict, list)):
        raise IntakeError("fixtures file must be a JSON object or array")
    return data


def create_investigation(
    path: str | Path,
    *,
    config: REAConfig | None = None,
    notes: str | None = None,
    fixtures: dict[str, Any] | list[Any] | None = None,
) -> Investigation:
    cfg = config or DEFAULT_CONFIG
    artifact = register_artifact(path, config=cfg, notes=notes)
    metadata: dict[str, Any] = {"source_path": str(Path(path).resolve())}
    if fixtures is not None:
        metadata["validation_fixtures"] = fixtures
    return Investigation(
        status=InvestigationStatus.INTAKE_COMPLETE,
        artifacts=[artifact],
        metadata=metadata,
    )


def run_full_pipeline(
    path: str | Path,
    *,
    config: REAConfig | None = None,
    store: JsonInvestigationStore | None = None,
    notes: str | None = None,
    fixtures: dict[str, Any] | list[Any] | None = None,
    fixtures_path: str | Path | None = None,
) -> Investigation:
    cfg = config or DEFAULT_CONFIG
    loaded = fixtures
    if fixtures_path is not None:
        loaded = _load_fixtures_file(fixtures_path)
    inv = create_investigation(path, config=cfg, notes=notes, fixtures=loaded)
    inv = analyze_investigation(inv)
    inv = build_evidence_graph(inv)
    inv = form_hypotheses(inv)
    inv = plan_static_experiments(inv)
    inv = run_static_experiments(inv)
    inv = reconstruct(inv)
    inv = validate_investigation(inv)
    inv.updated_at = _utcnow()
    if store is not None:
        store.save(inv)
    else:
        JsonInvestigationStore(cfg).save(inv)
    return inv
