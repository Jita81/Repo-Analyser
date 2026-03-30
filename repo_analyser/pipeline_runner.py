"""
Run the Athena (Repo Analyser) LangGraph pipeline via the Olympus runtime.

Agent YAML and pipeline graph are bundled under ``repo_analyser/pipelines/athena/``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Bundled pipeline layout (package data)
_PACKAGE_DIR = Path(__file__).resolve().parent
_DEFAULT_PIPELINE = _PACKAGE_DIR / "pipelines" / "athena" / "athena-pipeline.yaml"
_DEFAULT_AGENTS = _PACKAGE_DIR / "pipelines" / "athena" / "agents"


def bundled_athena_paths() -> tuple[Path, Path]:
    """Return (pipeline_yaml, agents_dir) for the shipped Athena pipeline."""
    if not _DEFAULT_PIPELINE.is_file():
        raise FileNotFoundError(
            f"Bundled pipeline missing: {_DEFAULT_PIPELINE}. "
            "Reinstall repo-analyser or check package installation."
        )
    return _DEFAULT_PIPELINE, _DEFAULT_AGENTS


def run_athena_context_package(
    *,
    repo_path: Path,
    user_story: str,
    acceptance_criteria: list[str],
    model: str,
    db_path: Path | None,
    chroma_path: Path | None,
    embedding_model: str,
    index_repo: bool = True,
) -> tuple[Any, str]:
    """
    Execute the full eight-hero Athena pipeline + orchestrator.

    Returns (final_state_pydantic_model, run_id).
    """
    try:
        from olympus.athena_state import register_athena_schemas
        from olympus.iris_tools import register_iris
        from olympus.pipeline import run_pipeline
        from olympus.schema_registry import resolve_state_schema
    except ImportError as e:
        raise RuntimeError(
            "Olympus is required for `repo-analyser package`. Install with:\n"
            "  pip install 'repo-analyser[athena]'\n"
            "or install Olympus from source:\n"
            "  pip install -e path/to/Olympus-Agent-Framework/packages/olympus\n"
            f"Import error: {e}"
        ) from e

    pipeline_path, agents_dir = bundled_athena_paths()
    repo_path = repo_path.resolve()

    register_athena_schemas()
    register_iris()

    state_cls = resolve_state_schema("AthenaPipelineState")
    initial = state_cls(
        user_story=user_story,
        acceptance_criteria=acceptance_criteria,
        repo_path=str(repo_path),
    )

    return run_pipeline(
        pipeline_path=pipeline_path,
        agents_dir=agents_dir,
        initial_state=initial,
        model=model,
        db_path=db_path,
        register_demo=False,
        register_lethe=False,
        register_athena=True,
        register_iris=True,
        index_repo=index_repo,
        chroma_path=chroma_path,
        embedding_model=embedding_model,
    )


def write_context_package_markdown(final_state: Any, output_path: Path) -> Path:
    """Write a single Markdown file from orchestrator ContextPackage if present."""
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pkg = getattr(final_state, "context_package", None)
    if pkg is None:
        body = "# Context package\n\n_Orchestrator did not produce context_package._\n"
    else:
        lines = [
            f"# {pkg.title or 'Context package'}",
            "",
            "## Sections",
            "",
        ]
        for name, content in (pkg.sections or {}).items():
            lines.append(f"### {name}\n")
            lines.append(content or "")
            lines.append("")
        if pkg.metadata:
            lines.append("## Metadata\n")
            lines.append("```json")
            lines.append(json.dumps(pkg.metadata, indent=2))
            lines.append("```\n")
        body = "\n".join(lines)
    score = getattr(final_state, "package_score", None)
    if score is not None:
        body += f"\n---\n\n**Package score:** {score.overall} — {score.notes}\n"
    output_path.write_text(body, encoding="utf-8")
    return output_path
