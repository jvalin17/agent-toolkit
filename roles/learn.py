#!/usr/bin/env python3
"""Role knowledge learning — fetch, study, store, synthesize.

Single script for all role knowledge acquisition. Fetches any resource
(repo, URL, local path, paper), studies it through a role-specific lens
using LLM, and stores structured knowledge.

Usage:
  python learn.py --role backend --repo https://github.com/nestjs/nest
  python learn.py --role frontend --url https://react.dev/blog/2026/react-20
  python learn.py --role backend --path /path/to/local/project
  python learn.py --role all --repo https://github.com/calcom/cal.com
  python learn.py --synthesize backend
  python learn.py --health backend
"""

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore

try:
    from markdownify import markdownify
except ImportError:
    markdownify = None  # type: ignore


ROLES_DIR = Path(__file__).resolve().parent
MAX_CONTENT_CHARS = 32000  # ~8K tokens
MAX_FILES_PER_EXTRACT = 40  # don't over-analyze — cap extracted files
MAX_REPOS_PER_ROLE = 10  # prevent runaway indexing
MAX_STUDY_RETRIES = 1  # don't burn tokens on retries

# Security: never read or send these files
SENSITIVE_FILE_PATTERNS = {
    ".env", ".env.local", ".env.production", ".env.staging",
    "credentials.json", "service-account.json", "*.pem", "*.key",
    "*.p12", "*.pfx", "secrets.yml", "secrets.yaml",
    ".npmrc", ".pypirc", ".netrc", "id_rsa", "id_ed25519",
}

IGNORE_DIRS = {
    "node_modules", ".git", "dist", "build", "__pycache__", ".next",
    ".nuxt", "vendor", "target", ".gradle", "Pods", "DerivedData",
    ".svelte-kit", ".output", "coverage", ".nyc_output", ".cache",
}

# File patterns for extraction, ordered by priority
METADATA_FILES = [
    "package.json", "pyproject.toml", "Cargo.toml", "go.mod",
    "build.gradle", "build.gradle.kts", "Podfile", "Gemfile",
    "pom.xml", "composer.json",
]

CONFIG_FILES = [
    "*.config.*", ".env.example", "docker-compose.*", "Dockerfile",
    "tsconfig.json", "next.config.*", "vite.config.*",
]

ENTRY_PATTERNS = [
    "src/index.*", "src/main.*", "src/app.*", "server.*",
    "app.*", "main.*", "index.*", "cmd/main.*",
]

ROUTE_PATTERNS = [
    "**/routes/**/*", "**/api/**/*", "**/controllers/**/*",
    "**/endpoints/**/*", "**/handlers/**/*",
]

MODEL_PATTERNS = [
    "**/models/**/*", "**/schema*", "**/entities/**/*",
    "**/types/**/*", "prisma/schema.prisma", "**/migrations/**/*",
]

TEST_PATTERNS = [
    "**/__tests__/**/*", "**/test/**/*", "**/tests/**/*",
    "**/*.test.*", "**/*.spec.*",
]


# --- Data classes ---


@dataclass
class FetchResult:
    source_type: str  # "repo", "article", "path", "paper"
    path: Path


@dataclass
class ExtractResult:
    file_tree: str = ""
    files: List[str] = field(default_factory=list)
    contents: Dict[str, str] = field(default_factory=dict)

    def add_content(self, name: str, content: str) -> None:
        self.files.append(name)
        self.contents[name] = content

    def add_file(self, filepath: Path, relative_to: Path) -> None:
        try:
            # Skip sensitive files
            _sensitive = {
                ".env", ".env.local", ".env.production", "credentials.json",
                "service-account.json", "secrets.yml", "secrets.yaml",
                ".npmrc", ".pypirc", ".netrc", "id_rsa", "id_ed25519",
            }
            _sensitive_ext = {".pem", ".key", ".p12", ".pfx"}
            name = filepath.name
            if name in _sensitive or filepath.suffix in _sensitive_ext:
                return
            # Skip binary files
            content = filepath.read_text(errors="ignore")
            if "\x00" in content[:1000]:
                return
            rel = str(filepath.relative_to(relative_to))
            self.files.append(rel)
            self.contents[rel] = content
        except (OSError, ValueError):
            pass

    def to_text(self) -> str:
        parts = []
        if self.file_tree:
            parts.append(f"FILE TREE:\n{self.file_tree}\n")
        for name, content in self.contents.items():
            parts.append(f"--- {name} ---\n{content}\n")
        text = "\n".join(parts)
        if len(text) > MAX_CONTENT_CHARS:
            text = text[:MAX_CONTENT_CHARS] + "\n\n[TRUNCATED]"
        return text


@dataclass
class Knowledge:
    role: str
    source: Dict[str, str]
    content: str
    studied_at: str


@dataclass
class RoleHealthReport:
    role: str
    gaps: List[Dict[str, str]] = field(default_factory=list)

    def add_gap(self, gap_type: str, message: str) -> None:
        self.gaps.append({"type": gap_type, "message": message})

    def to_text(self) -> str:
        if not self.gaps:
            return f"Role '{self.role}': HEALTHY (no gaps)"
        lines = [f"Role '{self.role}': {len(self.gaps)} gap(s)"]
        for gap in self.gaps:
            lines.append(f"  [{gap['type']}] {gap['message']}")
        return "\n".join(lines)


# --- Helpers ---


def slug(source: str) -> str:
    """Convert a URL or path to a filesystem-safe slug."""
    # Take last meaningful segment
    cleaned = source.rstrip("/")
    # Remove query strings and fragments
    cleaned = re.split(r"[?#]", cleaned)[0]
    # For URLs, take the last 2 path segments (org/repo)
    if "://" in cleaned:
        parts = cleaned.split("/")
        # Filter out empty strings and protocol parts
        meaningful = [p for p in parts if p and ":" not in p]
        if len(meaningful) >= 2:
            cleaned = f"{meaningful[-2]}-{meaningful[-1]}"
        elif meaningful:
            cleaned = meaningful[-1]
        else:
            cleaned = "unknown"
    else:
        # For paths, take the last segment
        cleaned = Path(cleaned).name

    # Sanitize
    cleaned = re.sub(r"[^a-zA-Z0-9_-]", "-", cleaned)
    cleaned = re.sub(r"-+", "-", cleaned).strip("-").lower()
    return cleaned or "unknown"


def _generate_tree(directory: Path, max_depth: int = 3, prefix: str = "") -> str:
    """Generate a directory tree string, ignoring common non-essential dirs."""
    if max_depth <= 0:
        return ""

    lines = []
    try:
        entries = sorted(directory.iterdir(), key=lambda p: (not p.is_dir(), p.name))
    except PermissionError:
        return ""

    # Filter out ignored directories and hidden files
    entries = [
        e for e in entries
        if e.name not in IGNORE_DIRS and not e.name.startswith(".")
    ]

    for i, entry in enumerate(entries[:30]):  # cap entries per level
        connector = "└── " if i == len(entries) - 1 else "├── "
        lines.append(f"{prefix}{connector}{entry.name}")
        if entry.is_dir():
            extension = "    " if i == len(entries) - 1 else "│   "
            subtree = _generate_tree(entry, max_depth - 1, prefix + extension)
            if subtree:
                lines.append(subtree)

    return "\n".join(lines)


def _is_sensitive(filepath: Path) -> bool:
    """Check if a file matches sensitive patterns — never extract these."""
    name = filepath.name
    for pattern in SENSITIVE_FILE_PATTERNS:
        if pattern.startswith("*"):
            if name.endswith(pattern[1:]):
                return True
        elif name == pattern:
            return True
    return False


def _glob_files(directory: Path, patterns: List[str], max_files: int = 10) -> List[Path]:
    """Glob for files matching patterns, capped at max_files. Skips sensitive files."""
    found = []
    for pattern in patterns:
        for match in directory.glob(pattern):
            if (match.is_file()
                    and not any(p in match.parts for p in IGNORE_DIRS)
                    and not _is_sensitive(match)):
                found.append(match)
                if len(found) >= max_files:
                    return found
    return found


def _parse_role_frontmatter(role_path: Path) -> Dict[str, Any]:
    """Parse YAML-like frontmatter from a role.md file."""
    content = role_path.read_text()
    if not content.startswith("---"):
        return {"name": role_path.parent.name}

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {"name": role_path.parent.name}

    frontmatter = parts[1].strip()
    result = {}
    for line in frontmatter.split("\n"):
        if ":" in line:
            key, _, value = line.partition(":")
            result[key.strip()] = value.strip()
    return result


MODEL_MAP = {
    "sonnet": "claude-sonnet-4-6",
    "opus": "claude-opus-4-6",
    "haiku": "claude-haiku-4-5-20251001",
    "fable": "claude-fable-5",
}


def call_llm(prompt: str, max_tokens: int = 4000, model: str = "sonnet") -> str:
    """Call Anthropic Messages API via httpx. No SDK dependency.

    Requires ANTHROPIC_API_KEY environment variable.
    Model shortcuts: 'sonnet', 'opus', 'haiku' or full model ID.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY not set. Export it or use --dry-run.\n"
            "  export ANTHROPIC_API_KEY=sk-ant-..."
        )

    if httpx is None:
        raise ImportError("httpx is required: pip install httpx")

    model_id = MODEL_MAP.get(model, model)

    response = httpx.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": model_id,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=120,
    )

    if response.status_code != 200:
        error_detail = response.text[:500]
        raise RuntimeError(
            f"Anthropic API error ({response.status_code}): {error_detail}"
        )

    data = response.json()
    # Extract text from response content blocks
    content_blocks = data.get("content", [])
    text_parts = [
        block.get("text", "")
        for block in content_blocks
        if block.get("type") == "text"
    ]
    return "\n".join(text_parts)


# --- Step 1: FETCH ---


def fetch(source_type: str, source: str, cache_dir: Path) -> FetchResult:
    """Fetch a resource. Returns a FetchResult with local path."""
    cache_dir.mkdir(parents=True, exist_ok=True)

    if source_type == "path":
        local = Path(source)
        if not local.is_dir():
            raise ValueError(f"Path '{source}' is not a directory")
        return FetchResult(source_type="path", path=local)

    elif source_type == "repo":
        # Validate URL — only allow https:// git URLs
        if not source.startswith("https://"):
            raise ValueError(
                f"Only HTTPS repo URLs are allowed (got: {source[:50]}). "
                "Use --path for local directories."
            )
        # Block git exploit vectors
        if any(flag in source for flag in ["--upload-pack", "--config", "-c "]):
            raise ValueError(f"Suspicious repo URL rejected: {source[:50]}")

        repo_dir = cache_dir / slug(source)
        if repo_dir.exists():
            subprocess.run(
                ["git", "-C", str(repo_dir), "pull", "--ff-only"],
                capture_output=True, timeout=120, check=False,
            )
        else:
            subprocess.run(
                ["git", "clone", "--depth", "1", source, str(repo_dir)],
                capture_output=True, timeout=300, check=False,
            )
        return FetchResult(source_type="repo", path=repo_dir)

    elif source_type == "url":
        if httpx is None:
            raise ImportError("httpx is required for URL fetching: pip install httpx")

        response = httpx.get(source, follow_redirects=True, timeout=30)
        if markdownify:
            md_content = markdownify(response.text, strip=["script", "style", "nav"])
        else:
            # Fallback: strip HTML tags with regex
            md_content = re.sub(r"<[^>]+>", "", response.text)
            md_content = re.sub(r"\s+", " ", md_content).strip()

        save_path = cache_dir / f"{slug(source)}.md"
        save_path.write_text(md_content)
        return FetchResult(source_type="article", path=save_path)

    elif source_type == "paper":
        if httpx is None:
            raise ImportError("httpx is required for paper fetching: pip install httpx")

        response = httpx.get(source, follow_redirects=True, timeout=60)
        pdf_path = cache_dir / f"{slug(source)}.pdf"
        pdf_path.write_bytes(response.content)

        # Try to extract text from PDF
        try:
            import pdfplumber
            with pdfplumber.open(pdf_path) as pdf:
                text = "\n\n".join(page.extract_text() or "" for page in pdf.pages)
        except ImportError:
            text = f"[PDF downloaded to {pdf_path} — install pdfplumber for text extraction]"

        md_path = cache_dir / f"{slug(source)}.md"
        md_path.write_text(text)
        return FetchResult(source_type="paper", path=md_path)

    else:
        raise ValueError(f"Unknown source type: {source_type}")


# --- Step 2: EXTRACT ---


def extract_repo(repo_dir: Path) -> ExtractResult:
    """Extract key files from a repo using heuristics. No LLM.

    Guardrails:
    - Never extracts sensitive files (.env, credentials, keys)
    - Caps total files at MAX_FILES_PER_EXTRACT
    - Caps total content at MAX_CONTENT_CHARS
    - Skips binary files
    """
    result = ExtractResult()

    # File tree
    result.file_tree = _generate_tree(repo_dir, max_depth=3)

    # Metadata files (package.json, etc.)
    for filename in METADATA_FILES:
        filepath = repo_dir / filename
        if filepath.is_file():
            result.add_file(filepath, repo_dir)

    # README
    readme = repo_dir / "README.md"
    if readme.is_file():
        content = readme.read_text(errors="ignore")
        # Cap README at 3000 chars
        result.add_content("README.md", content[:3000])

    # Config files
    for f in _glob_files(repo_dir, CONFIG_FILES, max_files=5):
        result.add_file(f, repo_dir)

    # Entry points
    for f in _glob_files(repo_dir, ENTRY_PATTERNS, max_files=5):
        result.add_file(f, repo_dir)

    # Routes / API definitions
    for f in _glob_files(repo_dir, ROUTE_PATTERNS, max_files=10):
        result.add_file(f, repo_dir)

    # Models / schemas
    for f in _glob_files(repo_dir, MODEL_PATTERNS, max_files=10):
        result.add_file(f, repo_dir)

    # Tests (just a few to understand testing approach)
    for f in _glob_files(repo_dir, TEST_PATTERNS, max_files=3):
        result.add_file(f, repo_dir)

    return result


def extract_article(article_path: Path) -> ExtractResult:
    """Extract content from a markdown article."""
    result = ExtractResult()
    content = article_path.read_text(errors="ignore")
    result.add_content(article_path.name, content[:MAX_CONTENT_CHARS])
    return result


# --- Step 3: STUDY ---


def study(
    role_name: str,
    extracted: ExtractResult,
    source_info: Dict[str, str],
    roles_dir: Optional[Path] = None,
) -> Knowledge:
    """Ask LLM to study extracted content through a role-specific lens."""
    if roles_dir is None:
        roles_dir = ROLES_DIR

    # Load role definition
    role_md = roles_dir / role_name / "role.md"
    role_def = _parse_role_frontmatter(role_md) if role_md.is_file() else {}
    scope = role_def.get("scope", role_name)
    not_scope = role_def.get("not_scope", "")

    prompt = f"""You are studying this codebase/resource as a {role_name}.
Your expertise: {scope}
Not your concern: {not_scope}

SOURCE: {source_info['name']} ({source_info['type']})

EXTRACTED CONTENT:
{extracted.to_text()}

Extract EVERYTHING relevant to your role from this codebase. Be objective —
describe what you see, not what you think is good or bad. The human will
review and decide what to keep.

Answer these questions as structured markdown. Be specific — cite file
paths, function names, and concrete code patterns.

## 1. Patterns Used
What design patterns does this codebase use?
List each with a concrete example (file path, code snippet).

## 2. Architecture Decisions
What architectural choices were made? What tradeoffs?
(e.g., monolith vs microservices, SQL vs NoSQL, sync vs async)

## 3. Code Conventions
Naming, error handling, file structure, config management, logging.
Just describe what they do — don't judge.

## 4. How They Solve Problems
For problems relevant to your role, how does this codebase solve them?
(e.g., auth, caching, pagination, error handling, data fetching)
Include actual code patterns or approaches.

## 5. Dependencies & Tools
What libraries/tools are used and for what purpose?

## 6. Testing Approach
How do they test? Structure, fixtures, mocking, coverage strategy.

## 7. Deployment & Production Setup
How is this deployed? Monitoring, error recovery, configuration.

## 8. Tradeoffs & Decisions
What tradeoffs did they make? Document both sides — let the reviewer decide.
Format: DECISION → OPTION A (what they chose) vs OPTION B (alternative) → WHY
"""

    # Sonnet for studying — extraction doesn't need flagship reasoning
    study_model = os.environ.get("LEARN_STUDY_MODEL", "sonnet")
    response = call_llm(prompt, max_tokens=4000, model=study_model)

    return Knowledge(
        role=role_name,
        source=source_info,
        content=response,
        studied_at=datetime.now().isoformat(),
    )


# --- Step 4: STORE ---


def store(knowledge: Knowledge, roles_dir: Optional[Path] = None) -> Path:
    """Save knowledge as a structured markdown file."""
    if roles_dir is None:
        roles_dir = ROLES_DIR

    role_dir = roles_dir / knowledge.role / "knowledge"
    role_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{slug(knowledge.source.get('url_or_path', knowledge.source['name']))}.md"
    filepath = role_dir / filename

    content = f"""---
source: {knowledge.source.get('url_or_path', '')}
type: {knowledge.source['type']}
role: {knowledge.role}
studied_at: {knowledge.studied_at}
---

{knowledge.content}
"""
    filepath.write_text(content)

    # Update sources.json
    sources_file = roles_dir / knowledge.role / "sources.json"
    sources = []
    if sources_file.exists():
        try:
            sources = json.loads(sources_file.read_text())
        except (json.JSONDecodeError, TypeError):
            sources = []

    sources.append({
        "name": knowledge.source["name"],
        "url": knowledge.source.get("url_or_path", ""),
        "type": knowledge.source["type"],
        "studied_at": knowledge.studied_at,
        "knowledge_file": filename,
    })
    sources_file.write_text(json.dumps(sources, indent=2))

    return filepath


# --- Step 5: SYNTHESIZE ---


def synthesize(role_name: str, roles_dir: Optional[Path] = None) -> Path:
    """Merge all knowledge files for a role into _synthesis.md."""
    if roles_dir is None:
        roles_dir = ROLES_DIR

    knowledge_dir = roles_dir / role_name / "knowledge"
    if not knowledge_dir.is_dir():
        raise ValueError(f"No knowledge files for role '{role_name}'")

    knowledge_files = sorted(knowledge_dir.glob("*.md"))
    knowledge_files = [f for f in knowledge_files if f.name != "_synthesis.md"]

    if not knowledge_files:
        raise ValueError(f"No knowledge files for role '{role_name}'")

    # Load role definition
    role_md = roles_dir / role_name / "role.md"
    role_def = _parse_role_frontmatter(role_md) if role_md.is_file() else {}
    scope = role_def.get("scope", role_name)
    not_scope = role_def.get("not_scope", "")

    # Load all knowledge
    all_knowledge = ""
    for f in knowledge_files:
        all_knowledge += f"\n\n--- SOURCE: {f.stem} ---\n\n"
        all_knowledge += f.read_text()

    prompt = f"""You are synthesizing knowledge for the {role_name} role.
This role's scope: {scope}
Not this role's concern: {not_scope}

Below is knowledge extracted from {len(knowledge_files)} open-source projects.
Merge them into a single, unified document. Be OBJECTIVE — describe patterns
and approaches found, don't judge good vs bad. The human will review and
decide what to keep for this role.

RULES:
- Deduplicate — if multiple sources use the same pattern, note frequency
- Be specific — include actual code patterns, not just descriptions
- For common problems: show how different repos solve them (compare approaches)
- Organize by category, not by source
- Note which repos use which approach (provenance)
- Keep it under 3000 tokens — this will be loaded at runtime
- Mark everything as DRAFT — human review required

SOURCES:
{all_knowledge}

OUTPUT FORMAT:

## [DRAFT — HUMAN REVIEW REQUIRED]

## Role Summary
[2-3 sentences: what this role covers based on studied repos]

## Patterns Found (ranked by frequency across repos)
[Pattern → which repos use it → concrete code example]

## How Problems Are Solved
[PROBLEM → APPROACH (with code) → which repos do this]

## Architecture Decisions Seen
[DECISION → what repos chose → tradeoffs noted]

## Testing Approaches
[How repos test this role's concerns]

## Deployment & Production
[How repos handle deployment, monitoring, error recovery]

## Open Questions (for reviewer)
[Conflicting approaches found — reviewer should decide which to adopt]
"""

    synth_model = os.environ.get("LEARN_SYNTH_MODEL", "fable")
    synthesis = call_llm(prompt, max_tokens=4000, model=synth_model)

    output_path = knowledge_dir / "_synthesis.md"
    output_path.write_text(f"""---
role: {role_name}
sources: {len(knowledge_files)}
synthesized_at: {datetime.now().isoformat()}
---

{synthesis}
""")

    return output_path


# --- Health Check ---


def filter_knowledge(
    role_name: str,
    roles_dir: Optional[Path] = None,
) -> Path:
    """Filter synthesized knowledge — remove opinions, keep only objective
    patterns with provenance. Produces _synthesis_filtered.md for human review.

    Run after bootstrap: python learn.py --filter backend
    """
    if roles_dir is None:
        roles_dir = ROLES_DIR

    synthesis_path = roles_dir / role_name / "knowledge" / "_synthesis.md"
    if not synthesis_path.is_file():
        raise ValueError(f"No _synthesis.md for role '{role_name}' — run bootstrap first")

    role_md = roles_dir / role_name / "role.md"
    role_def = _parse_role_frontmatter(role_md) if role_md.is_file() else {}
    scope = role_def.get("scope", role_name)

    content = synthesis_path.read_text()

    prompt = f"""You are filtering knowledge for the {role_name} role (scope: {scope}).

Below is synthesized knowledge from multiple open-source repos. Your job is
to FILTER it objectively:

KEEP:
- Factual patterns with concrete code examples
- Approaches that multiple repos independently use (proven by frequency)
- Tradeoff descriptions that present both sides neutrally
- Specific library/tool recommendations with reasoning

REMOVE:
- Subjective judgments ("this is the best way", "you should always")
- Anti-patterns without the correct alternative shown
- Vague advice without concrete code ("use proper error handling")
- Opinions disguised as facts
- Anything that assumes a specific tech stack without stating it

REWRITE to be objective:
- "Always use X" → "X is used by 3/5 repos studied because..."
- "Bad practice" → "Alternative approach: ..."
- "Best practice" → "Common pattern (seen in N repos): ..."

Add a section at the end: "## Needs Human Decision" for anything where
repos disagree and there's no clear majority.

INPUT:
{content}

Output the filtered version. Keep the same structure, just clean the content.
"""

    filter_model = os.environ.get("LEARN_FILTER_MODEL", "fable")
    filtered = call_llm(prompt, max_tokens=4000, model=filter_model)

    output_path = roles_dir / role_name / "knowledge" / "_synthesis_filtered.md"
    output_path.write_text(f"""---
role: {role_name}
filtered_at: {datetime.now().isoformat()}
status: DRAFT — human review required
---

{filtered}
""")

    return output_path


def check_role_health(
    role_name: str,
    roles_dir: Optional[Path] = None,
) -> RoleHealthReport:
    """Check knowledge freshness and completeness for a role."""
    if roles_dir is None:
        roles_dir = ROLES_DIR

    report = RoleHealthReport(role=role_name)

    synthesis_path = roles_dir / role_name / "knowledge" / "_synthesis.md"
    if not synthesis_path.is_file():
        report.add_gap("NO_KNOWLEDGE", f"No _synthesis.md for {role_name}")
        return report

    # Check freshness
    import time
    age_days = (time.time() - synthesis_path.stat().st_mtime) / 86400
    if age_days > 90:
        report.add_gap("STALE", f"Knowledge is {int(age_days)} days old")

    # Check completeness
    content = synthesis_path.read_text().lower()
    required_sections = ["advisory", "anti_patterns", "quality_checks", "bug_fixes"]
    for section in required_sections:
        # Check for section header (flexible matching)
        section_pattern = section.replace("_", "[ _-]")
        if not re.search(section_pattern, content):
            report.add_gap("INCOMPLETE", f"Missing section: {section}")

    return report


# --- CLI ---


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Role knowledge learning — fetch, study, store, synthesize",
    )
    parser.add_argument("--role", required=True, help="Role name or 'all'")

    source = parser.add_mutually_exclusive_group()
    source.add_argument("--repo", help="Git repo URL")
    source.add_argument("--url", help="Blog/docs URL")
    source.add_argument("--path", help="Local directory path")
    source.add_argument("--paper", help="Academic paper URL (PDF)")

    parser.add_argument("--synthesize", action="store_true",
                        help="Merge all knowledge into _synthesis.md")
    parser.add_argument("--filter", action="store_true",
                        help="Filter synthesis — remove opinions, keep objective patterns")
    parser.add_argument("--health", action="store_true",
                        help="Check knowledge freshness and completeness")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show prompts without calling LLM")
    parser.add_argument("--cache-dir", default=".learn-cache",
                        help="Cache directory for fetched resources")

    args = parser.parse_args()

    if args.health:
        report = check_role_health(args.role)
        print(report.to_text())
        return 0

    if args.filter:
        roles_to_filter = []
        if args.role == "all":
            for d in ROLES_DIR.iterdir():
                if d.is_dir() and (d / "knowledge" / "_synthesis.md").is_file():
                    roles_to_filter.append(d.name)
        else:
            roles_to_filter = [args.role]

        for role in roles_to_filter:
            try:
                result = filter_knowledge(role)
                print(f"Filtered {role} → {result}")
            except ValueError as exc:
                print(f"Skip {role}: {exc}", file=sys.stderr)
        return 0

    if args.synthesize:
        try:
            result = synthesize(args.role)
            print(f"Synthesized → {result}")
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        return 0

    # Determine source
    if args.repo:
        source_type, source_val = "repo", args.repo
    elif args.url:
        source_type, source_val = "url", args.url
    elif args.path:
        source_type, source_val = "path", args.path
    elif args.paper:
        source_type, source_val = "paper", args.paper
    else:
        parser.error("Provide --repo, --url, --path, or --paper")
        return 1

    # Determine roles
    if args.role == "all":
        role_dirs = [d for d in ROLES_DIR.iterdir()
                     if d.is_dir() and (d / "role.md").is_file()]
        roles = [d.name for d in role_dirs]
    else:
        roles = [args.role]

    # 1. Fetch
    print(f"Fetching {source_type}: {source_val}")
    fetched = fetch(source_type, source_val, Path(args.cache_dir))
    print(f"  → fetched to {fetched.path}")

    # 2. Extract
    print("Extracting key content...")
    if fetched.source_type in ("repo", "path"):
        extracted = extract_repo(fetched.path)
    else:
        extracted = extract_article(fetched.path)
    print(f"  → {len(extracted.files)} files, {len(extracted.to_text())} chars")

    # 3. Study + Store per role
    for role in roles:
        print(f"Studying as {role}...")
        source_info = {
            "name": slug(source_val),
            "url_or_path": source_val,
            "type": source_type,
        }

        if args.dry_run:
            print(f"  [DRY RUN] Would send {len(extracted.to_text())} chars to LLM")
            continue

        knowledge = study(role, extracted, source_info)
        path = store(knowledge)
        print(f"  → saved to {path}")

    if not args.dry_run:
        print(f"\nDone. Run --synthesize {roles[0]} to merge into _synthesis.md")

    return 0


if __name__ == "__main__":
    sys.exit(main())
