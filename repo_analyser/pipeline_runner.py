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
    ck = d.get("codebase_knowledge")
    pallas_body = _format_codebase_knowledge(ck)
    if not pallas_body.strip():
        pallas_body = _format_pattern_library(d.get("pattern_library"))
    lines.append(_md_block("3a–c Patterns & conventions (Pallas)", pallas_body))
    lines.append(_md_block("3e Gaps (Asclepius)", _format_gap_register(d.get("gap_register"))))

    lines.append("---")
    lines.append("")
    lines.append("## 4. Change-specific context")
    lines.append("")
    cc = d.get("change_classification")
    ast = d.get("assembled_standards")
    tt = d.get("testing_templates")
    nike_body = _format_nike(cc, ast)
    if tt:
        nike_body += "\n\n**Testing templates (Nike → Arete):**\n"
        for t in (tt if isinstance(tt, list) else [])[:20]:
            if isinstance(t, dict):
                g, w, th = t.get("given", ""), t.get("when", ""), t.get("then", "")
                nike_body += f"- Given: {g} / When: {w} / Then: {th}\n"
    lines.append(_md_block("4b–d Classification & standards (Nike)", nike_body))

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
    lb = idx.get("language_breakdown") or {}
    lb_s = ", ".join(f"{k}: {v}" for k, v in list(lb.items())[:12]) if lb else ""
    changed = idx.get("changed_files") or []
    iris_q = idx.get("needs_iris_refresh") or []
    parts = [
        f"Ready: {idx.get('ready')} | Chunks: {idx.get('indexed_chunks')} | "
        f"Collection: `{idx.get('collection_name', '')}` | "
        f"Merkle: `{str(idx.get('merkle_root', ''))[:16]}…`",
    ]
    if lb_s:
        parts.append(f"Languages: {lb_s}")
    if changed:
        parts.append(f"Changed files this run: {', '.join(str(x) for x in changed[:20])}")
    if iris_q:
        parts.append(f"needs_iris_refresh: {', '.join(str(x) for x in iris_q[:15])}")
    if idx.get("note"):
        parts.append(str(idx["note"]))
    return "\n".join(parts)


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


def _format_codebase_knowledge(ck: Any) -> str:
    if not ck:
        return ""
    if hasattr(ck, "model_dump"):
        ck = ck.model_dump()
    if not isinstance(ck, dict):
        return str(ck)
    lines = [str(ck.get("summary", "")), ""]
    for c in ck.get("conventions", [])[:30]:
        if isinstance(c, dict):
            nm, cat, desc = c.get("name", ""), c.get("category", ""), c.get("description", "")
            lines.append(f"- **{nm}** ({cat}): {desc}")
        else:
            lines.append(f"- {c!r}")
    lines.append("")
    for p in ck.get("patterns", [])[:30]:
        if isinstance(p, dict):
            lines.append(f"- **{p.get('name', '')}**: {p.get('description', '')}")
        else:
            lines.append(f"- {p!r}")
    lines.append("")
    for ad in ck.get("architectural_decisions", [])[:20]:
        if isinstance(ad, dict):
            lines.append(f"- **{ad.get('title', '')}**: {ad.get('description', '')}")
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
            cat = g.get("category", "")
            lines.append(
                f"- **[{g.get('area', '')}]** ({g.get('severity', '')})"
                f"{f' [{cat}]' if cat else ''}: {g.get('detail', '')}\n"
                f"  - Agent: {g.get('agent_instruction', '')}"
            )
        else:
            gd = g.model_dump() if hasattr(g, "model_dump") else {}
            if gd:
                a, sev, det = gd.get("area", ""), gd.get("severity", ""), gd.get("detail", "")
                ai = gd.get("agent_instruction", "")
                lines.append(f"- **[{a}]** ({sev}): {det}\n  - Agent: {ai}")
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
    prim = ", ".join(f"`{x}`" for x in (cb.get("primary_modules") or [])[:20])
    sec = ", ".join(f"`{x}`" for x in (cb.get("secondary_modules") or [])[:20])
    hyp = cb.get("change_type_hypothesis", "")
    oos = cb.get("out_of_scope", "")
    lines = [str(cb.get("summary", "")), "", f"**Files:** {fl}"]
    if prim:
        lines.append(f"**Primary:** {prim}")
    if sec:
        lines.append(f"**Secondary:** {sec}")
    if hyp:
        lines.append(f"**Change hypothesis:** {hyp}")
    if oos:
        lines.append(f"**Out of scope:** {oos}")
    return "\n".join(lines)


def _format_retrieved_code(rc: Any) -> str:
    if not rc:
        return ""
    if hasattr(rc, "model_dump"):
        rc = rc.model_dump()
    if not isinstance(rc, dict):
        return str(rc)
    paths = rc.get("paths") or []
    pl = ", ".join(f"`{p}`" for p in paths[:40])
    lines = [str(rc.get("summary", "")), "", f"Paths: {pl}"]
    for sn in (rc.get("snippets") or [])[:15]:
        if isinstance(sn, dict):
            lines.append(
                f"\n```{sn.get('path', '')} "
                f"L{sn.get('start_line', '')}-{sn.get('end_line', '')}\n"
                f"{sn.get('content', '')[:2000]}\n```"
            )
    return "\n".join(lines)


def _format_nike(cc: Any, ast: Any) -> str:
    parts: list[str] = []
    if cc:
        if hasattr(cc, "model_dump"):
            cc = cc.model_dump()
        if isinstance(cc, dict):
            at = cc.get("all_types") or []
            at_s = ", ".join(str(x) for x in at) if at else ""
            parts.append(
                f"**Type:** {cc.get('change_type', '')}"
                f"{f' (all: {at_s})' if at_s else ''}\n\n{cc.get('rationale', '')}"
            )
    if ast:
        if hasattr(ast, "model_dump"):
            ast = ast.model_dump()
        if isinstance(ast, dict):
            parts.append(f"**Standards summary:** {ast.get('summary', '')}")
            for s in (ast.get("standards") or [])[:60]:
                parts.append(f"- {s}")
            iso = ast.get("iso25010_notes") or {}
            if isinstance(iso, dict) and iso:
                parts.append("\n**ISO 25010 (applied):**")
                for k, v in list(iso.items())[:12]:
                    parts.append(f"- {k}: {v}")
            fg = ast.get("file_guidance") or []
            if fg:
                parts.append("\n**Per-file guidance:**")
                for item in fg[:25]:
                    if isinstance(item, dict):
                        instr = "; ".join(item.get("instructions") or [])
                        parts.append(f"- `{item.get('path', '')}`: {instr}")
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
    for comp in (dec.get("components") or [])[:20]:
        if isinstance(comp, dict):
            deps = ", ".join(comp.get("depends_on") or [])
            lines.append(
                f"- **{comp.get('title', '')}** (risk: {comp.get('risk', '')})"
                f"{f' deps: {deps}' if deps else ''}\n  {comp.get('description', '')}"
            )
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
    for sc in (tc.get("structured_contracts") or [])[:15]:
        if isinstance(sc, dict):
            lines.append(f"### {sc.get('component', 'component')}")
            if sc.get("preconditions"):
                lines.append("**Pre:** " + "; ".join(sc["preconditions"][:8]))
            if sc.get("postconditions"):
                lines.append("**Post:** " + "; ".join(sc["postconditions"][:8]))
            for s in (sc.get("scenarios") or [])[:6]:
                if isinstance(s, dict):
                    sg, sw, st = s.get("given", ""), s.get("when", ""), s.get("then", "")
                    lines.append(f"- G: {sg} | W: {sw} | T: {st}")
            lines.append("")
    return "\n".join(lines).strip()
