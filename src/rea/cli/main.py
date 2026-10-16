"""REA command-line interface."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from rea import __version__
from rea.adapters.registry import all_capabilities, adapters_for
from rea.analysis.pipeline import collect_observations
from rea.core.errors import (
    IntakeError, InvestigationNotFoundError, REAError,
    SafetyBoundaryError, UnsupportedArtifactError,
)
from rea.core.store import JsonInvestigationStore
from rea.intake.registry import register_artifact
from rea.pipeline import run_full_pipeline
from rea.validation.reporter import validate_investigation

app = typer.Typer(
    name="rea",
    help="REA — Reverse Engineer Anything.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console(stderr=True)
out = Console()


def _exit_error(msg: str, code: int = 1) -> None:
    console.print(f"[red]error:[/red] {msg}")
    raise typer.Exit(code)


@app.command("inspect")
def inspect_cmd(path: Path = typer.Argument(..., help="Path to artifact")) -> None:
    """Inventory an artifact and report supported analysis capabilities."""
    try:
        artifact = register_artifact(path)
    except (IntakeError, SafetyBoundaryError) as exc:
        _exit_error(str(exc), 2)
    out.print(Panel(f"[bold]Artifact[/bold]  {artifact.origin}", title="REA inspect"))
    table = Table(show_header=True, header_style="bold")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("id", artifact.id)
    table.add_row("kind", artifact.kind.value)
    table.add_row("size_bytes", str(artifact.size_bytes))
    digest = artifact.content_digest or "n/a"
    table.add_row("digest", digest[:16] + "…" if len(digest) > 16 else digest)
    out.print(table)
    capable = adapters_for(artifact)
    out.print("\n[bold]Supported capabilities:[/bold]")
    if not capable:
        out.print("  [yellow]None — kind not supported.[/yellow]")
    else:
        for a in capable:
            for c in a.capabilities():
                out.print(f"  • {c.name} ({c.id})")
                for lim in c.limitations:
                    out.print(f"      limitation: {lim}")


@app.command("analyze")
def analyze_cmd(path: Path = typer.Argument(..., help="Path to artifact")) -> None:
    """Collect structural observations."""
    try:
        artifact = register_artifact(path)
        observations = collect_observations(artifact)
    except UnsupportedArtifactError as exc:
        _exit_error(str(exc), 3)
    except REAError as exc:
        _exit_error(str(exc), 1)
    out.print(Panel(f"Collected {len(observations)} observation(s)", title="REA analyze"))
    for obs in observations:
        out.print(f"\n[cyan]{obs.observation_type.value}[/cyan]  id={obs.id}")
        payload = {k: v for k, v in obs.payload.items() if k != "preview"}
        out.print(json.dumps(payload, indent=2, default=str)[:800])


@app.command("investigate")
def investigate_cmd(
    path: Path = typer.Argument(..., help="Path to artifact"),
    notes: Optional[str] = typer.Option(None, "--notes"),
) -> None:
    """Execute the complete investigation pipeline."""
    try:
        inv = run_full_pipeline(path, notes=notes)
    except UnsupportedArtifactError as exc:
        _exit_error(str(exc), 3)
    except REAError as exc:
        _exit_error(str(exc), 1)
    out.print(Panel(
        f"[bold]Investigation[/bold] {inv.id}\nStatus: {inv.status.value}\n"
        f"Observations: {len(inv.observations)}  Evidence: {len(inv.evidence)}  "
        f"Hypotheses: {len(inv.hypotheses)}",
        title="REA investigate",
    ))
    out.print(f"\nUse: [bold]rea report {inv.id}[/bold]")


@app.command("report")
def report_cmd(investigation_id: str = typer.Argument(...)) -> None:
    """Display findings, evidence, hypotheses."""
    try:
        inv = JsonInvestigationStore().load(investigation_id)
    except InvestigationNotFoundError as exc:
        _exit_error(str(exc), 4)
    out.print(Panel(f"Investigation {inv.id}  [{inv.status.value}]", title="REA report"))
    for h in inv.hypotheses:
        out.print(f"  [{h.status.value}/{h.confidence.value}]  {h.claim}")
    if inv.system_model and inv.system_model.unresolved_areas:
        out.print("[bold]Unresolved[/bold]")
        for u in inv.system_model.unresolved_areas:
            out.print(f"  • {u}")


@app.command("validate")
def validate_cmd(investigation_id: str = typer.Argument(...)) -> None:
    """Run validation checks."""
    store = JsonInvestigationStore()
    try:
        inv = store.load(investigation_id)
    except InvestigationNotFoundError as exc:
        _exit_error(str(exc), 4)
    inv = validate_investigation(inv)
    store.save(inv)
    vr = inv.validation_report
    assert vr is not None
    out.print(Panel(f"matches={vr.match_count}  mismatches={vr.mismatch_count}", title="REA validate"))
    for f in vr.findings:
        mark = "yes" if f.matched else "no"
        out.print(f"  {f.test_name}: {mark} ({f.actual})")


@app.command("export")
def export_cmd(
    investigation_id: str = typer.Argument(...),
    format: str = typer.Option("json", "--format"),
    output: Optional[Path] = typer.Option(None, "--output", "-o"),
) -> None:
    """Export investigation as JSON."""
    if format != "json":
        _exit_error("only json supported in v0.1", 2)
    try:
        inv = JsonInvestigationStore().load(investigation_id)
    except InvestigationNotFoundError as exc:
        _exit_error(str(exc), 4)
    text = json.dumps(inv.model_dump(mode="json"), indent=2, default=str)
    if output:
        output.write_text(text, encoding="utf-8")
        out.print(f"Exported → {output}")
    else:
        sys.stdout.write(text + "\n")


@app.command("version")
def version_cmd() -> None:
    out.print(f"rea {__version__}")


if __name__ == "__main__":
    app()
