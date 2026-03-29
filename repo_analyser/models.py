"""
Data models for Repo Analyser.
These models are the contracts between layers. Changing a model here
has deliberate downstream consequences — treat them as the source of truth
for the output standard.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Ingestion layer output
# ---------------------------------------------------------------------------


class FileEntry(BaseModel):
    """A single file in the repository."""

    path: str
    language: str | None = None
    size_bytes: int = 0
    is_sampled: bool = False  # True if content was read for analysis
    content: str | None = None  # Only populated when is_sampled=True


class DependencyFile(BaseModel):
    """A dependency manifest file (package.json, requirements.txt, etc.)."""

    path: str
    kind: Literal[
        "npm",
        "pip",
        "cargo",
        "go",
        "maven",
        "gradle",
        "composer",
        "ruby",
        "other",
    ]
    content: str


class RepoSnapshot(BaseModel):
    """
    Structured representation of a repository, ready for LLM analysis.
    This is the output of the ingestion layer and the input to the analysis layer.

    It is deliberately bounded — we do not send everything to Claude, we send
    the right things.
    """

    repo_path: str
    repo_name: str
    primary_language: str | None = None
    detected_languages: list[str] = Field(default_factory=list)
    detected_frameworks: list[str] = Field(default_factory=list)
    file_tree: list[str] = Field(default_factory=list)  # Relative paths, filtered
    sampled_files: list[FileEntry] = Field(default_factory=list)
    dependency_files: list[DependencyFile] = Field(default_factory=list)
    readme_content: str | None = None
    existing_docs: list[FileEntry] = Field(default_factory=list)
    total_file_count: int = 0
    sampled_file_count: int = 0

    def to_prompt_text(self) -> str:
        """Serialise the snapshot into a structured text block for the analysis prompt."""
        sections: list[str] = []
        sections.append(f"# Repository: {self.repo_name}")
        sections.append(
            f"Primary language: {self.primary_language or 'unknown'}\n"
            f"Detected languages: {', '.join(self.detected_languages) or 'none'}\n"
            f"Detected frameworks: {', '.join(self.detected_frameworks) or 'none'}\n"
            f"Total files: {self.total_file_count} "
            f"({self.sampled_file_count} sampled for analysis)\n"
        )
        if self.readme_content:
            sections.append(f"## README\n{self.readme_content[:3000]}")
        if self.dependency_files:
            dep_text = "\n\n".join(
                f"### {df.path}\n{df.content[:2000]}" for df in self.dependency_files
            )
            sections.append(f"## Dependency Files\n{dep_text}")
        sections.append("## File Tree (filtered)\n" + "\n".join(self.file_tree[:200]))
        if self.sampled_files:
            file_text = "\n\n".join(
                f"### {f.path}\n```\n{f.content[:3000]}\n```"
                for f in self.sampled_files
                if f.content
            )
            sections.append(f"## Sampled Source Files\n{file_text}")
        if self.existing_docs:
            doc_text = "\n\n".join(
                f"### {d.path}\n{d.content[:2000]}" for d in self.existing_docs if d.content
            )
            sections.append(f"## Existing Documentation\n{doc_text}")
        return "\n\n---\n\n".join(sections)


# ---------------------------------------------------------------------------
# Analysis layer output
# ---------------------------------------------------------------------------


class CodePattern(BaseModel):
    """A concrete coding pattern observed in the repository."""

    name: str
    description: str
    example: str | None = None  # Actual code from the repo
    locations: list[str] = Field(default_factory=list)  # File paths where seen


class QualityCharacteristic(BaseModel):
    """
    A quality characteristic mapped to ISO 25010.
    ISO 25010 characteristics: Functional Suitability, Performance Efficiency,
    Compatibility, Interaction Capability, Reliability, Security,
    Maintainability, Flexibility, Safety.
    """

    characteristic: str  # ISO 25010 characteristic name
    observed_level: Literal["strong", "adequate", "weak", "absent", "unknown"]
    evidence: str  # What in the codebase led to this assessment
    recommendations: list[str] = Field(default_factory=list)


class ArchitecturalView(BaseModel):
    """
    A view of the system architecture, aligned with ISO 42010.
    ISO 42010 defines architecture as expressed through multiple views,
    each addressing different stakeholder concerns.
    """

    view_name: str  # e.g. "Structural", "Behavioural", "Deployment"
    description: str
    key_components: list[str] = Field(default_factory=list)
    relationships: list[str] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)  # Architectural decisions observed


class Gap(BaseModel):
    """A gap, inconsistency, or undocumented decision in the codebase."""

    title: str
    description: str
    severity: Literal["high", "medium", "low"]
    category: Literal[
        "pattern_inconsistency",
        "missing_documentation",
        "architectural_ambiguity",
        "quality_concern",
        "security_concern",
        "test_coverage",
        "dependency_risk",
    ]
    agent_instruction: str  # What an agent should do when it encounters this


class AnalysisResult(BaseModel):
    """
    The structured output of Claude's analysis of a repository.
    This is the output of the analysis layer and the input to the generation layer.
    It maps directly to the five context documents.
    """

    repo_name: str
    summary: str  # One paragraph: what this repo is and does
    architectural_views: list[ArchitecturalView] = Field(default_factory=list)
    patterns: list[CodePattern] = Field(default_factory=list)
    quality_characteristics: list[QualityCharacteristic] = Field(default_factory=list)
    gaps: list[Gap] = Field(default_factory=list)
    agent_onboarding_notes: list[str] = Field(default_factory=list)
    analysis_confidence: Literal["high", "medium", "low"] = "medium"
    analysis_notes: str = ""  # Any caveats about the analysis itself


# ---------------------------------------------------------------------------
# Generation layer output
# ---------------------------------------------------------------------------


class ContextDocument(BaseModel):
    """A single generated context document."""

    filename: str
    title: str
    content: str


class ContextDocumentSet(BaseModel):
    """The full set of context documents produced for a repository."""

    repo_name: str
    documents: list[ContextDocument] = Field(default_factory=list)
    output_dir: str = ".context"

    def write(self, output_path: Path) -> list[Path]:
        """Write all documents to disk. Returns list of written paths."""
        output_path.mkdir(parents=True, exist_ok=True)
        written: list[Path] = []
        for doc in self.documents:
            file_path = output_path / doc.filename
            file_path.write_text(doc.content, encoding="utf-8")
            written.append(file_path)
        return written
