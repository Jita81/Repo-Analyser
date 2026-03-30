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


def _md_block(title: str, body: str) -> str:
    b = (body or "").strip()
    if not b:
        return f"### {title}\n\n_(No content.)_\n"
    return f"### {title}\n\n{b}\n"


def _dump_json_block(data: Any) -> str:
    try:
        if hasattr(data, "model_dump"):
            data = data.model_dump()
        return "```json\n" + json.dumps(data, indent=2, default=str) + "\n```\n"
    except (TypeError, ValueError):
        return f"```\n{data!r}\n```\n"


def write_context_package_markdown(final_state: Any, output_path: Path) -> Path:
    """
    Write CONTEXT_PACKAGE.md: merge orchestrator sections with full pipeline state
    (Product Definition §5) so the file is useful even when Athena sections are thin.
    """
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    d = final_state.model_dump() if hasattr(final_state, "model_dump") else {}

    lines: list[str] = []
    pkg = d.get("context_package")
    title = "Context package"
    if isinstance(pkg, dict) and pkg.get("title"):
        title = str(pkg["title"])
    lines.append("# CONTEXT PACKAGE")
    lines.append("")
    lines.append(f"**{title}**")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 1. Executive summary")
    lines.append("")
    orch_exec = ""
    if isinstance(pkg, dict):
        sec = pkg.get("sections") or {}
        if isinstance(sec, dict):
            orch_exec = str(sec.get("executive_summary", "") or "")
    lines.append(
        orch_exec.strip()
        or _summary_from_meta(d)
        or "_(See hero outputs below.)_"
    )
    lines.append("")

    if isinstance(pkg, dict) and isinstance(pkg.get("metadata"), dict):
        lines.append("### Run metadata")
        lines.append(_dump_json_block(pkg["metadata"]))
        lines.append("")

    score = d.get("package_score")
    if isinstance(score, dict):
        lines.append(
            f"**Package score:** {score.get('overall', 'n/a')} — {score.get('notes', '')}\n"
        )

    lines.append("---")
    lines.append("")
    lines.append("## 2. Change boundary (Daedalus)")
    lines.append("")
    cb = d.get("change_boundary")
    rc = d.get("retrieved_code")
    lines.append(_md_block("Boundary", _format_change_boundary(cb)))
    lines.append(_md_block("Retrieved code focus", _format_retrieved_code(rc)))

    lines.append("---")
    lines.append("")
    lines.append("## 3. Standing context")
    lines.append("")
    idx = d.get("index_status")
    lines.append(_md_block("3.0 Index (Lethe)", _format_index_status(idx)))
    iris_block = _format_analytical_explanations(d.get("analytical_explanations"))
    lines.append(_md_block("3d Module map (Iris)", iris_block))
    pl = d.get("pattern_library")
    lines.append(_md_block("3a–c Patterns & conventions (Pallas)", _format_pattern_library(pl)))
    lines.append(_md_block("3e Gaps (Asclepius)", _format_gap_register(d.get("gap_register"))))

    lines.append("---")
    lines.append("")
    lines.append("## 4. Change-specific context")
    lines.append("")
    cc = d.get("change_classification")
    ast = d.get("assembled_standards")
    lines.append(_md_block("4b–d Classification & standards (Nike)", _format_nike(cc, ast)))

    lines.append("---")
    lines.append("")
    lines.append("## 5. Decomposition (Tyche)")
    lines.append("")
    lines.append(_md_block("Work items", _format_decomposition(d.get("decomposition"))))

    lines.append("---")
    lines.append("")
    lines.append("## 6. Testing contract (Arete)")
    lines.append("")
    lines.append(_md_block("Contracts", _format_testing_contracts(d.get("testing_contracts"))))

    lines.append("---")
    lines.append("")
    lines.append("## 7. Agent instructions (Athena orchestrator)")
    lines.append("")
    orch_instr = ""
    if isinstance(pkg, dict):
        sec = pkg.get("sections") or {}
        if isinstance(sec, dict):
            orch_instr = str(sec.get("agent_instructions", "") or "")
    lines.append(
        orch_instr.strip()
        or "_(Follow acceptance criteria and gap_register agent_instruction fields.)_"
    )
    lines.append("")

    if isinstance(pkg, dict):
        sec = pkg.get("sections") or {}
        if isinstance(sec, dict):
            skip = {"executive_summary", "agent_instructions"}
            extra = {k: v for k, v in sec.items() if k not in skip}
            if extra:
                lines.append("---")
                lines.append("")
                lines.append("## Orchestrator sections (full)")
                lines.append("")
                for k, v in extra.items():
                    lines.append(_md_block(k, str(v)))

    lines.append("---")
    lines.append("")
    lines.append("## Inputs")
    lines.append("")
    lines.append(f"- **User story:** {d.get('user_story', '')}")
    lines.append(f"- **Acceptance criteria:** {d.get('acceptance_criteria', [])}")
    lines.append(f"- **Repository:** `{d.get('repo_path', '')}`")
    lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def _summary_from_meta(d: dict[str, Any]) -> str:
    parts: list[str] = []
    if d.get("iris_score") is not None:
        parts.append(f"Iris score: {d.get('iris_score')}")
    if d.get("explanation_coverage") is not None:
        parts.append(f"Explanation coverage: {d.get('explanation_coverage')}")
    return ". ".join(parts) if parts else ""


def _format_index_status(idx: Any) -> str:
    if not idx:
        return ""
    if hasattr(idx, "model_dump"):
        idx = idx.model_dump()
    if not isinstance(idx, dict):
        return str(idx)
    return (
        f"Ready: {idx.get('ready')} | Chunks: {idx.get('indexed_chunks')} | "
        f"Merkle: `{str(idx.get('merkle_root', ''))[:16]}…` | {idx.get('note', '')}"
    )


def _format_analytical_explanations(ae: Any) -> str:
    if not ae:
        return ""
    if hasattr(ae, "model_dump"):
        ae = ae.model_dump()
    if not isinstance(ae, dict):
        return str(ae)
    cov = ae.get("coverage_pct", 0)
    em = ae.get("explained_modules")
    tm = ae.get("total_modules")
    lines = [
        f"Coverage: {cov}% ({em}/{tm} modules)",
        "",
    ]
    for ex in ae.get("explanations", [])[:50]:
        if not isinstance(ex, dict):
            continue
        mp = ex.get("module_path", "")
        lines.append(f"#### `{mp}`")
        lines.append(ex.get("explanation", ""))
        if ex.get("key_responsibilities"):
            lines.append("- " + "\n- ".join(str(r) for r in ex["key_responsibilities"][:7]))
        lines.append("")
    return "\n".join(lines).strip()


def _format_pattern_library(pl: Any) -> str:
    if not pl:
        return ""
    if hasattr(pl, "model_dump"):
        pl = pl.model_dump()
    if not isinstance(pl, dict):
        return str(pl)
    out = [str(pl.get("summary", "")), ""]
    for p in pl.get("patterns", [])[:40]:
        if isinstance(p, dict):
            out.append(f"- **{p.get('name', '?')}**: {p.get('description', '')}")
        else:
            out.append(f"- {p!r}")
    return "\n".join(out).strip()


def _format_gap_register(gr: Any) -> str:
    if not gr:
        return ""
    if hasattr(gr, "model_dump"):
        gr = gr.model_dump()
    if not isinstance(gr, dict):
        return str(gr)
    lines = [str(gr.get("summary", "")), f"Count: {gr.get('gap_count', 0)}", ""]
    for g in gr.get("gaps", [])[:50]:
        if isinstance(g, dict):
            lines.append(
                f"- **[{g.get('area', '')}]** ({g.get('severity', '')}): {g.get('detail', '')}\n"
                f"  - Agent: {g.get('agent_instruction', '')}"
            )
        else:
            lines.append(f"- {g!r}")
    return "\n".join(lines).strip()


def _format_change_boundary(cb: Any) -> str:
    if not cb:
        return ""
    if hasattr(cb, "model_dump"):
        cb = cb.model_dump()
    if not isinstance(cb, dict):
        return str(cb)
    files = cb.get("boundary_files") or []
    fl = ", ".join(f"`{f}`" for f in files[:40])
    return f"{cb.get('summary', '')}\n\nFiles: {fl}"


def _format_retrieved_code(rc: Any) -> str:
    if not rc:
        return ""
    if hasattr(rc, "model_dump"):
        rc = rc.model_dump()
    if not isinstance(rc, dict):
        return str(rc)
    paths = rc.get("paths") or []
    pl = ", ".join(f"`{p}`" for p in paths[:40])
    return f"{rc.get('summary', '')}\n\nPaths: {pl}"


def _format_nike(cc: Any, ast: Any) -> str:
    parts: list[str] = []
    if cc:
        if hasattr(cc, "model_dump"):
            cc = cc.model_dump()
        if isinstance(cc, dict):
            parts.append(f"**Type:** {cc.get('change_type', '')}\n\n{cc.get('rationale', '')}")
    if ast:
        if hasattr(ast, "model_dump"):
            ast = ast.model_dump()
        if isinstance(ast, dict):
            parts.append(f"**Standards summary:** {ast.get('summary', '')}")
            for s in (ast.get("standards") or [])[:60]:
                parts.append(f"- {s}")
    return "\n\n".join(parts).strip()


def _format_decomposition(dec: Any) -> str:
    if not dec:
        return ""
    if hasattr(dec, "model_dump"):
        dec = dec.model_dump()
    if not isinstance(dec, dict):
        return str(dec)
    lines = [str(dec.get("summary", "")), ""]
    for i, item in enumerate(dec.get("work_items") or [], 1):
        lines.append(f"{i}. {item}")
    return "\n".join(lines).strip()


def _format_testing_contracts(tc: Any) -> str:
    if not tc:
        return ""
    if hasattr(tc, "model_dump"):
        tc = tc.model_dump()
    if not isinstance(tc, dict):
        return str(tc)
    lines = [str(tc.get("summary", "")), ""]
    for c in tc.get("contracts") or []:
        lines.append(str(c))
        lines.append("")
    return "\n".join(lines).strip()
