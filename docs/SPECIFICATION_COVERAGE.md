# Specification coverage

Authoritative product and hero build PDFs live in [`specifications/`](./specifications/). This file records **implementation status** in this repository and the bundled Olympus framework (see `Olympus-Agent-Framework/` when present).

**Legend:** **Done** = matches the spec in spirit and core behaviour. **Partial** = implemented but missing named artefacts, fields, or behaviours from the PDF. **Gap** = not implemented as specified.

---

## Repo Analyser — Product Definition v4 (`repo-analyser-product-definition_2.pdf`)

| Area | Status | Notes |
|------|--------|--------|
| Eight heroes + Athena orchestrator | **Partial** | YAML + LangGraph order match; hero **data models** in code are slimmer than some build docs (e.g. Pallas `CodebaseKnowledge`). |
| Two-layer pipeline | **Done** | Standing → conditional → change-specific → assemble. |
| ~45k-token context package shape | **Partial** | `CONTEXT_PACKAGE.md` follows §5 outline and embeds full state; no enforced token budget. |
| Tuning Studio / MCP | **Gap** | Olympus has Studio pieces; not wired as end-to-end “product” in this repo. |

---

## Olympus Framework (`olympus_framework_.pdf`)

| Area | Status | Notes |
|------|--------|--------|
| Agent YAML, pipeline YAML → LangGraph | **Done** | Loader + `StateGraph`. |
| Tools, feed-forward state, scoring, retries | **Done** | `node_executor`, `scoring`, run log. |
| Claude + tool loop | **Done** | Anthropic path. |
| OpenAI-compatible local models | **Partial** | `OLYMPUS_OPENAI_COMPATIBLE` + `/v1/chat/completions`; quality depends on model. |
| Tuning Studio API (full §5) | **Partial** | FastAPI exists in Olympus package; feature parity not audited here. |

---

## Lethe (`lethe-build-document.pdf`)

| Area | Status | Notes |
|------|--------|--------|
| AST-oriented chunking (Chonkie + tree-sitter) | **Done** | `indexing.build_index`. |
| Chroma + sentence-transformers | **Done** | Local embeddings. |
| Merkle skip / rebuild | **Partial** | Merkle on **collection metadata**; spec’s **per-file** Merkle + `lethe_merkle.json` + incremental **per-file** re-index not implemented. |
| Collection name `olympus_lethe` | **Gap** | Runtime uses **per-run** collection name (e.g. `lethe_<runprefix>`), not fixed `olympus_lethe`. |
| Chunk metadata schema (chunk_type, chunk_name, file_hash, indexed_at) | **Partial** | Has `path`/`file_path`, `chunk_id`, lines, `language`; missing several spec fields. |
| IndexStatus language breakdown / changed_files / needs_iris_refresh | **Gap** | Current `IndexStatus` is a smaller shape. |

---

## Iris (`iris-build-document.pdf`)

| Area | Status | Notes |
|------|--------|--------|
| Tools: get_module_list, get_module_chunks, write_explanation | **Done** | `iris_tools.py`; Chroma filter in-process (not `$contains` wire format). |
| `.olympus/iris_explanations.json` | **Done** | Persisted. |
| Chroma enrichment metadata on chunks | **Done** | `iris_explanation`, etc. |
| register_iris / CLI flag | **Done** | |
| Collection name `olympus_lethe` | **Gap** | Same as Lethe — must match active collection. |

---

## Pallas (`pallas-build-document.pdf`)

| Area | Status | Notes |
|------|--------|--------|
| Role + YAML + tools | **Partial** | Agent uses `pattern_library` in state, not spec’s **`CodebaseKnowledge`** / `convention_count` / `pattern_count`. |
| `.olympus/pallas_knowledge.json` | **Gap** | Not written. |
| Chroma pattern tags on chunks | **Gap** | Not implemented. |
| Structured Convention / ArchitecturalDecision models | **Gap** | Uses generic `PatternLibrary` dicts. |

---

## Asclepius (`asclepius-build-document.pdf`)

| Area | Status | Notes |
|------|--------|--------|
| Tools read_file, read_explanation, write_gap, read_gaps | **Done** | |
| Typed gap register in state | **Partial** | `GapRegister` exists; session **`write_gap`** merge helps; spec may require richer gap schema. |
| Chroma violation queries | **Gap** | Not implemented as in doc. |

---

## Daedalus (`daedalus-build-document.pdf`)

| Area | Status | Notes |
|------|--------|--------|
| Tools + boundary / retrieved_code outputs | **Partial** | State fields exist; **verbatim code with line numbers** in `retrieved_code` relies on model + `read_file`; no dedicated `change_type_hypothesis` field. |
| Structured ChangeBoundary per spec (primary/secondary modules) | **Partial** | Flat `boundary_files` / summaries vs full spec model. |

---

## Nike (`nike-build-document.pdf`)

| Area | Status | Notes |
|------|--------|--------|
| classify_change_type + get_standard tools | **Done** | `nike_standards.py` knowledge base + keyword taxonomy. |
| ISO families “all characteristics evaluated” | **Partial** | Curated bullets by change type, not full 8× matrix per run. |
| `codebase_knowledge` from Pallas | **Gap** | State uses `pattern_library`, not spec model. |
| `testing_templates` for Arete | **Gap** | Not separate state field. |
| File-specific standards per boundary file | **Partial** | Prompt asks for applied standards; no structured per-file map in state. |

---

## Tyche (`tyche-build-document.pdf`)

| Area | Status | Notes |
|------|--------|--------|
| Decomposition + tools | **Partial** | `Decomposition.work_items`; spec may require dependencies / risk flags as structured fields. |

---

## Arete (`arete-build-document.pdf`)

| Area | Status | Notes |
|------|--------|--------|
| Testing contracts output | **Partial** | `TestingContracts.contracts` as strings; spec may require richer contract objects. |

---

## Legacy five-document CLI (`README.pdf`, `cli.pdf`, `models.pdf`, `analysis.pdf`, `ingestion.pdf`, `generation.pdf`)

| Area | Status | Notes |
|------|--------|--------|
| Ingestion → analysis → five Markdown files | **Done** | `repo_analyser analyse` |

---

## Conclusion

**These PDFs are now versioned in-repo under `docs/specifications/`.**

**They are not all delivered “in full” at the build-document level:** several heroes (especially **Lethe** collection naming and incremental Merkle file, **Pallas** knowledge model and persistence, **Nike** full standards matrix and `testing_templates`, parts of **Daedalus** / **Arete** structure) still differ from the PDFs. The **product definition** pipeline and **Olympus runtime** are largely in place; remaining work is tightening **schemas, persistence, and index semantics** to match each build document line-by-line.
