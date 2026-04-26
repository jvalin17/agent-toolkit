# Agent Toolkit

Reusable Claude Code skills for planning, building, and shipping software projects. Works in any repo, any language.

## Install

```bash
git clone https://github.com/jvalin17/agent-toolkit.git
cd agent-toolkit
./install.sh
```

This does three things:
1. Symlinks skills to `~/.claude/skills/` and agents to `~/.claude/agents/`
2. Adds an auto-update hook — pulls latest before every skill invocation
3. Available globally in any Claude Code session

Requires `jq` for the auto-update hook (skips gracefully if missing).

## Skills

| Skill | What It Does |
|-------|-------------|
| `/requirements` | Gather and validate requirements. Drafts early, explore on demand. Auto-researches when you say "idk". |
| `/architecture` | Design architecture with trade-offs. User journey mandatory. Legal/ToS checks. Concurrency warnings. |
| `/implementation` | Build with TDD. Skeleton + slabs. Fix, refactor, and demo modes. Dependency weight audit. |
| `/reviewer` | Review code + write tests + smoke test + accessibility + dependency audit + UI validation. |
| `/setup` | Generate install scripts, Docker, Makefile, README. One-command setup, platform agnostic. |
| `/status` | Project dashboard. What's done, what's next. Reads all docs and reports. |
| `/evaluate` | Grade output against the original prompt. Run between any skills as checkpoint. |
| `/updater` | Audit toolkit health, freshness, security, standards compliance. |

## How It Works

### Shared Project State

All skills read and write `project-state.md` in your project root. This is the shared brain:
- Core intent (what the user actually wants)
- Parking lot with red flags (is the main goal being deferred?)
- Key decisions across all skills
- Feature status (works / placeholder / broken)
- Handoff summaries between skills

### Draft Early, Deepen on Demand

```
/requirements recipe-finder

-> Intake: What? How do you do this today? What exists? Core feature?
-> Draft saved immediately
-> Explore menu: UI/UX, ML/AI, LLM, Testing, Non-Functional, Scale
-> Pick what you want, skip the rest, come back anytime
```

### Adding Features to Existing Apps

```
/requirements add-search

-> Scans codebase ONCE via codestructure-analyzer agent
-> Builds Codebase Index (tech stack, structure, conventions)
-> Index reused by all downstream skills (no re-scanning)
-> /architecture designs how the feature fits (not a full redesign)
-> /implementation skips skeleton, goes straight to feature slab
```

### Walking Skeleton + Feature Slabs (Greenfield)

```
Phase 1: Walking Skeleton (no TDD -- scaffold)
  1 table + 1 endpoint + 1 page = architecture proved

Phase 2: Feature Slabs (TDD for logic, security stitched in)
  Slab 1: Auth (Backend + Security)
  Slab 2: Core CRUD (Backend + Frontend)
  Slab 3: AI features (Backend + LLM + Security)
  One commit per slab. All tests passing.
```

### Fix, Refactor, Demo Modes

```
/implementation fix login-bug     -> write failing test, fix, verify
/implementation refactor auth     -> refactor, all tests still pass
/implementation demo auto-apply   -> simulated data, validate UX first
```

### Review Everything

```
/reviewer recipe-finder

-> Code quality (SOLID/DRY, naming, structure)
-> Test coverage (writes missing tests with realistic data)
-> Smoke test (starts app, tries primary flow)
-> Accessibility (fonts, contrast, keyboard nav)
-> Dependencies (flags packages over 10MB)
-> UI (overflow, empty states, placeholders, false success)
```

### One-Command Setup

```
/setup recipe-finder

-> Generates: setup.sh, Dockerfile, docker-compose.yml, Makefile, .env.example, README
-> User experience: git clone && ./setup.sh
-> Platform agnostic, sensible defaults, prompts only for API keys
```

### Mid-Conversation Updates

Changed your mind? Say "actually I need ML too" while in `/architecture` -- the upstream doc updates in place, current skill continues.

### Re-Entry

All skills support re-entry. Run the same skill again -- it shows what exists and offers to continue, revisit, or start fresh.

## Modular Architecture

Each skill is a lean orchestrator (under 350 lines) that reads sub-skill files on demand:

```
skills/requirements/     127 lines base + 4 sub-skills + 7 references
skills/architecture/     117 lines base + 8 sub-skills + 4 references
skills/implementation/   152 lines base + 7 sub-skills + 7 references
skills/reviewer/         103 lines base + 6 sub-skills
skills/setup/            350 lines (standalone)
skills/status/           143 lines (standalone)
skills/evaluate/         255 lines (standalone)
skills/updater/          180 lines (standalone)
shared/                  guardrails.md + report-format.md + project-state-template.md
```

## Agents

| Agent | Purpose |
|-------|---------|
| `functional-researcher` | How features work in other products |
| `scale-estimator` | Back-of-envelope math |
| `infrastructure-planner` | Servers, databases, cost |
| `tech-stack-advisor` | Tech options with trade-offs |
| `pattern-advisor` | Design patterns for specific problems |
| `scale-advisor` | What changes at each scale level |
| `codestructure-analyzer` | Analyze existing codebase structure and conventions |

## Guardrails

Safety limits on every skill. When hit: warns, records, continues.

**Universal:** No secrets in output. No destructive ops without confirmation. File safety checks. No PII. Mid-conversation updates. LLM data security. README auto-update after feature changes.

**Skill-specific:** Question limits, backtrack limits, decision limits, OWASP references, dependency audits, file overwrite protection.

See `shared/guardrails.md` for full details.

## Quick Start

```
/requirements my-app         # gather requirements
/architecture my-app         # design architecture
/implementation my-app       # skeleton + slabs with TDD
/reviewer my-app             # code + tests + a11y + smoke test
/setup my-app                # install scripts + Docker + README
/status my-app               # where am I? what's next?
/evaluate my-app             # did it match what was asked?
```

Skills read each other's output via `project-state.md` -- run in order for best results, or independently.
