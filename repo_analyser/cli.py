"""
CLI entry point for Repo Analyser.

Usage:
    repo-analyser analyse --repo ./path/to/repo
    repo-analyser analyse --repo ./path/to/repo --output ./custom-output-dir
    repo-analyser analyse --repo ./path/to/repo --api-key sk-ant-...
"""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from . import analysis, generation, ingestion

console = Console()


@click.group()
@click.version_option(version="0.1.0", prog_name="repo-analyser")
def main() -> None:
    """Repo Analyser — generate structured context documents for AI-assisted coding."""
    pass


@main.command()
@click.option(
    "--repo",
    required=True,
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    help="Path to the repository to analyse.",
)
@click.option(
    "--output",
    default=None,
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    help="Output directory for context documents. Defaults to <repo>/.context",
)
@click.option(
    "--api-key",
    default=None,
    envvar="ANTHROPIC_API_KEY",
    help="Anthropic API key. Falls back to ANTHROPIC_API_KEY environment variable.",
)
def analyse(repo: Path, output: Path | None, api_key: str | None) -> None:
    """
    Analyse a repository and generate context documents.

    Reads the repository, sends a structured snapshot to Claude for analysis,
    and writes five context documents to the output directory.
    """
    repo = repo.resolve()
    output_dir = output.resolve() if output else repo / ".context"
    console.print(f"\n[bold]Repo Analyser[/bold] — analysing [cyan]{repo.name}[/cyan]\n")

    # -----------------------------------------------------------------------
    # Step 1: Ingestion
    # -----------------------------------------------------------------------
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Reading repository...", total=None)
        try:
            snapshot = ingestion.ingest(repo)
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)
        progress.update(task, completed=True)

    console.print(
        f"  ✓ [green]Ingested[/green] {snapshot.total_file_count} files "
        f"({snapshot.sampled_file_count} sampled) | "
        f"Language: [cyan]{snapshot.primary_language or 'unknown'}[/cyan] | "
        f"Frameworks: [cyan]{', '.join(snapshot.detected_frameworks) or 'none detected'}[/cyan]"
    )

    # -----------------------------------------------------------------------
    # Step 2: Analysis
    # -----------------------------------------------------------------------
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Analysing with Claude (this takes 30–60 seconds)...", total=None)
        try:
            result = analysis.analyse(snapshot, api_key=api_key)
        except ValueError as e:
            console.print(f"[red]Parse error:[/red] {e}")
            sys.exit(1)
        except Exception as e:
            console.print(f"[red]API error:[/red] {e}")
            sys.exit(1)
        progress.update(task, completed=True)

    confidence_colour = {"high": "green", "medium": "yellow", "low": "red"}.get(
        result.analysis_confidence, "yellow"
    )
    console.print(
        f"  ✓ [green]Analysed[/green] — "
        f"{len(result.patterns)} patterns | "
        f"{len(result.gaps)} gaps | "
        f"Confidence: [{confidence_colour}]{result.analysis_confidence}[/{confidence_colour}]"
    )

    # -----------------------------------------------------------------------
    # Step 3: Generation
    # -----------------------------------------------------------------------
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Generating context documents...", total=None)
        doc_set = generation.generate(result)
        written_paths = doc_set.write(output_dir)
        progress.update(task, completed=True)

    console.print(f"  ✓ [green]Generated[/green] {len(written_paths)} context documents\n")

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    table = Table(title="Context Documents", show_header=True, header_style="bold")
    table.add_column("File", style="cyan")
    table.add_column("Purpose")
    table.add_column("Path", style="dim")
    purposes = {
        "AGENT_BRIEF.md": "Entry point — read this first",
        "ARCHITECTURE.md": "System structure (ISO 42010)",
        "PATTERNS.md": "Coding patterns with examples",
        "STANDARDS.md": "Quality standards (ISO 25010)",
        "GAPS.md": "Known gaps & agent instructions",
    }
    for path in written_paths:
        table.add_row(path.name, purposes.get(path.name, ""), str(path))

    console.print(table)
    if result.analysis_notes:
        console.print(f"\n[yellow]Note:[/yellow] {result.analysis_notes}")
    high_gaps = [g for g in result.gaps if g.severity == "high"]
    if high_gaps:
        console.print(
            f"\n[red]  {len(high_gaps)} high-severity gap(s) detected.[/red] "
            f"Review [cyan]GAPS.md[/cyan] before using these documents with an agent."
        )
    console.print(
        f"\n[bold green]Done.[/bold green] "
        f"Point your agent at [cyan]{output_dir / 'AGENT_BRIEF.md'}[/cyan] to get started.\n"
    )
