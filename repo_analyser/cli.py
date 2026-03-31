"""
CLI entry point for Repo Analyser (Athena on Olympus).

Usage:
    repo-analyser package --repo ./path/to/repo --user-story "..."
    repo-analyser analyse --repo ./path/to/repo   # legacy five-document path
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from . import analysis, generation, ingestion

console = Console()


@click.group()
@click.version_option(version="0.2.0", prog_name="repo-analyser")
def main() -> None:
    """Repo Analyser: Athena eight-hero package on Olympus; optional static .context docs."""
    pass


@main.command("package")
@click.option(
    "--repo",
    required=True,
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    help="Repository root to index and analyse.",
)
@click.option(
    "--user-story",
    required=True,
    help="User story driving change-specific heroes (Daedalus → Arete).",
)
@click.option(
    "--acceptance",
    "acceptance_criteria",
    multiple=True,
    help="Acceptance criterion (repeat for multiple).",
)
@click.option(
    "--output",
    "output_md",
    default=None,
    type=click.Path(file_okay=True, dir_okay=False, path_type=Path),
    help=(
        "Write assembled context package Markdown "
        "(default: <repo>/.context/CONTEXT_PACKAGE.md)."
    ),
)
@click.option(
    "--db",
    "db_path",
    default=None,
    type=click.Path(file_okay=True, dir_okay=False, path_type=Path),
    help="Olympus run log SQLite (default: <repo>/.olympus/runs.sqlite).",
)
@click.option(
    "--chroma-path",
    default=None,
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    help="Chroma persistence directory (default: <repo>/.olympus/chroma_lethe).",
)
@click.option(
    "--embedding-model",
    default="all-MiniLM-L6-v2",
    help="sentence-transformers model for Lethe indexing.",
)
@click.option(
    "--model",
    default="claude-sonnet-4-20250514",
    help="Claude model id for all heroes.",
)
@click.option(
    "--no-index",
    is_flag=True,
    help="Skip Chroma build (tools need an existing index in chroma-path).",
)
def package_cmd(
    repo: Path,
    user_story: str,
    acceptance_criteria: tuple[str, ...],
    output_md: Path | None,
    db_path: Path | None,
    chroma_path: Path | None,
    embedding_model: str,
    model: str,
    no_index: bool,
) -> None:
    """
    Run the full Athena pipeline on Olympus (Lethe → … → Arete → Athena).

    Requires ``pip install 'repo-analyser[athena]'`` and a resolvable ``olympus`` package
    (PyPI or editable install from Olympus-Agent-Framework). Set ANTHROPIC_API_KEY for
    live Claude; without it, Olympus uses deterministic mocks for CI/local smoke tests.
    """
    from .pipeline_runner import run_athena_context_package, write_context_package_markdown

    repo = repo.resolve()
    ac = (
        list(acceptance_criteria)
        if acceptance_criteria
        else ["Implementation meets the user story."]
    )
    db = db_path or (repo / ".olympus" / "runs.sqlite")
    chroma = chroma_path or (repo / ".olympus" / "chroma_lethe")
    out = output_md or (repo / ".context" / "CONTEXT_PACKAGE.md")

    console.print(
        f"\n[bold]Repo Analyser[/bold] — [cyan]Athena package[/cyan] on Olympus\n"
        f"  Repo: {repo}\n"
    )

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            progress.add_task(
                "Running Athena pipeline (eight heroes + orchestrator)...",
                total=None,
            )
            final, run_id = run_athena_context_package(
                repo_path=repo,
                user_story=user_story,
                acceptance_criteria=ac,
                model=model,
                db_path=db,
                chroma_path=chroma,
                embedding_model=embedding_model,
                index_repo=not no_index,
            )
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Pipeline error:[/red] {e}")
        sys.exit(1)

    path = write_context_package_markdown(final, out)
    console.print(f"  ✓ [green]run_id[/green] {run_id}")
    console.print(f"  ✓ [green]Wrote[/green] {path}\n")
    dump = {
        "run_id": run_id,
        "package_score": (
            final.package_score.model_dump() if getattr(final, "package_score", None) else None
        ),
        "context_package_title": (
            final.context_package.title if getattr(final, "context_package", None) else None
        ),
    }
    console.print(json.dumps(dump, indent=2))
    console.print(
        f"\n[dim]Run log:[/dim] {db}  — use [cyan]olympus show-run {run_id} --db {db}[/cyan]\n"
    )


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
