# Repo Analyser

**Repo Analyser** is the first product on the **[Olympus](https://github.com/Jita81/Olympus-Agent-Framework) Agent Framework**: **Athena’s pipeline** — eight YAML-configured heroes plus an orchestrator — producing a **~45,000-token context package** from a **repository** and a **user story** with acceptance criteria (see *Repo Analyser Product Definition*, Automated Agile).

It is not a generic documentation generator: it is the automated equivalent of a senior **Context Engineer** briefing a coding agent before implementation.

## Architecture (two layers)

| Layer | Heroes | Role |
|-------|--------|------|
| **Standing Knowledge** | Lethe → Iris → Pallas → Asclepius | Index + semantic explanations + patterns/conventions + gap register (rebuild when the repo changes). |
| **Change-specific** | Daedalus → Nike → Tyche → Arete | Boundary + verbatim code + standards + decomposition + testing contracts (per user story). |
| **Assembly** | Athena (orchestrator) | Merges state into one structured package; scores the result. |

Every hero is an Olympus agent: **YAML** (`role`, `system_prompt`, `tools`, `input_schema` / `output_schema`, `scoring`). The runtime handles Claude, tools, **typed feed-forward state** (`AthenaPipelineState`), logging, and retries.

Bundled definitions live under `repo_analyser/pipelines/athena/`:

- `athena-pipeline.yaml` — LangGraph graph  
- `agents/*.yaml` — Lethe, Iris, Pallas, Asclepius, Daedalus, Nike, Tyche, Arete, Athena  

## Installation

**Python 3.11+**

```bash
pip install -e .
```

### Full Athena pipeline (recommended)

Requires the **`olympus`** package (LangGraph, Chroma, Lethe/Iris tools, etc.):

```bash
# If olympus is not yet on your index, install from the Olympus repo:
pip install -e path/to/Olympus-Agent-Framework/packages/olympus

pip install -e ".[athena]"
```

Or with extras in one line when `olympus` is published:

```bash
pip install "repo-analyser[athena]"
```

## Usage

### Primary: context package (`package`)

Runs the **full eight heroes + Athena** and writes **`CONTEXT_PACKAGE.md`** (default: `<repo>/.context/CONTEXT_PACKAGE.md`). The file follows the **product outline** (executive summary, boundary, standing context with index + Iris + Pallas + gaps, change-specific, decomposition, testing contract, agent instructions) and **embeds full hero state** so the package is complete even if the orchestrator’s sections are brief.

Run log: `<repo>/.olympus/runs.sqlite`.

**Olympus runtime:** install **`olympus`** from the [Olympus-Agent-Framework](https://github.com/Jita81/Olympus-Agent-Framework) tree (editable install) so Daedalus/Nike/Tyche get **state-aware** tools: `read_explanation`, `get_module_map`, `get_pattern` read **current pipeline state** (and `.olympus/iris_explanations.json`). Nike’s **`get_standard`** / **`classify_change_type`** use an **applied standards knowledge base**. Asclepius **`write_gap`** merges into **`gap_register`** when the model returns an empty gap list.

```bash
export ANTHROPIC_API_KEY=sk-ant-...

repo-analyser package \
  --repo ./path/to/repo \
  --user-story "Add validation to the checkout API" \
  --acceptance "Invalid payloads return 400" \
  --acceptance "Valid payloads persist to the database"
```

Options:

- `--output` — path to the Markdown file  
- `--db` — SQLite run log path  
- `--chroma-path` — Chroma persistence (default `<repo>/.olympus/chroma_lethe`)  
- `--no-index` — skip index build (only if the index already exists)  
- `--model` — Claude model id  

Inspect runs with the Olympus CLI:

```bash
olympus show-run <run_id> --db ./path/to/repo/.olympus/runs.sqlite
```

Without `ANTHROPIC_API_KEY`, Olympus uses **deterministic mocks** (useful for smoke tests; not for real packages).

### Self-hosted models (Ollama / OpenAI-compatible)

Olympus can drive the same YAML agents via a **local** `/v1/chat/completions` server (e.g. [Ollama](https://ollama.com)):

```bash
export OLYMPUS_OPENAI_COMPATIBLE=1
export OPENAI_BASE_URL=http://127.0.0.1:11434/v1
export OLYMPUS_MODEL=llama3.2   # or another instruct-capable model
# Leave ANTHROPIC_API_KEY unset so this path is used
repo-analyser package --repo . --user-story "..." --acceptance "..."
```

Use a model strong enough to emit **valid JSON** for each hero’s `output_schema`. Lethe’s **`read_file`** / **`get_git_history`** work from **`repo_path`** in state; **`search_index`** still needs indexing (`--index-repo` / default) for Chroma.

### Legacy: five static context documents (`analyse`)

Single-shot **ingestion → one Claude analysis → five Markdown files** (ISO 25010 / ISO 42010 shaped), no LangGraph:

```bash
repo-analyser analyse --repo ./path/to/repo
```

Output: `<repo>/.context/` → `AGENT_BRIEF.md`, `ARCHITECTURE.md`, `PATTERNS.md`, `STANDARDS.md`, `GAPS.md`.

## Product vs legacy

| Path | Output | When to use |
|------|--------|-------------|
| **`package`** | Orchestrated sections (~45k token target), per-hero traceability in run log | Production Repo Analyser / Athena. |
| **`analyse`** | Five fixed docs from one analysis call | Quick static snapshot without full pipeline. |

## Standards (Nike / static path)

- **ISO 25010** — quality characteristics  
- **ISO 42010** — architectural views  
- Nike’s prompt instructs **applied** standards (SOLID, OWASP, language norms) tied to **change type** and **this repo**, not generic quotes.

## Tuning Studio

Olympus provides the **Tuning Studio** (FastAPI + React in the Olympus monorepo) for prompt versioning, run logs, and isolation re-runs. Repo Analyser agents are plain YAML on disk until synced via `OLYMPUS_STUDIO=1` when using the Olympus API.

## License

MIT
