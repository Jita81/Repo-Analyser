"""
Ingestion layer.
Reads a repository from disk and produces a RepoSnapshot — a bounded,
structured representation that is appropriate for sending to Claude.
Design decisions:
- We do NOT send everything. We send the right things.
- Sampling is deterministic: entry points, largest files, test examples.
- Binary files, build artifacts, and generated code are excluded.
- The file tree is filtered but complete (for structural understanding).
"""

from __future__ import annotations

import os
from pathlib import Path

from .models import DependencyFile, FileEntry, RepoSnapshot

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EXCLUDED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    "target",
    "out",
    ".next",
    ".nuxt",
    ".output",
    "vendor",
    "venv",
    ".venv",
    "env",
    ".env",
    "coverage",
    ".coverage",
    "htmlcov",
    ".idea",
    ".vscode",
    ".DS_Store",
}

EXCLUDED_EXTENSIONS = {
    # Compiled / binary
    ".pyc",
    ".pyo",
    ".pyd",
    ".so",
    ".dll",
    ".dylib",
    ".exe",
    ".o",
    ".a",
    # Media
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".ico",
    ".webp",
    ".mp4",
    ".mp3",
    # Archives
    ".zip",
    ".tar",
    ".gz",
    ".bz2",
    ".rar",
    ".7z",
    # Lock files (we want the manifest, not the lock)
    ".lock",
    # Fonts
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    # Data / generated
    ".min.js",
    ".min.css",
    ".map",
}

DEPENDENCY_FILES = {
    "package.json": "npm",
    "requirements.txt": "pip",
    "pyproject.toml": "pip",
    "setup.py": "pip",
    "setup.cfg": "pip",
    "Cargo.toml": "cargo",
    "go.mod": "go",
    "pom.xml": "maven",
    "build.gradle": "gradle",
    "build.gradle.kts": "gradle",
    "composer.json": "composer",
    "Gemfile": "ruby",
}

LANGUAGE_BY_EXTENSION = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".jsx": "JavaScript",
    ".tsx": "TypeScript",
    ".rs": "Rust",
    ".go": "Go",
    ".java": "Java",
    ".cs": "C#",
    ".cpp": "C++",
    ".c": "C",
    ".rb": "Ruby",
    ".php": "PHP",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".scala": "Scala",
    ".ex": "Elixir",
    ".hs": "Haskell",
    ".ml": "OCaml",
    ".sh": "Shell",
    ".bash": "Shell",
    ".sql": "SQL",
    ".html": "HTML",
    ".css": "CSS",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".json": "JSON",
    ".toml": "TOML",
    ".md": "Markdown",
}

FRAMEWORK_SIGNALS = {
    "next.config": "Next.js",
    "nuxt.config": "Nuxt.js",
    "vite.config": "Vite",
    "webpack.config": "Webpack",
    "django": "Django",
    "flask": "Flask",
    "fastapi": "FastAPI",
    "express": "Express",
    "nestjs": "@nestjs",
    "rails": "Ruby on Rails",
    "spring": "Spring",
    "react": "React",
    "vue": "Vue",
    "angular": "Angular",
    "svelte": "Svelte",
    "remix": "Remix",
}

ENTRY_POINT_PATTERNS = {
    "main.py",
    "app.py",
    "server.py",
    "index.py",
    "run.py",
    "main.ts",
    "main.js",
    "index.ts",
    "index.js",
    "app.ts",
    "app.js",
    "main.rs",
    "main.go",
    "main.java",
    "Program.cs",
    "manage.py",  # Django
}

DOC_PATTERNS = {"architecture", "adr", "decision", "design", "overview", "context"}

MAX_SAMPLE_FILES = 20
MAX_FILE_SIZE_BYTES = 100_000  # Skip files over 100KB


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------


def ingest(repo_path: Path) -> RepoSnapshot:
    """
    Read a repository and produce a RepoSnapshot.

    Args:
        repo_path: Absolute path to the repository root.

    Returns:
        A structured snapshot ready for analysis.
    """
    repo_path = repo_path.resolve()
    if not repo_path.is_dir():
        raise ValueError(f"Repository path does not exist or is not a directory: {repo_path}")

    all_files = _walk_repo(repo_path)
    language_counts: dict[str, int] = {}
    file_tree: list[str] = []
    for f in all_files:
        rel = str(Path(f.path))
        file_tree.append(rel)
        if f.language:
            language_counts[f.language] = language_counts.get(f.language, 0) + 1

    primary_language = max(language_counts, key=language_counts.get) if language_counts else None
    detected_languages = sorted(language_counts, key=language_counts.get, reverse=True)
    dependency_files = _read_dependency_files(repo_path)
    detected_frameworks = _detect_frameworks(repo_path, dependency_files)
    readme = _read_readme(repo_path)
    existing_docs = _read_existing_docs(repo_path, all_files)
    sampled_files = _sample_files(repo_path, all_files)

    return RepoSnapshot(
        repo_path=str(repo_path),
        repo_name=repo_path.name,
        primary_language=primary_language,
        detected_languages=detected_languages,
        detected_frameworks=detected_frameworks,
        file_tree=file_tree,
        sampled_files=sampled_files,
        dependency_files=dependency_files,
        readme_content=readme,
        existing_docs=existing_docs,
        total_file_count=len(all_files),
        sampled_file_count=len(sampled_files),
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _walk_repo(repo_path: Path) -> list[FileEntry]:
    """Walk the repository, excluding noise, and return all relevant files."""
    entries: list[FileEntry] = []
    for root, dirs, files in os.walk(repo_path):
        # Prune excluded directories in-place (affects os.walk traversal)
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS and not d.startswith(".")]
        for filename in files:
            full_path = Path(root) / filename
            rel_path = full_path.relative_to(repo_path)
            # Skip excluded extensions
            suffix = full_path.suffix.lower()
            if suffix in EXCLUDED_EXTENSIONS:
                continue
            # Skip minified files
            if filename.endswith(".min.js") or filename.endswith(".min.css"):
                continue
            try:
                size = full_path.stat().st_size
            except OSError:
                continue

            language = LANGUAGE_BY_EXTENSION.get(suffix)
            entries.append(
                FileEntry(
                    path=str(rel_path),
                    language=language,
                    size_bytes=size,
                )
            )
    return entries


def _read_dependency_files(repo_path: Path) -> list[DependencyFile]:
    """Read known dependency manifest files from the repo root."""
    result: list[DependencyFile] = []
    for filename, kind in DEPENDENCY_FILES.items():
        candidate = repo_path / filename
        if candidate.is_file():
            try:
                content = candidate.read_text(encoding="utf-8", errors="replace")
                result.append(DependencyFile(path=filename, kind=kind, content=content))
            except OSError:
                pass
    return result


def _detect_frameworks(repo_path: Path, dep_files: list[DependencyFile]) -> list[str]:
    """Detect frameworks from config file names and dependency file contents."""
    detected: set[str] = set()
    dep_content = " ".join(df.content.lower() for df in dep_files)
    for signal, framework in FRAMEWORK_SIGNALS.items():
        if signal in dep_content:
            detected.add(framework)
    # Config file signals
    for item in repo_path.iterdir():
        for signal, framework in FRAMEWORK_SIGNALS.items():
            if signal in item.name.lower():
                detected.add(framework)
    return sorted(detected)


def _read_readme(repo_path: Path) -> str | None:
    """Read the repository README if one exists."""
    for candidate in ["README.md", "README.rst", "README.txt", "README"]:
        path = repo_path / candidate
        if path.is_file():
            try:
                return path.read_text(encoding="utf-8", errors="replace")[:5000]
            except OSError:
                pass
    return None


def _read_existing_docs(repo_path: Path, all_files: list[FileEntry]) -> list[FileEntry]:
    """Find and read existing architecture/design documentation."""
    doc_files: list[FileEntry] = []
    for entry in all_files:
        path_lower = entry.path.lower()
        if any(pattern in path_lower for pattern in DOC_PATTERNS):
            if entry.path.endswith((".md", ".txt", ".rst")):
                full_path = repo_path / entry.path
                try:
                    content = full_path.read_text(encoding="utf-8", errors="replace")
                    doc_files.append(
                        FileEntry(
                            path=entry.path,
                            language=entry.language,
                            size_bytes=entry.size_bytes,
                            is_sampled=True,
                            content=content[:3000],
                        )
                    )
                except OSError:
                    pass
    return doc_files[:5]  # Cap at 5 doc files


def _sample_files(repo_path: Path, all_files: list[FileEntry]) -> list[FileEntry]:
    """
    Select a representative sample of source files for analysis.
    Strategy (in priority order):
    1. Entry points (main.py, index.ts, etc.)
    2. Test files (one example per test type)
    3. Largest source files (structural complexity lives here)
    Total cap: MAX_SAMPLE_FILES files.
    """
    sampled: list[FileEntry] = []
    seen_paths: set[str] = set()

    source_extensions = {
        ext
        for ext, lang in LANGUAGE_BY_EXTENSION.items()
        if lang not in {"YAML", "JSON", "TOML", "Markdown", "HTML", "CSS"}
    }

    def _read_and_add(entry: FileEntry) -> bool:
        if entry.path in seen_paths:
            return False
        if entry.size_bytes > MAX_FILE_SIZE_BYTES:
            return False
        full_path = repo_path / entry.path
        try:
            content = full_path.read_text(encoding="utf-8", errors="replace")
            sampled.append(
                FileEntry(
                    path=entry.path,
                    language=entry.language,
                    size_bytes=entry.size_bytes,
                    is_sampled=True,
                    content=content,
                )
            )
            seen_paths.add(entry.path)
            return True
        except OSError:
            return False

    # Priority 1: entry points
    for entry in all_files:
        filename = Path(entry.path).name
        if filename in ENTRY_POINT_PATTERNS:
            _read_and_add(entry)

    # Priority 2: test files (up to 3)
    test_count = 0
    for entry in all_files:
        if test_count >= 3:
            break
        path_lower = entry.path.lower()
        is_test_path = "test" in path_lower or "spec" in path_lower
        if is_test_path and Path(entry.path).suffix in source_extensions:
            if _read_and_add(entry):
                test_count += 1

    # Priority 3: largest source files
    source_files = sorted(
        [f for f in all_files if Path(f.path).suffix in source_extensions],
        key=lambda f: f.size_bytes,
        reverse=True,
    )
    for entry in source_files:
        if len(sampled) >= MAX_SAMPLE_FILES:
            break
        _read_and_add(entry)

    return sampled
