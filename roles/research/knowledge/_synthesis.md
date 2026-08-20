---
role: research
sources: 5
synthesized_at: 2026-08-17T02:30:22.527268
---

## [DRAFT — HUMAN REVIEW REQUIRED]

## Role Summary
All 5 studied repos are **knowledge curation infrastructures**, not application codebases: curated lists (awesome-selfhosted, build-your-own-x), catalogs (free-programming-books), study guides (system-design-primer), and academic paper collections (papers-we-love). The research value is in how they organize, maintain, validate, and distribute knowledge at scale using Git/GitHub as the entire platform — patterns directly reusable for a research role's knowledge management.

## Patterns Found (ranked by frequency across repos)

### 1. Markdown-as-Database / Flat-File Catalog (5/5 repos)
All repos store structured knowledge in Markdown with implicit per-entry schemas, no database.

```markdown
# awesome-selfhosted:
[Name](url) - Description. ([Source](url), [License badge])

# build-your-own-x:
* [**{Language}**: _{Title}_]({URL})

# free-programming-books:
* [Book Title](URL) - Author Name
```
Consistency of the micro-format is the "schema enforcement" mechanism — human review catches deviations.

### 2. Taxonomy via Directory/Section Structure (5/5)
- **Filesystem-as-ontology** (papers-we-love, system-design-primer, free-programming-books): topic = directory, each with its own README index. `distributed_systems/README.md` + co-located PDFs.
- **Single-file with anchored ToC** (awesome-selfhosted, build-your-own-x): `#### Build your own \`Database\`` headers + GitHub auto-anchor navigation. ToC acts as the contributor contract (1:1 mapping to sections).
- Nested sub-taxonomy only where density justifies it (papers-we-love: `artificial_intelligence/judea_pearl/`).

### 3. GitHub as Complete Infrastructure (5/5)
Hosting, rendering, contribution pipeline (PRs), coordination (Issues), CI (Actions) — zero owned infrastructure. Issues used creatively: translation status tracking (system-design-primer, e.g., `issues/170` for Arabic), aggregated CI failure reporting (awesome-selfhosted, all failures → single pinned `/issues/1`).

### 4. Internationalization via File Proliferation (2/5, extensively)
- system-design-primer: `README-{locale}.md` at root (leverages GitHub auto-detection)
- free-programming-books: `{content-type}-{lang}.md` suffix pattern, underscore region codes (`pt_BR`, `fa_IR`); 30+ manually translated CODE_OF_CONDUCT files
- No i18n frameworks anywhere — each language file is self-contained.

### 5. Multi-Format Distribution from Single Source (3/5)
- awesome-selfhosted: data repo → HTML site (recommended) + Markdown (legacy)
- system-design-primer: README → EPUB (`generate-epub.sh` + `epub-metadata.yaml`, implies pandoc) + Anki `.apkg` flashcards
- free-programming-books: Markdown → Jekyll/GitHub Pages + separate search microsite

### 6. Solution/Contribution Templates (2/5)
- system-design-primer: `solutions/system_design/template/` — concrete copy-pasteable directory enforces structure by example, not documentation
- build-your-own-x: `ISSUE_TEMPLATE.md` standardizes link submissions

### 7. Badge-as-Dashboard (2/5)
awesome-selfhosted and free-programming-books embed shields.io/CI badges as public real-time health indicators (link checks, site uptime, Hacktoberfest stats).

## How Problems Are Solved

**PROBLEM: Link rot** (all repos face it; three distinct responses)
- awesome-selfhosted: automated CI (`check-dead-links.yml` in data repo) → single tracking issue + README badge
- papers-we-love: host PDFs in-repo when license permits, marked with `:scroll:` emoji; external links unvalidated
- build-your-own-x, free-programming-books: no visible automation — accept rot as tradeoff of zero maintenance

**PROBLEM: Staleness/abandonment detection**
- awesome-selfhosted only: dedicated `check-unmaintained-projects.yml` workflow, distinct from dead-link checks

**PROBLEM: Search over static Markdown**
- free-programming-books: decoupled search microsite, GET-based form embedded in README:
```html
<form action="https://ebookfoundation.github.io/free-programming-books-search">
  <input type="text" name="search" required placeholder="Search Book or Author"/>
</form>
```
- awesome-selfhosted: HTML site with better navigation, Markdown demoted to "legacy"
- papers-we-love, others: no search — offload to GitHub search + external aggregators (arXiv, alphaXiv, Lobste.rs)

**PROBLEM: Free vs. non-free / license-sensitive content**
- awesome-selfhosted: hard file split (`README.md` vs `non-free.md`) instead of inline tags
- papers-we-love: license-aware hosting policy — host or link based on copyright, emoji marker signals which

**PROBLEM: Learning reinforcement** (system-design-primer)
Three modalities from same content: prose README → worked solutions per directory → Anki `.apkg` spaced-repetition decks. Concept sections follow: definition → tradeoffs → when to use → sources.

**PROBLEM: RTL/bidirectional text in multilingual content** (free-programming-books)
Dedicated config-driven linter: `scripts/rtl_ltr_linter.py` + `rtl_ltr_linter_config.yml` — the one objectively automatable content check.

## Architecture Decisions Seen

| Decision | Approaches observed | Tradeoffs noted |
|---|---|---|
| Data/presentation split | awesome-selfhosted: separate `-data` repo generates HTML + MD outputs, CI runs on data repo | Independent CI & multi-format output vs. two-repo coordination overhead |
| Single file vs. multi-file | Single README (build-your-own-x, system-design-primer, awesome-selfhosted) vs. dir-per-topic (papers-we-love, free-programming-books) | Single file = landing-page discoverability; dirs = per-topic indexes, scales for binary assets |
| Monorepo for all topics/languages | 5/5 chose monorepo | One contribution surface; cost: PR noise, no per-topic watch granularity |
| Metadata richness | build-your-own-x: minimal (language+title+URL only) — explicitly rejects difficulty/stars/dates | Low contribution friction vs. no quality differentiation between 5-page post and 500-page book |
| Diagrams | system-design-primer: pre-rendered PNG + proprietary `.graffle` source vs. Mermaid/PlantUML | Universal rendering + EPUB compat; contributors can't edit source without macOS/OmniGraffle |
| Binary assets in git | system-design-primer commits `.apkg` Anki binaries | Directly importable, no build step; non-diffable |
| Funding | awesome-selfhosted: Liberapay (FOSS-aligned) vs. build-your-own-x: commercial banner (codecrafters.io funds maintenance) | Philosophy-consistent vs. sustainability via commercial sponsor; latter is a notable OSS funding model |
| Category taxonomy | build-your-own-x's 28 categories = crowd-validated consensus of "foundational systems worth rebuilding" — reusable classification framework | — |

## Testing Approaches
No traditional test suites anywhere. Quality mechanisms observed:
- **Automated content validation**: dead-link + unmaintained-project CI (awesome-selfhosted); RTL/LTR linter (free-programming-books)
- **Human review as the test layer**: PR review is the primary quality gate in all 5 repos
- **Structural enforcement by template**: template directory (system-design-primer), issue template (build-your-own-x)
- **Failure aggregation convention**: all CI failures → one pinned issue, avoiding tracker flooding (awesome-selfhosted)

## Deployment & Production
- **"Deployment" = GitHub rendering** for 3/5 repos (zero config)
- **GitHub Pages + Jekyll** (free-programming-books: `_config.yml`, `_includes/head-custom.html`)
- **Generated static HTML site from data repo** (awesome-selfhosted → awesome-selfhosted.net)
- **Monitoring**: passive shields.io/CI badges on README as public health dashboard (awesome-selfhosted, free-programming-books); no active alerting anywhere
- **Alternate channels**: EPUB export, Anki packages (system-design-primer); YouTube + Discord as out-of-band discussion layers (papers-we-love)
- **Continuous update model**: no formal releases/changelogs observed in any repo

## Open Questions (for reviewer)
1. **Link rot policy**: automate checking (awesome-selfhosted's CI approach) vs. accept rot (build-your-own-x) vs. host content locally (papers-we-love)? Each has different maintenance cost for our knowledge base.
2. **Metadata richness**: minimal schema (build-your-own-x) vs. rich annotations (papers-we-love READMEs)? Directly affects contribution friction vs. usefulness at retrieval time.
3. **Single-file vs. directory-per-topic**: depends on expected corpus size and whether binary assets (PDFs, diagrams) will be stored.
4. **Data/presentation split**: is a separate structured data source (awesome-selfhosted model) worth the overhead, or is Markdown-as-source sufficient?
5. **Naming consistency**: multiple repos show organic drift (snake_case vs kebab-case dirs in papers-we-love; hyphen/underscore mix in free-programming-books) — enforce a linter early or tolerate drift?
6. **Discussion layer**: in-repo (Issues/Discussions) vs. out-of-band (Discord/meetups, papers-we-love)? Affects discoverability of research conversations.
