# Repo Analyser

**Repo Analyser** is [Athena](https://github.com/Jita81/Olympus-Agent-Framework)’s pipeline as a product: **eight YAML agents + an orchestrator** on the **Olympus** runtime, turning a **repository** and a **user story** (with acceptance criteria) into a **structured context package** for coding agents.

It is the Automated Agile idea of a **Context Engineer** in a box — not a generic doc generator.

---

## Where this repo is today (March 2026)

This branch is a **working integration** of:

| Area | Status |
|------|--------|
| **Bundled pipeline** | `repo_analyser/pipelines/athena/` — `athena-pipeline.yaml` + agent YAML for Lethe → … → Athena. |
| **Primary CLI** | `repo-analyser package` — runs Olympus `run_pipeline`, optional Chroma index, writes `CONTEXT_PACKAGE.md` + SQLite run log. |
| **Legacy CLI** | `repo-analyser analyse` — single Claude pass → five Markdown files in `.context/` (no LangGraph). |
| **Specifications** | PDFs in [`docs/specifications/`](docs/specifications/); traceability in [`docs/SPECIFICATION_COVERAGE.md`](docs/SPECIFICATION_COVERAGE.md). |
| **Olympus framework** | Full hero schemas, Lethe `olympus_lethe` + `lethe_merkle.json`, Pallas persistence tools, Nike ISO matrix, etc. live in **[Olympus-Agent-Framework](https://github.com/Jita81/Olympus-Agent-Framework)** (`cursor/iris-standing-knowledge` / **v0.6.0**). **Install Olympus from that repo** until `olympus` is published at ≥0.6. |

**Not included as a one-click “cloud deploy” here:** hosted API, Docker image, or PyPI publish automation — you deploy by **installing Python packages** and running the CLI (see below). **Tuning Studio** ships with Olympus; wire it separately if you want a web UI.

---

## Architecture

| Layer | Heroes | Role |
|-------|--------|------|
| **Standing knowledge** | Lethe → Iris → Pallas → Asclepius | Vector index, Iris explanations, `CodebaseKnowledge`, gap register. |
| **Change-specific** | Daedalus → Nike → Tyche → Arete | Boundary, retrieved snippets, standards + testing templates, decomposition, contracts. |
| **Assembly** | Athena | Merges `ContextPackage` + `PackageScore`. |

Runtime: **LangGraph**, **typed `AthenaPipelineState`**, tool loop, **SQLite** run store (`olympus show-run`).

---

## Deploy / run locally

### Prerequisites

- **Python 3.11+**
- **Anthropic API key** *or* a local **OpenAI-compatible** server ([Ollama](https://ollama.com), etc.) via Olympus env vars
- **Olympus ≥ 0.6.0** (from source until PyPI catches up)

### 1. Install Olympus (required for `package`)

```bash
git clone https://github.com/Jita81/Olympus-Agent-Framework.git
cd Olympus-Agent-Framework/packages/olympus
# Use branch with v0.6.0 spec alignment if `main` lags:
# git checkout cursor/iris-standing-knowledge
pip install -e ".[dev]"
```

### 2. Install Repo Analyser

```bash
cd /path/to/Repo-Analyser
pip install -e ".[dev]"
# Optional: pip install -e ".[athena]" after olympus is on PyPI with matching version
```

### 3. Run the context package

```bash
export ANTHROPIC_API_KEY=sk-ant-...

repo-analyser package \
  --repo /path/to/target/repo \
  --user-story "Add validation to the checkout API" \
  --acceptance "Invalid payloads return 400"
```

**Outputs**

| Artifact | Location |
|----------|----------|
| Context package (Markdown) | `<repo>/.context/CONTEXT_PACKAGE.md` (override with `--output`) |
| Run log (SQLite) | `<repo>/.olympus/runs.sqlite` (override with `--db`) |
| Chroma index | `<repo>/.olympus/chroma_lethe` (override with `--chroma-path`) |
| Lethe file hashes | `<repo>/.olympus/lethe_merkle.json` |
| Iris explanations (JSON) | `<repo>/.olympus/iris_explanations.json` |
| Pallas knowledge (JSON) | `<repo>/.olympus/pallas_knowledge.json` (when agent persists) |

```bash
olympus show-run <run_id> --db /path/to/target/repo/.olympus/runs.sqlite
```

### Self-hosted LLM (no Anthropic)

```bash
ollama serve
ollama pull llama3.2

export OLYMPUS_OPENAI_COMPATIBLE=1
export OPENAI_BASE_URL=http://127.0.0.1:11434/v1
export OLYMPUS_MODEL=llama3.2
# Do not set ANTHROPIC_API_KEY

repo-analyser package --repo . --user-story "..." --acceptance "..."
```

Use an **instruct** model that can emit **valid JSON** per hero; small models often fail on large schemas.

### Legacy: five-document path

No Olympus required for this command only (still needs `ANTHROPIC_API_KEY` for real analysis):

```bash
repo-analyser analyse --repo ./path/to/repo
```

→ `AGENT_BRIEF.md`, `ARCHITECTURE.md`, `PATTERNS.md`, `STANDARDS.md`, `GAPS.md` under `.context/`.

---

## CI (this repository)

On push/PR, GitHub Actions runs **Ruff** and **pytest** on the bundled package (see `.github/workflows/ci.yml`). Full Athena integration tests run in the **Olympus** repo.

---

## Project layout

```
repo_analyser/
  cli.py                 # package + analyse
  pipeline_runner.py     # invokes Olympus + writes CONTEXT_PACKAGE.md
  pipelines/athena/      # shipped YAML graph + agents
  analysis.py …         # legacy five-doc pipeline
docs/
  specifications/        # product + hero PDFs
  SPECIFICATION_COVERAGE.md
```

---

## Standards & specs

- **ISO 25010 / ISO 42010** — wired through Nike and the static `analyse` path.
- **PDF index** — [`docs/specifications/`](docs/specifications/)
- **Implementation matrix** — [`docs/SPECIFICATION_COVERAGE.md`](docs/SPECIFICATION_COVERAGE.md)

---

## License

MIT

---

## Links

- [Olympus Agent Framework](https://github.com/Jita81/Olympus-Agent-Framework)  
- [Automated Agile](https://automatedagile.co.uk) (framework context)
