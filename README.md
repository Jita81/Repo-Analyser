# Repo Analyser

Analyse a repository and generate structured context documents for AI-assisted coding.

Part of the Automated Agile framework.

## What it does

Repo Analyser reads your codebase and produces five context documents that give AI coding agents (Claude Code, Cursor, Copilot, etc.) the institutional knowledge they need to code to your standard — not just generically.

Without context documents, agents produce code that works but degrades your codebase over time: wrong patterns, inconsistent conventions, missed architectural decisions.

With context documents, agents understand what “good” looks like in your specific codebase.

## Output

Running `repo-analyser analyse` produces a `.context/` directory containing:

| Document | Contents |
|----------|----------|
| `AGENT_BRIEF.md` | Entry point. What the repo is, critical notes, index. Read this first. |
| `ARCHITECTURE.md` | System structure, components, relationships (ISO 42010). |
| `PATTERNS.md` | Concrete coding patterns with examples from your codebase. |
| `STANDARDS.md` | Quality standards mapped to ISO 25010. |
| `GAPS.md` | Known gaps and inconsistencies, with agent instructions. |

## Installation

From this repository:

```bash
pip install -e .
```

Or from PyPI (when published):

```bash
pip install repo-analyser
```

## Usage

Set your Anthropic API key, then analyse a local repository:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
repo-analyser analyse --repo ./path/to/your/repo
```

Custom output directory:

```bash
repo-analyser analyse --repo ./path/to/your/repo --output ./docs/context
```

## How to use the output

1. Run `repo-analyser analyse` on your repo.
2. Commit the `.context/` directory (or add it to your agent’s context path).
3. When starting an agentic coding session, instruct your agent to read `.context/AGENT_BRIEF.md` first.
4. The agent will code to your codebase’s standard, not generic best practice.

## Standards

Context documents are aligned with:

- **ISO 25010** — Software quality characteristics (maintainability, reliability, security, etc.).
- **ISO 42010** — Architecture description (structural, behavioural, deployment views).

## License

MIT
