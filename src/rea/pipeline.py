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
from rea.evidence.project_graph import build_project_evidence_graph
from rea.experiments.planner import plan_static_experiments, run_static_experiments
from rea.hypotheses.engine import form_hypotheses
from rea.intake.project import intake_project
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
    project: bool | None = None,
) -> Investigation:
    """Create an investigation from a file or project directory.

    If *project* is True, or *path* is a directory and project is not False,
    bounded multi-file project intake is used. Single-file behaviour is
    preserved when *path* is a file or *project* is False.
    """
    cfg = config or DEFAULT_CONFIG
    p = Path(path)
    use_project = project if project is not None else p.is_dir()

    metadata: dict[str, Any] = {"source_path": str(p.resolve())}
    if fixtures is not None:
        metadata["validation_fixtures"] = fixtures

    if use_project and p.is_dir():
        root_art, records, file_arts = intake_project(p, config=cfg, notes=notes)
        metadata["project_intake"] = True
        metadata["project_file_count"] = len(records)
        metadata["project_analyzed_count"] = len(file_arts)
        return Investigation(
            status=InvestigationStatus.INTAKE_COMPLETE,
            artifacts=[root_art, *file_arts],
            project_files=records,
            metadata=metadata,
        )

    artifact = register_artifact(path, config=cfg, notes=notes)
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
    project: bool | None = None,
) -> Investigation:
    cfg = config or DEFAULT_CONFIG
    loaded = fixtures
    if fixtures_path is not None:
        loaded = _load_fixtures_file(fixtures_path)
    inv = create_investigation(path, config=cfg, notes=notes, fixtures=loaded, project=project)
    inv = analyze_investigation(inv)
    inv = build_evidence_graph(inv)
    if inv.project_files or inv.metadata.get("project_intake"):
        inv = build_project_evidence_graph(inv)
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
