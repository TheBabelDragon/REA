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
    IntakeError,
    InvestigationNotFoundError,
    REAError,
    SafetyBoundaryError,
    UnsupportedArtifactError,
)
from rea.core.store import JsonInvestigationStore
from rea.intake.registry import register_artifact
from rea.pipeline import run_full_pipeline
from rea.validation.reporter import validate_investigation

app = typer.Typer(
    name="rea",
    help="REA — Reverse Engineer Anything. Evidence-driven reverse-engineering framework.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console(stderr=True)
out = Console()


def _exit_error(msg: str, code: int = 1) -> None:
    console.print(f"[red]error:[/red] {msg}")
    raise typer.Exit(code)


@app.callback()
def main_callback() -> None:
    """REA v0.1 — modular, evidence-driven reverse engineering."""


@app.command("inspect")
def inspect_cmd(
    path: Path = typer.Argument(..., help="Path to artifact (file or directory)"),
) -> None:
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
    table.add_row("acquired", str(artifact.acquisition_timestamp))
    out.print(table)

    capable = adapters_for(artifact)
    out.print("\n[bold]Supported capabilities for this artifact:[/bold]")
    if not capable:
        out.print("  [yellow]None — artifact kind is not supported by available adapters.[/yellow]")
        out.print("  Available adapters support: source_code, text, directory.")
    else:
        for a in capable:
            for c in a.capabilities():
                out.print(f"  • {c.name} ({c.id})")
                for lim in c.limitations:
                    out.print(f"      limitation: {lim}")

    out.print("\n[bold]All registered capabilities:[/bold]")
    for c in all_capabilities():
        out.print(f"  • {c['name']} — kinds: {', '.join(c['supported_kinds'])}")


@app.command("analyze")
def analyze_cmd(
    path: Path = typer.Argument(..., help="Path to artifact"),
) -> None:
    """Collect structural observations using available adapters."""
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
        if "preview" in obs.payload:
            payload["preview"] = "(truncated)"
        out.print(json.dumps(payload, indent=2, default=str)[:800])


@app.command("investigate")
def investigate_cmd(
    path: Path = typer.Argument(..., help="Path to artifact"),
    notes: Optional[str] = typer.Option(None, "--notes", help="Optional notes"),
) -> None:
    """Execute the complete supported investigation pipeline."""
    try:
        inv = run_full_pipeline(path, notes=notes)
    except UnsupportedArtifactError as exc:
        _exit_error(str(exc), 3)
    except REAError as exc:
        _exit_error(str(exc), 1)

    out.print(
        Panel(
            f"[bold]Investigation[/bold] {inv.id}\n"
            f"Status: {inv.status.value}\n"
            f"Artifacts: {len(inv.artifacts)}  "
            f"Observations: {len(inv.observations)}  "
            f"Evidence: {len(inv.evidence)}  "
            f"Hypotheses: {len(inv.hypotheses)}",
            title="REA investigate",
        )
    )
    out.print(f"\nSaved to local store. Use: [bold]rea report {inv.id}[/bold]")


@app.command("report")
def report_cmd(
    investigation_id: str = typer.Argument(..., help="Investigation ID"),
) -> None:
    """Display findings, evidence, hypotheses, confidence, and unresolved questions."""
    store = JsonInvestigationStore()
    try:
        inv = store.load(investigation_id)
    except InvestigationNotFoundError as exc:
        _exit_error(str(exc), 4)

    out.print(Panel(f"Investigation {inv.id}  [{inv.status.value}]", title="REA report"))

    out.print("\n[bold]Artifacts[/bold]")
    for a in inv.artifacts:
        out.print(f"  {a.id}  kind={a.kind.value}  origin={a.origin}")

    out.print(f"\n[bold]Observations[/bold] ({len(inv.observations)})")
    for o in inv.observations[:15]:
        out.print(f"  {o.id}  {o.observation_type.value}")
    if len(inv.observations) > 15:
        out.print(f"  … and {len(inv.observations) - 15} more")

    out.print(f"\n[bold]Evidence[/bold] ({len(inv.evidence)})")
    for e in inv.evidence[:10]:
        out.print(f"  {e.id}  [{e.relation.value}]  {e.summary[:80]}")

    out.print(f"\n[bold]Hypotheses[/bold] ({len(inv.hypotheses)})")
    for h in inv.hypotheses:
        out.print(f"  {h.id}  [{h.status.value}/{h.confidence.value}]  {h.claim}")
        for u in h.unresolved_assumptions:
            out.print(f"      assumption: {u}")

    if inv.system_model:
        sm = inv.system_model
        out.print(
            f"\n[bold]System model[/bold]  components={len(sm.components)}  "
            f"interfaces={len(sm.interfaces)}"
        )
        if sm.unresolved_areas:
            out.print("[bold]Unresolved[/bold]")
            for u in sm.unresolved_areas:
                out.print(f"  • {u}")

    if inv.validation_report:
        vr = inv.validation_report
        out.print(
            f"\n[bold]Validation[/bold]  matches={vr.match_count}  "
            f"mismatches={vr.mismatch_count}"
        )


@app.command("validate")
def validate_cmd(
    investigation_id: str = typer.Argument(..., help="Investigation ID"),
) -> None:
    """Run available reconstruction checks and generate a validation report."""
    store = JsonInvestigationStore()
    try:
        inv = store.load(investigation_id)
    except InvestigationNotFoundError as exc:
        _exit_error(str(exc), 4)

    inv = validate_investigation(inv)
    store.save(inv)

    vr = inv.validation_report
    assert vr is not None
    out.print(Panel(f"Validation report {vr.id}", title="REA validate"))
    table = Table(show_header=True, header_style="bold")
    table.add_column("Test")
    table.add_column("Matched")
    table.add_column("Expected")
    table.add_column("Actual")
    for f in vr.findings:
        matched = "[green]yes[/green]" if f.matched else "[red]no[/red]"
        table.add_row(f.test_name, matched, f.expected, f.actual)
    out.print(table)
    out.print(f"\nMatches: {vr.match_count}  Mismatches: {vr.mismatch_count}")
    if vr.limitations:
        out.print("\n[bold]Limitations[/bold]")
        for lim in vr.limitations:
            out.print(f"  • {lim}")


@app.command("export")
def export_cmd(
    investigation_id: str = typer.Argument(..., help="Investigation ID"),
    format: str = typer.Option("json", "--format", help="Export format (json)"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file"),
) -> None:
    """Export a versioned, portable investigation record."""
    if format != "json":
        _exit_error(f"unsupported format: {format} (only json in v0.1)", 2)

    store = JsonInvestigationStore()
    try:
        inv = store.load(investigation_id)
    except InvestigationNotFoundError as exc:
        _exit_error(str(exc), 4)

    data = inv.model_dump(mode="json")
    text = json.dumps(data, indent=2, default=str)

    if output:
        output.write_text(text, encoding="utf-8")
        out.print(f"Exported {investigation_id} → {output}")
    else:
        sys.stdout.write(text)
        sys.stdout.write("\n")


@app.command("version")
def version_cmd() -> None:
    """Print REA version."""
    out.print(f"rea {__version__}")


if __name__ == "__main__":
    app()
