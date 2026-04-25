# Agent Toolkit

Reusable Claude Code skills for planning, building, and evaluating software projects. Works in any repo, any language.

## Skills

| Skill | What It Does |
|-------|-------------|
| `/requirements` | Gather requirements through structured questionnaire. Auto-scales: quick feature -> standard app -> full system design. Drafts early, then lets you explore areas on demand. Re-enter anytime to add or revise. |
| `/architecture` | Design system architecture with waterfall decision flow. Presents options with trade-offs -- you decide. Backtracking and re-entry supported. Always includes a local/cheap option. |
| `/implementation` | Build features with TDD. Walking skeleton first, then feature slabs. Security stitched in, not bolted on. Follows upstream decisions -- never re-decides. |
| `/test` | Generate comprehensive tests for existing code. Every method, every button, every flow. Realistic data, not placeholders. Unit, component, integration, and regression tests. Coverage analysis and bug detection. |
| `/status` | Project dashboard. Reads all docs and reports, shows what's done, what's in progress, what's left. Suggests next action. Run anytime mid-conversation or when returning to a project. |
| `/evaluate` | Grade agent output against the original prompt. Evidence-based scorecard with file:line references. Run after any skill or agent work. |
| `/updater` | Audits toolkit for relevance, security, and standards compliance. Checks references, sub-skills, guardrails, and best practices. |

## Modular Architecture

Each skill is a **lean orchestrator** (under 200 lines) that reads **sub-skill files on demand**. Sub-skills only load when the user explores that area -- no context wasted on unused sections.

```
skills/requirements/
  SKILL.md (195)        <- orchestrator: intake, mode, draft, explore menu
  frontend.md           <- UI/UX: screens, flows, design system, wireframes
  ml.md                 <- ML/AI: algorithms, data, accuracy
  llm.md                <- LLM: provider selection, free vs paid
  testing.md            <- testing level, types, CI/CD
  references/
    llm-providers.md    <- provider tables (loaded when needed)
    ml-algorithms.md    <- algorithm families (loaded when needed)
    template.md         <- output document template

skills/architecture/
  SKILL.md (136)        <- orchestrator: context, quick arch, explore menu
  frontend.md           <- 8 decisions: framework, components, state, styling...
  backend.md            <- data, API, code structure, extensibility
  ml.md                 <- model serving, pipelines, evaluation
  llm.md                <- provider arch, prompts, context, safety
  security.md           <- auth, authorization, OWASP
  system.md             <- scaling, observability, team workflow
  testing.md            <- pyramid, frameworks, CI pipeline

skills/implementation/
  SKILL.md (172)        <- orchestrator: context, sequence, slab cycle
  skeleton.md           <- walking skeleton (thin end-to-end path)
  backend.md            <- backend TDD patterns
  frontend.md           <- frontend TDD patterns
  security.md           <- stitched security (attack tests first)
  ml.md                 <- ML implementation
  llm.md                <- LLM integration
  pipeline.md           <- CI/CD
```

## How It Works

### Draft Early, Deepen on Demand

Skills don't interrogate you. After a quick intake, you get a **draft document immediately**. Then you choose which areas to explore:

```
/requirements recipe-finder

-> Quick intake: What? Who? Core feature? Needs UI? ML? etc.
-> Draft saved to requirements/recipe-finder.md

"Here's your draft. Explore any area, or say 'done':"
  [~] UI/UX -- screens, flows, design system, accessibility
  [~] ML/AI -- algorithms, models, data, accuracy
  [~] LLM Strategy -- provider selection, free vs paid, use cases
  [~] Testing -- level, test types, CI/CD, regression
  [~] Non-Functional -- performance, availability, security
  [-] Scale Estimation -- not applicable (personal app)

> "Let's do UI/UX"
-> reads frontend.md, explores UI, updates draft
  [x] UI/UX -- done
  [~] Testing -- not yet explored
  ...
> "done"
-> finalizes document
```

### Adding Features to Existing Apps

When you pick "feature for an existing app", the skills shift to **Feature Mode** -- a faster path that respects what's already built:

```
/requirements add-search

-> Scans your codebase ONCE, builds a Codebase Index:
   Tech stack: Next.js 14, PostgreSQL/Prisma, Tailwind
   Structure: src/app/, src/components/, src/lib/
   Conventions: REST routes, camelCase, vitest
   Existing: auth, user model, basic UI layout

-> Asks only about what's NEW (skips what exists)
-> Index reused by /architecture and /implementation (no re-scanning)
```

`/architecture` reads the index and designs how the feature **fits** -- integration points, new components, migrations. No full redesign.

`/implementation` skips the walking skeleton (your app IS the skeleton) and goes straight to feature slabs following your existing conventions.

### Walking Skeleton + Feature Slabs (Greenfield)

For new projects, implementation builds a **thin end-to-end slice first** (skeleton), then adds features one slab at a time:

```
Phase 1: Walking Skeleton (no TDD -- just get it running)
  1 table + 1 endpoint + 1 page = proves architecture works

Phase 2: Feature Slabs (TDD for business logic)
  Slab 1: Auth system (Backend + Security)
  Slab 2: Recipe CRUD (Backend + Frontend)
  Slab 3: AI matching (Backend + LLM + Security)
  ...
  One commit per slab. All tests passing.
```

### Mid-Conversation Updates

Changed your mind? No need to restart. Say "actually I need ML too" while in `/architecture` -- the upstream doc gets updated in place, and the current skill continues with the new context.

### Re-Entry

Run `/requirements recipe-finder` again later? It picks up the existing doc:
```
"I found existing requirements. Here's the completeness:"
  [x] Functional, [x] UI/UX, [~] Testing, [ ] ML/AI
  -> Continue | Revisit | Start fresh
```

Same for `/architecture` and `/implementation` -- shows progress and lets you continue.

## End-to-End Example

Building a **recipe finder app** with AI-powered ingredient matching:

```
recipe-finder/
+-- requirements/
|   +-- recipe-finder.md          <- generated by /requirements
|   +-- wireframes/
|       +-- home.html             <- optional HTML wireframes
+-- architecture/
|   +-- recipe-finder.md          <- generated by /architecture
+-- reports/
|   +-- requirements/
|   +-- architecture/
|   +-- implementation/
+-- backend/
|   +-- recipe_scraper.py         <- generated by /implementation
|   +-- recipe_scraper_test.py
+-- frontend/
    +-- RecipeSearch.tsx
```

**Step 1:** `/requirements recipe-finder`
```
Quick intake -> draft generated
-> explores: UI/UX (screens, design system), LLM strategy (Claude API)
-> skips: testing (defaults), scale (personal app)
-> generates requirements/recipe-finder.md
```

**Step 2:** `/architecture recipe-finder`
```
Reads requirements -> quick architecture: Python, React, SQLite, REST
-> goes deeper: Frontend architecture + LLM integration
-> generates architecture/recipe-finder.md
```

**Step 3:** `/implementation recipe-finder`
```
Reads both docs -> derives sequence:
  Skeleton -> Auth slab -> CRUD slab -> AI matching slab
-> TDD per slab, security stitched in, one commit per slab
```

**Step 4:** `/test recipe-finder`
```
Analyzes codebase -> coverage analysis:
  recipe_scraper.py: 8 methods, 3 tested, 5 untested
  RecipeSearch.tsx: 4 interactions, 0 tested
-> writes 47 tests with realistic data (real recipe names, real ingredients)
-> unit + component + integration + regression
-> finds 1 bug: search fails on unicode ingredient names
```

**Step 5 (optional):** `/evaluate`
```
Parses claims -> inspects code
  [PASS] search by ingredients: found in recipe_scraper.py:24
  [FAIL] save favorites: no favorites endpoint found
  Scorecard: 1/2 passed
```

## Sub-Agents

Skills spawn these for parallel research:

| Agent | Spawned By | Purpose |
|-------|-----------|---------|
| `functional-researcher` | requirements | How features work in other products |
| `scale-estimator` | requirements | Back-of-envelope math (QPS, storage, bandwidth) |
| `infrastructure-planner` | requirements | Servers, databases, caching, cost estimates |
| `tech-stack-advisor` | architecture | Tech options with trade-offs (never decides) |
| `pattern-advisor` | architecture | Design patterns for specific problems |
| `scale-advisor` | architecture | What changes at each scale level |
| `test-generator` | implementation | Generate tests for existing code |
| `code-reviewer` | implementation | Quality, security, and principles review |

## Guardrails

Every skill has safety limits. When hit: warns you, records it, continues with what it has.

**Universal (all skills):**
- No secrets in generated files -- uses env var placeholders
- No destructive operations without confirmation
- File safety check: size limit (1MB), allowed extensions (docs + images), path traversal blocked, prompt injection scanning
- No PII in generated files -- uses synthetic data
- Mid-conversation updates: change upstream decisions without restarting
- LLM data security: never sends secrets to external LLMs, warns before sending source code, marks data exit points

**Skill-specific:**

| Skill | Guardrail | Limit |
|-------|-----------|-------|
| `/requirements` | Max questions | 20 -- prioritizes core > ML > UI > testing |
| `/requirements` | ML data privacy | Flags PII in training data, compliance for regulated industries |
| `/architecture` | Backtrack limit | 2 per decision |
| `/architecture` | Max decisions | 20 per run |
| `/architecture` | Security decisions | Must reference OWASP |
| `/architecture` | LLM decisions | Must reference OWASP LLM Top 10 |
| `/implementation` | SQL injection | Never uses string concatenation |
| `/implementation` | Secret protection | Always uses environment variables |
| `/implementation` | File overwrite | Shows diff, asks before overwriting |
| `/evaluate` | Unverifiable claims | Always highlighted |
| `/evaluate` | Guardrail-aware | Doesn't penalize guardrail-limited output |
| `/updater` | No auto-updates | Reports only -- user approves changes |

## Reports

Skills generate progress reports in `reports/`:
- Created at start, updated progressively
- UUID-suffixed to avoid collisions
- Marked `completed` or `incomplete` with reason
- Previous reports linked automatically
- Implementation reports include slab sequence with progress tracking

## Coding Standards

`/implementation` enforces language-specific standards. `/evaluate` can check against them.

| Language | Based On |
|----------|----------|
| Python | PEP 8, Google Python Style Guide |
| TypeScript/React | Google TS Guide, Airbnb JS Guide |
| Java | Google Java Style Guide, Effective Java |
| Rust | Rust API Guidelines, Clippy lints |

## Install

```bash
git clone https://github.com/jvalin17/agent-toolkit.git
cd agent-toolkit
./install.sh
```

This does three things:
1. Symlinks skills to `~/.claude/skills/` and agents to `~/.claude/agents/`
2. Adds an **auto-update hook** to `~/.claude/settings.json` -- pulls latest before every skill invocation
3. Available globally in any Claude Code session

Auto-update: fast-forward only, fails silently offline, requires `jq` for install. Re-run `./install.sh` if you move the repo.

## Quick Start

```
/requirements my-feature        # gather requirements (draft + explore)
/architecture my-feature        # design architecture (quick + deep dive)
/implementation my-feature      # skeleton + feature slabs with TDD
/test my-feature                # comprehensive tests (every method, every button)
/status my-feature              # where am I? what's next?
/evaluate                       # grade the output (optional)
/updater                        # audit toolkit health
```

Skills read each other's output -- run in order for best results, or independently.
