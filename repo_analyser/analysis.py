"""
Analysis layer.
Sends a RepoSnapshot to Claude and returns a structured AnalysisResult.
Design decisions:
- The prompt is the core IP. It is structured, versioned, and opinionated.
- We request JSON output and parse it into our typed models.
- The prompt maps explicitly to ISO 25010 and ISO 42010.
- We keep the analysis prompt separate from the generation logic — they have
  different rates of change.
"""

from __future__ import annotations

import json
import re

import anthropic

from .models import (
    AnalysisResult,
    ArchitecturalView,
    CodePattern,
    Gap,
    QualityCharacteristic,
    RepoSnapshot,
)

MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 8000

# ---------------------------------------------------------------------------
# Analysis prompt — the core IP
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are an expert software architect and code quality analyst.
Your role is to analyse a repository snapshot and produce a structured analysis
that will be used to generate context documents for AI-assisted coding agents.
Your analysis must be:
- Grounded in evidence from the actual code provided, not assumptions
- Mapped to ISO 25010 (software quality characteristics) and ISO 42010 (architecture description)
- Actionable — every observation must translate into a concrete instruction for an agent
- Honest — flag gaps, inconsistencies, and unknowns rather than inventing coverage
You will return a single JSON object. No markdown, no preamble, no explanation outside the JSON."""

ANALYSIS_PROMPT_TEMPLATE = """Analyse this repository and return a structured JSON analysis.

{repo_snapshot}

---

Return this exact JSON structure (all fields required):

{{
  "summary": "One paragraph: what this repository is, what it does, and its primary purpose",
  "architectural_views": [
    {{
      "view_name": "Structural | Behavioural | Deployment | Data",
      "description": "Description of this architectural view",
      "key_components": ["Component 1", "Component 2"],
      "relationships": ["Component A calls Component B", "Component C depends on Component D"],
      "decisions": ["Architectural decision observed, e.g. layered architecture, event-driven"]
    }}
  ],
  "patterns": [
    {{
      "name": "Pattern name (e.g. Repository Pattern, Error boundary, Dependency injection)",
      "description": "How this pattern is used in this codebase specifically",
      "example": "Short code snippet (2-5 lines) showing the pattern as used here",
      "locations": ["path/to/file.py", "path/to/other_file.py"]
    }}
  ],
  "quality_characteristics": [
    {{
      "characteristic": "One of: Functional Suitability | Performance Efficiency | Compatibility | Interaction Capability | Reliability | Security | Maintainability | Flexibility | Safety",
      "observed_level": "One of: strong | adequate | weak | absent | unknown",
      "evidence": "Specific evidence from the codebase that led to this assessment",
      "recommendations": ["Specific recommendation for an agent working in this codebase"]
    }}
  ],
  "gaps": [
    {{
      "title": "Short gap title",
      "description": "What is missing, inconsistent, or undocumented",
      "severity": "high | medium | low",
      "category": "pattern_inconsistency | missing_documentation | architectural_ambiguity | quality_concern | security_concern | test_coverage | dependency_risk",
      "agent_instruction": "Concrete instruction for an agent: what to do when it encounters this"
    }}
  ],
  "agent_onboarding_notes": [
    "Critical thing an agent must know before modifying this codebase",
    "Another critical note"
  ],
  "analysis_confidence": "high | medium | low",
  "analysis_notes": "Any caveats about this analysis — what was unclear, what was not sampled"
}}

Guidelines:
- Include 1-4 architectural views (only those visible in the provided code)
- Include 3-10 patterns (concrete, specific to this codebase)
- Assess all 9 ISO 25010 quality characteristics listed above
  (use 'unknown' if insufficient evidence)
- Include all gaps found, no matter how minor (severity distinguishes them)
- Agent onboarding notes should be the 3-7 most critical things an agent needs to know
- Be specific. "Uses async/await consistently" is better than "uses modern JavaScript"
"""


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------


def analyse(snapshot: RepoSnapshot, api_key: str | None = None) -> AnalysisResult:
    """
    Send a RepoSnapshot to Claude and return a structured AnalysisResult.

    Args:
        snapshot: The structured repository snapshot from the ingestion layer.
        api_key: Anthropic API key. If None, uses ANTHROPIC_API_KEY env var.

    Returns:
        A structured AnalysisResult ready for document generation.

    Raises:
        ValueError: If the API response cannot be parsed into an AnalysisResult.
        anthropic.APIError: If the API call fails.
    """
    client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()

    prompt_text = snapshot.to_prompt_text()
    user_prompt = ANALYSIS_PROMPT_TEMPLATE.format(repo_snapshot=prompt_text)
    message = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    raw_text = message.content[0].text
    return _parse_response(raw_text, snapshot.repo_name)


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------


def _parse_response(raw_text: str, repo_name: str) -> AnalysisResult:
    """Parse Claude's JSON response into a typed AnalysisResult."""
    # Strip any accidental markdown fences
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw_text.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        snippet = raw_text[:500]
        msg = f"Claude returned invalid JSON: {e}\n\nRaw response:\n{snippet}"
        raise ValueError(msg) from e

    try:
        architectural_views = [
            ArchitecturalView(**view) for view in data.get("architectural_views", [])
        ]
        patterns = [CodePattern(**p) for p in data.get("patterns", [])]
        quality_characteristics = [
            QualityCharacteristic(**q) for q in data.get("quality_characteristics", [])
        ]
        gaps = [Gap(**g) for g in data.get("gaps", [])]
        return AnalysisResult(
            repo_name=repo_name,
            summary=data.get("summary", ""),
            architectural_views=architectural_views,
            patterns=patterns,
            quality_characteristics=quality_characteristics,
            gaps=gaps,
            agent_onboarding_notes=data.get("agent_onboarding_notes", []),
            analysis_confidence=data.get("analysis_confidence", "medium"),
            analysis_notes=data.get("analysis_notes", ""),
        )
    except (KeyError, TypeError) as e:
        raise ValueError(f"Claude response did not match expected schema: {e}") from e
