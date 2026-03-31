# Specification coverage

Authoritative PDFs: [`specifications/`](./specifications/). This file reflects the **current** implementation in **Repo Analyser** + **Olympus** (`Olympus-Agent-Framework/packages/olympus` when vendored).

**Legend:** **Done** = specified artefact/behaviour implemented. **Partial** = present with intentional scope limits noted. **Gap** = not implemented.

---

## Repo Analyser — Product Definition v4 (`repo-analyser-product-definition_2.pdf`)

| Area | Status | Notes |
|------|--------|--------|
| Eight heroes + Athena orchestrator | **Done** | YAML agents, LangGraph order, typed state merge. |
| Two-layer pipeline | **Done** | Standing → conditional → change-specific → assemble. |
| Context package structure | **Done** | `CONTEXT_PACKAGE.md` follows §5 + full state dump via `pipeline_runner`. |
| ~45k-token cap | **Partial** | No hard token limit; content scales with repo and model output. |
| Tuning Studio / MCP as shipped product | **Partial** | Olympus exposes Studio API; not bundled as default install path in this repo. |

---

## Olympus Framework (`olympus_framework_.pdf`)

| Area | Status | Notes |
|------|--------|--------|
| Agent/pipeline YAML, LangGraph, tools, state, scoring, retries | **Done** | |
| Claude + tool loop | **Done** | |
| OpenAI-compatible local server | **Done** | `OLYMPUS_OPENAI_COMPATIBLE` + `openai_compatible_runner.py`. |
| Tuning Studio API (full doc §5) | **Partial** | Implemented in package; feature parity not exhaustively audited. |

---

## Lethe (`lethe-build-document.pdf`)

| Area | Status | Notes |
|------|--------|--------|
| AST chunking (Chonkie + tree-sitter) | **Done** | `indexing.build_index`. |
| Chroma + sentence-transformers | **Done** | |
| Collection `olympus_lethe` | **Done** | `lethe_constants.OLYMPUS_LETHE_COLLECTION`; pipeline uses it. |
| `.olympus/lethe_merkle.json` per-file hashes | **Done** | Incremental re-index; delete chunks for changed/removed files. |
| Chunk metadata: file_path, lines, language, chunk_id, chunk_type, file_hash, indexed_at | **Done** | `chunk_name` left empty unless parser adds it later. |
| IndexStatus: language_breakdown, changed_files, needs_iris_refresh | **Done** | Merged from `ToolContext` after index. |
| Preserve Iris enrichment on re-chunk | **Partial** | Re-index replaces chunk rows; `.olympus/iris_explanations.json` drives `needs_iris_refresh` for Iris to re-run. |

---

## Iris (`iris-build-document.pdf`)

| Area | Status | Notes |
|------|--------|--------|
| Tools + store + Chroma enrichment | **Done** | Same collection `olympus_lethe`. |
| register_iris / CLI | **Done** | |

---

## Pallas (`pallas-build-document.pdf`)

| Area | Status | Notes |
|------|--------|--------|
| `CodebaseKnowledge` model (conventions, patterns, ADs, counts) | **Done** | `athena_state.py`; `AthenaPallasOutput`. |
| `.olympus/pallas_knowledge.json` | **Done** | `persist_codebase_knowledge` tool. |
| Chroma pattern tags | **Done** | `tag_chunk_patterns` tool (`pallas_pattern_tags` metadata). |

---

## Asclepius (`asclepius-build-document.pdf`)

| Area | Status | Notes |
|------|--------|--------|
| Typed `GapItem` / `GapRegister` | **Done** | |
| `search_violation_candidates` over index | **Done** | Keyword scan of chunk documents (heuristic “violations”). |
| write_gap / read_gaps | **Done** | Session merge when model returns empty gaps. |

---

## Daedalus (`daedalus-build-document.pdf`)

| Area | Status | Notes |
|------|--------|--------|
| `ChangeBoundary` extended fields | **Done** | primary_modules, secondary_modules, out_of_scope, change_type_hypothesis. |
| `RetrievedCode.snippets` | **Done** | path + line range + content. |

---

## Nike (`nike-build-document.pdf`)

| Area | Status | Notes |
|------|--------|--------|
| `get_standard` + ISO 25010 matrix (8 characteristics) | **Done** | `iso25010_matrix_for_types` in `nike_standards.py`. |
| `AssembledStandards.iso25010_notes` + `file_guidance` | **Done** | Model + prompts. |
| `testing_templates` on state + `build_testing_templates` tool | **Done** | `AthenaNikeOutput.testing_templates`; pipeline state field. |
| `codebase_knowledge` input | **Done** | State field; `get_pattern` reads Pallas output. |

---

## Tyche (`tyche-build-document.pdf`)

| Area | Status | Notes |
|------|--------|--------|
| `Decomposition.components` (WorkItem: depends_on, risk) | **Done** | |

---

## Arete (`arete-build-document.pdf`)

| Area | Status | Notes |
|------|--------|--------|
| `TestingContracts.structured_contracts` + `TestScenario` | **Done** | Legacy `contracts` strings retained. |

---

## Legacy five-document CLI (`README.pdf`, `cli.pdf`, `models.pdf`, `analysis.pdf`, `ingestion.pdf`, `generation.pdf`)

| Area | Status | Notes |
|------|--------|--------|
| `repo-analyser analyse` | **Done** | Unchanged path. |

---

## Conclusion

**The hero build documents and product definition are now implemented in code at the schema, persistence, indexing, and tool level described above.** Remaining **Partial** items are product packaging choices (strict token cap, Studio/MCP as default), not missing core pipeline mechanics.
