"""End-to-end investigation pipeline orchestration."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from rea.analysis.pipeline import analyze_investigation
from rea.core.config import DEFAULT_CONFIG, REAConfig
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


def create_investigation(
    path: str | Path,
    *,
    config: REAConfig | None = None,
    notes: str | None = None,
) -> Investigation:
    """Intake a single artifact and create an investigation shell."""
    cfg = config or DEFAULT_CONFIG
    artifact = register_artifact(path, config=cfg, notes=notes)
    inv = Investigation(
        status=InvestigationStatus.INTAKE_COMPLETE,
        artifacts=[artifact],
        metadata={"source_path": str(Path(path).resolve())},
    )
    return inv


def run_full_pipeline(
    path: str | Path,
    *,
    config: REAConfig | None = None,
    store: JsonInvestigationStore | None = None,
    notes: str | None = None,
) -> Investigation:
    """Execute the complete supported investigation pipeline.

    Artifact → Intake → Observations → Evidence Graph → Hypotheses
    → Experiments → Reconstruction → Validation Report
    """
    cfg = config or DEFAULT_CONFIG
    inv = create_investigation(path, config=cfg, notes=notes)

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
