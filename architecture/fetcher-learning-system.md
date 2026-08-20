# Architecture: Fetcher / Learning System

> The core of the role system — how roles learn from any resource
> One Python script that fetches, studies, and stores knowledge
> Date: 2026-08-16

## What This Is

A single script: `roles/learn.py`

It takes a resource (repo URL, blog URL, docs site, PDF, local codebase) and a role name, studies it using Python heuristics + LLM, and produces structured knowledge that the role can use at runtime.

```bash
# Usage examples:
python roles/learn.py --role backend --repo https://github.com/nestjs/nest
python roles/learn.py --role frontend --url https://react.dev/blog/2026/03/react-20
python roles/learn.py --role security --url https://owasp.org/Top10/
python roles/learn.py --role backend --path /Users/me/projects/my-legacy-app
python roles/learn.py --role dba --paper https://arxiv.org/abs/2401.12345
python roles/learn.py --role all --repo https://github.com/calcom/cal.com  # all roles study it
python roles/learn.py --synthesize backend  # merge all learned resources into _synthesis.md
```

## How It Works

```
┌──────────────────────────────────────────────────────┐
│                     learn.py                          │
│                                                      │
│  Input: --role <name> --repo|--url|--path|--paper    │
│                                                      │
│  1. FETCH — get the resource (Python, no LLM)        │
│     ├─ repo: git clone/fetch                         │
│     ├─ url: HTTP GET + html→markdown conversion      │
│     ├─ path: read local files                        │
│     └─ paper: download PDF, extract text             │
│                                                      │
│  2. EXTRACT — pull out relevant content (Python)     │
│     ├─ repo: file tree, deps, key files (heuristic)  │
│     ├─ url: main content (strip nav/ads/chrome)      │
│     ├─ path: same as repo                            │
│     └─ paper: abstract, methodology, results         │
│                                                      │
│  3. STUDY — ask LLM structured questions (LLM)      │
│     ├─ Load role definition (what this role cares about) │
│     ├─ Build prompt from role.md + extracted content  │
│     ├─ Ask role-specific questions                    │
│     └─ Get structured answers                        │
│                                                      │
│  4. STORE — save as structured knowledge (Python)    │
│     ├─ roles/{role}/knowledge/{source-name}.md       │
│     └─ Append to roles/{role}/sources.json           │
│                                                      │
│  5. SYNTHESIZE (optional, --synthesize flag)         │
│     ├─ Merge all knowledge files for this role       │
│     ├─ Deduplicate, rank by frequency, resolve conflicts │
│     └─ Output: roles/{role}/knowledge/_synthesis.md  │
└──────────────────────────────────────────────────────┘
```

## Step 1: FETCH (Python only, no LLM)

```python
def fetch(source_type: str, source: str, cache_dir: Path) -> FetchResult:
    """Fetch any resource. Returns local path to content."""

    if source_type == "repo":
        # git clone or git pull if already cached
        repo_dir = cache_dir / slug(source)
        if repo_dir.exists():
            run(["git", "-C", str(repo_dir), "pull", "--ff-only"])
        else:
            run(["git", "clone", "--depth", "1", source, str(repo_dir)])
        return FetchResult(type="repo", path=repo_dir)

    elif source_type == "url":
        # HTTP GET, convert HTML to markdown
        response = httpx.get(source, follow_redirects=True, timeout=30)
        markdown = html_to_markdown(response.text)  # strip nav, ads, chrome
        save_path = cache_dir / f"{slug(source)}.md"
        save_path.write_text(markdown)
        return FetchResult(type="article", path=save_path)

    elif source_type == "path":
        # Local directory — just validate it exists
        local = Path(source)
        if not local.is_dir():
            raise ValueError(f"Path {source} is not a directory")
        return FetchResult(type="repo", path=local)

    elif source_type == "paper":
        # Download PDF, extract text
        response = httpx.get(source, follow_redirects=True, timeout=60)
        pdf_path = cache_dir / f"{slug(source)}.pdf"
        pdf_path.write_bytes(response.content)
        text = extract_pdf_text(pdf_path)  # pdfplumber or pymupdf
        md_path = cache_dir / f"{slug(source)}.md"
        md_path.write_text(text)
        return FetchResult(type="paper", path=md_path)
```

**Dependencies (Python stdlib + 2-3 packages):**
- `httpx` — HTTP client (or `requests`)
- `markdownify` — HTML to markdown
- `pdfplumber` or `pymupdf` — PDF text extraction
- `git` — CLI (already available)

No heavy dependencies. No special environment needed. Works everywhere.

## Step 2: EXTRACT (Python heuristics, no LLM)

For repos, extract the files that matter most. Don't send the entire repo to LLM — that's wasteful.

```python
def extract_repo(repo_dir: Path) -> ExtractResult:
    """Extract key files from a repo using heuristics."""

    result = ExtractResult()

    # 1. Project metadata (always useful)
    result.add_if_exists(repo_dir / "package.json")
    result.add_if_exists(repo_dir / "pyproject.toml")
    result.add_if_exists(repo_dir / "Cargo.toml")
    result.add_if_exists(repo_dir / "go.mod")
    result.add_if_exists(repo_dir / "build.gradle")
    result.add_if_exists(repo_dir / "Podfile")

    # 2. File tree (structure tells a lot)
    result.file_tree = generate_tree(repo_dir, max_depth=3, ignore=[
        "node_modules", ".git", "dist", "build", "__pycache__", ".next"
    ])

    # 3. Entry points (where the app starts)
    for pattern in ["src/index.*", "src/main.*", "src/app.*", "server.*",
                     "app.*", "main.*", "index.*", "cmd/main.*"]:
        result.add_glob(repo_dir, pattern)

    # 4. Config files (how it's configured)
    for pattern in ["*.config.*", ".env.example", "docker-compose.*",
                     "Dockerfile", "tsconfig.json", "next.config.*"]:
        result.add_glob(repo_dir, pattern)

    # 5. Route/API definitions (what it exposes)
    for pattern in ["**/routes/**", "**/api/**", "**/controllers/**",
                     "**/endpoints/**", "**/handlers/**"]:
        result.add_glob(repo_dir, pattern, max_files=10)

    # 6. Models/schemas (data structure)
    for pattern in ["**/models/**", "**/schema*", "**/entities/**",
                     "**/types/**", "prisma/schema.prisma", "**/migrations/**"]:
        result.add_glob(repo_dir, pattern, max_files=10)

    # 7. Tests (how they test)
    for pattern in ["**/__tests__/**", "**/test/**", "**/tests/**",
                     "**/*.test.*", "**/*.spec.*"]:
        result.add_glob(repo_dir, pattern, max_files=5)

    # 8. README (project overview)
    result.add_if_exists(repo_dir / "README.md")

    # Cap total content at ~8K tokens worth of text
    result.truncate(max_chars=32000)

    return result


def extract_article(article_path: Path) -> ExtractResult:
    """Extract main content from a blog/docs article."""
    content = article_path.read_text()
    # Already markdown from fetch step — just cap length
    result = ExtractResult()
    result.add_content("article", content[:32000])
    return result


def extract_paper(paper_path: Path) -> ExtractResult:
    """Extract key sections from an academic paper."""
    content = paper_path.read_text()
    result = ExtractResult()
    # Try to find abstract, introduction, methodology, results, conclusion
    for section in ["abstract", "introduction", "method", "result", "conclusion"]:
        extracted = find_section(content, section)
        if extracted:
            result.add_content(section, extracted)
    result.truncate(max_chars=32000)
    return result
```

**Key principle: cap at ~8K tokens.** The LLM doesn't need the whole repo — it needs the patterns, structure, and key code. Heuristics select what matters.

## Step 3: STUDY (LLM — this is where cost happens)

The LLM is asked **role-specific questions** about the extracted content. Different roles study the same repo differently.

```python
def study(role_name: str, extracted: ExtractResult, source_info: dict) -> Knowledge:
    """Ask the LLM to study extracted content through the lens of a specific role."""

    role_def = load_role_definition(role_name)

    prompt = f"""You are studying this codebase/resource as a {role_def['name']}.
Your expertise: {role_def['scope']}
Not your concern: {role_def['not_scope']}

SOURCE: {source_info['name']} ({source_info['type']})
{source_info.get('description', '')}

EXTRACTED CONTENT:
{extracted.to_text()}

Answer these questions as structured markdown. Be specific — cite file paths, function names, line patterns. Include FIXES for every anti-pattern you identify.

## 1. Patterns
What design patterns does this codebase use that are relevant to your role?
List each with a concrete example from the code.

## 2. Conventions
What naming, formatting, error handling, or structural conventions does it follow?

## 3. Anti-Patterns (with fixes)
What mistakes or anti-patterns do you see? For EACH one, provide:
- What's wrong
- Why it's wrong
- The fix (actual code or approach)

## 4. Architecture Decisions
What architectural choices were made? What tradeoffs?

## 5. Dependencies & Tools
What libraries/tools are used and why? Any notable choices?

## 6. Testing Approach
How is it tested? What's covered, what's not?

## 7. Key Learnings
What would you take from this codebase into your next project?
Focus on patterns that are REUSABLE, not repo-specific.

## 8. Bug Fix Patterns
Common bugs in this type of codebase and how to fix them.
Format: SYMPTOM → CAUSE → FIX (with code)
"""

    response = call_llm(prompt, max_tokens=4000)

    return Knowledge(
        role=role_name,
        source=source_info,
        content=response,
        studied_at=datetime.now().isoformat(),
    )
```

**Cost per study:** ~8K tokens in + ~4K tokens out = ~12K tokens total. At Sonnet pricing (~$3/Mtok in, $15/Mtok out): **~$0.08 per resource studied.**

**Model choice:** Use Sonnet for studying (mid-tier — good enough for extraction, not worth Opus). Use Opus only for synthesis (merging requires judgment).

## Step 4: STORE (Python only)

```python
def store(knowledge: Knowledge, roles_dir: Path) -> Path:
    """Save knowledge as a structured markdown file."""

    role_dir = roles_dir / knowledge.role / "knowledge"
    role_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{slug(knowledge.source['name'])}.md"
    filepath = role_dir / filename

    # Write knowledge file
    content = f"""---
source: {knowledge.source['url_or_path']}
type: {knowledge.source['type']}
role: {knowledge.role}
studied_at: {knowledge.studied_at}
---

{knowledge.content}
"""
    filepath.write_text(content)

    # Update sources.json (index of all studied resources)
    sources_file = roles_dir / knowledge.role / "sources.json"
    sources = json.loads(sources_file.read_text()) if sources_file.exists() else []
    sources.append({
        "name": knowledge.source['name'],
        "url": knowledge.source.get('url_or_path', ''),
        "type": knowledge.source['type'],
        "studied_at": knowledge.studied_at,
        "knowledge_file": filename,
    })
    sources_file.write_text(json.dumps(sources, indent=2))

    return filepath
```

**Output structure:**
```
roles/backend/
  role.md              # role definition
  sources.json         # index of everything this role has studied
  knowledge/
    nestjs-nest.md     # studied from nestjs/nest repo
    fastapi-docs.md    # studied from fastapi docs URL
    caching-blog.md    # studied from a caching patterns blog post
    _synthesis.md      # merged knowledge (runtime file)
```

## Step 5: SYNTHESIZE (LLM — Opus for judgment)

Merges all individual knowledge files into one `_synthesis.md` that the role uses at runtime.

```python
def synthesize(role_name: str, roles_dir: Path) -> Path:
    """Merge all knowledge files for a role into _synthesis.md"""

    role_dir = roles_dir / role_name / "knowledge"
    knowledge_files = sorted(role_dir.glob("*.md"))
    knowledge_files = [f for f in knowledge_files if f.name != "_synthesis.md"]

    if not knowledge_files:
        raise ValueError(f"No knowledge files for role {role_name}")

    # Load all knowledge
    all_knowledge = ""
    for f in knowledge_files:
        all_knowledge += f"\n\n--- SOURCE: {f.stem} ---\n\n"
        all_knowledge += f.read_text()

    role_def = load_role_definition(role_name)

    prompt = f"""You are synthesizing knowledge for the {role_def['name']} role.
This role's scope: {role_def['scope']}

Below is knowledge extracted from {len(knowledge_files)} sources.
Merge them into a single, unified knowledge document.

RULES:
- Deduplicate — if multiple sources say the same thing, keep the best version
- Rank by frequency — patterns seen in multiple repos are more important
- Resolve conflicts — if sources disagree, note both approaches with tradeoffs
- Be specific — include actual code patterns, not just descriptions
- Every anti-pattern MUST have a fix (actual code)
- Organize by category, not by source
- Keep it under 3000 tokens — this will be loaded at runtime

SOURCES:
{all_knowledge}

OUTPUT FORMAT:

## Advisory Context
[2-3 sentences: what this role brings to a project]

## Patterns (use these)
[Ranked by how often they appear across sources]

## Anti-Patterns + Fixes
[Each: what's wrong → why → fix with code]

## Architecture Decisions
[Common tradeoffs this role encounters]

## Quality Checks
[Checklist items for /precommit evaluation]

## Bug Fix Patterns
[SYMPTOM → CAUSE → FIX with code, ranked by frequency]
"""

    # Use Opus for synthesis — judgment-heavy task
    synthesis = call_llm(prompt, max_tokens=4000, model="opus")

    output_path = role_dir / "_synthesis.md"
    output_path.write_text(f"""---
role: {role_name}
sources: {len(knowledge_files)}
synthesized_at: {datetime.now().isoformat()}
---

{synthesis}
""")

    return output_path
```

## The Complete Script: `learn.py`

```python
#!/usr/bin/env python3
"""Role knowledge acquisition — fetch, study, store, synthesize.

Usage:
  python learn.py --role backend --repo https://github.com/nestjs/nest
  python learn.py --role frontend --url https://react.dev/blog/2026/react-20
  python learn.py --role security --paper https://arxiv.org/abs/2401.12345
  python learn.py --role backend --path /path/to/local/project
  python learn.py --role all --repo https://github.com/calcom/cal.com
  python learn.py --synthesize backend
  python learn.py --health backend       # check knowledge freshness
"""

import argparse

def main():
    parser = argparse.ArgumentParser(description="Role knowledge learning")
    parser.add_argument("--role", required=True, help="Role name or 'all'")

    # Source types (mutually exclusive)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--repo", help="Git repo URL")
    source.add_argument("--url", help="Blog/docs URL")
    source.add_argument("--path", help="Local directory path")
    source.add_argument("--paper", help="Academic paper URL (PDF)")

    # Actions
    parser.add_argument("--synthesize", action="store_true",
                        help="Merge all knowledge into _synthesis.md")
    parser.add_argument("--health", action="store_true",
                        help="Check knowledge freshness and completeness")

    # Options
    parser.add_argument("--model", default="sonnet",
                        help="LLM model for study (default: sonnet)")
    parser.add_argument("--cache-dir", default=".learn-cache",
                        help="Cache directory for fetched resources")

    args = parser.parse_args()

    if args.synthesize:
        synthesize(args.role, ROLES_DIR)
        return

    if args.health:
        report = check_role_health(args.role, ROLES_DIR)
        print(report.to_text())
        return

    # Determine source type
    if args.repo:
        source_type, source = "repo", args.repo
    elif args.url:
        source_type, source = "url", args.url
    elif args.path:
        source_type, source = "path", args.path
    elif args.paper:
        source_type, source = "paper", args.paper
    else:
        parser.error("Provide --repo, --url, --path, or --paper")

    # Determine roles to study for
    roles = get_all_role_names() if args.role == "all" else [args.role]

    # 1. FETCH (once, regardless of how many roles)
    fetched = fetch(source_type, source, Path(args.cache_dir))

    # 2. EXTRACT (once)
    extracted = extract(fetched)

    # 3. STUDY + STORE (per role)
    for role in roles:
        print(f"Studying as {role}...")
        source_info = {
            "name": slug(source),
            "url_or_path": source,
            "type": source_type,
        }
        knowledge = study(role, extracted, source_info)
        path = store(knowledge, ROLES_DIR)
        print(f"  → saved to {path}")

    print(f"\nDone. Run --synthesize {roles[0]} to merge into _synthesis.md")
```

## Cost Analysis

| Action | LLM Model | Tokens | Cost |
|--------|-----------|--------|------|
| Study 1 resource for 1 role | Sonnet | ~12K | ~$0.08 |
| Study 1 resource for all 19 roles | Sonnet | ~228K | ~$1.50 |
| Study 5 repos for 1 role | Sonnet | ~60K | ~$0.40 |
| Synthesize 1 role | Opus | ~20K | ~$1.50 |
| Full setup: 6 starter roles × 5 repos each | Sonnet + Opus | ~450K | ~$12 |
| Full setup: all 19 roles × 5 repos each | Sonnet + Opus | ~1.4M | ~$40 |

## What This Enables

```bash
# A role needs to learn about a new framework:
python learn.py --role frontend --url https://svelte.dev/docs/svelte/overview

# Study a competitor's open-source project:
python learn.py --role all --repo https://github.com/calcom/cal.com

# Learn from an academic paper on caching:
python learn.py --role backend --paper https://arxiv.org/abs/2401.12345

# Study the user's own legacy codebase before modernizing:
python learn.py --role all --path /path/to/legacy/app

# Research Engineer finds a great blog post:
python learn.py --role backend --url https://stripe.com/blog/rate-limiters

# After studying multiple sources, merge into usable knowledge:
python learn.py --synthesize backend
```

## Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | Single script (`learn.py`), not multiple modules | User: "just have one script in python that could work for anyone" |
| D2 | 4 source types: repo, url, path, paper | Covers all real-world knowledge sources |
| D3 | Fetch once, study per role | Same repo studied by different roles → different knowledge extracted |
| D4 | Sonnet for studying, Opus for synthesis | Study is extraction (mid-tier fine). Synthesis is judgment (needs Opus) |
| D5 | Cap extraction at ~8K tokens | LLM doesn't need entire repo — heuristics select what matters |
| D6 | Structured questions per role | Role's `scope` and `not_scope` focus the LLM on relevant aspects |
| D7 | `--role all` studies for every role | One fetch, 19 studies — when a resource is broadly useful |
| D8 | `_synthesis.md` capped at ~3K tokens | This is loaded at runtime — must be compact |
| D9 | `sources.json` tracks everything studied | Audit trail + freshness checking |
| D10 | `--health` flag for on-demand checks | Not per-session, as user specified |
