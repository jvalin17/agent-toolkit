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
| `/implementation` | Build with TDD. Skeleton with frontend foundation (types, API client, hooks, ErrorBoundary). Feature slabs. Fix, refactor, demo modes. Post-feature hardening pass. |
| `/reviewer` | Review code + write tests + smoke test + accessibility + dependency audit + UI validation (Promise.all detection, empty states, false success, overflow). |
| `/explore` | Get familiar with any codebase (or multiple repos). Deep-dive tech stack, architecture, features, conventions, issues. Read-only. |
| `/debug` | Systematic debugging. Hypothesis-driven, layer-by-layer diagnosis. Reproduce with test, then fix (optional). 3-strikes escalation. |
| `/precommit` | Quality gate before every commit. Verifies all instructions addressed, tests are meaningful (not sloppy), code meets standards, changes work in running app. |
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
  Backend: 1 table + 1 endpoint + DB connection
  Frontend: 1 page + API call + ErrorBoundary + types/index.ts
            + api/client.ts + useAsync hook + toast library
  = architecture proved + frontend foundation ready

Phase 2: Feature Slabs (TDD for logic, security stitched in)
  Slab 1: Auth (Backend + Security)
  Slab 2: Core CRUD (Backend + Frontend)
  Slab 3: AI features (Backend + LLM + Security)
  One commit per slab. All tests passing.

Phase 3: Frontend Hardening (ONCE, after features stabilize)
  Crash prevention, stuck-state prevention, silent-lie prevention,
  security audit, code quality cleanup. Not mixed into feature work.
```

### Explore Any Codebase

```
/explore /path/to/unfamiliar-repo

-> Phase 1: Reconnaissance (glob/grep, never reads everything)
-> Phase 2: Architecture mapping (patterns, data flow, key dependencies)
-> Phase 3: Convention detection (naming, error handling, test patterns)
-> Phase 4: Feature & issue mapping (what works, what's broken, TODOs)
-> Outputs project-state.md with Codebase Index

Multi-repo: /explore /repo-a /repo-b
-> Maps API contracts, shared types, deployment relationships
```

### Debug Anything

```
/debug multiplayer is broken

-> Symptom: multiplayer lobby shows 0 players
-> Hypotheses: [H1] WebSocket disconnect not broadcast (high)
               [H2] Game cleanup removing active games (medium)
-> Investigation: [H1] CONFIRMED — websocket.py:240 catches
   WebSocketDisconnect but never emits player_left event
-> Reproducing test written and failing
-> "Want me to fix it?" -> yes -> fixed, test passes, regression added
```

### Pre-Commit Quality Gate

```
/precommit

-> Step 1: Did I address ALL user instructions? (re-reads every message)
-> Step 2: Are all tests meaningful? (no sloppy assertions, realistic data)
-> Step 3: Code standards met? (naming, no raw fetch, no silent catches)
-> Step 4: Verified in running app? (port check, curl endpoint, user confirms)
-> READY TO COMMIT or BLOCKED with reasons
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
skills/implementation/   186 lines base + 7 sub-skills + 7 references
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
| `readme-validator` | Verify every claim in README is actually true |

## Guardrails

Safety limits on every skill. When hit: warns, records, continues.

**Universal:** No secrets in output. No destructive ops without confirmation. File safety checks. No PII. Mid-conversation updates. LLM data security. README auto-update after feature changes.

**Skill-specific:** Question limits, backtrack limits, decision limits, OWASP references, dependency audits, file overwrite protection.

See `shared/guardrails.md` for full details.

## Quick Start

```
/explore /path/to/repo        # understand any codebase
/requirements my-app         # gather requirements
/architecture my-app         # design architecture
/implementation my-app       # skeleton + slabs with TDD
/debug something is broken   # systematic diagnosis + fix
/precommit                   # quality gate before commit
/reviewer my-app             # code + tests + a11y + smoke test
/setup my-app                # install scripts + Docker + README
/status my-app               # where am I? what's next?
/evaluate my-app             # did it match what was asked?
```

Skills read each other's output via `project-state.md` -- run in order for best results, or independently.
