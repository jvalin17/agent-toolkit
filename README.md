# Agent Toolkit

Reusable Claude Code skills for planning, building, and shipping software projects. Works in any repo, any language. Battle-tested across 12 sessions building a real product.

## Install

```bash
git clone https://github.com/jvalin17/agent-toolkit.git
cd agent-toolkit
./install.sh
```

Symlinks skills + agents globally, adds auto-update hook (pulls latest before every skill invocation). `jq` required for the auto-update hook — install still works without it, hook is just skipped.

## Skills

| Skill | What It Does |
|-------|-------------|
| `/explore` | Understand any codebase (or multiple repos). 4-phase: recon, architecture mapping, conventions, feature/issue mapping. Read-only. |
| `/requirements` | Gather requirements. Draft early, explore on demand. Asks "how do you do this today?" to prevent building the wrong product. |
| `/architecture` | Design architecture with trade-offs. User journey mandatory. Legal/ToS checks. Concurrency warnings. Drift detection. |
| `/implementation` | Build with TDD. Skeleton + frontend foundation + feature slabs. Fix, refactor, demo modes. Hardening pass. |
| `/debug` | Systematic debugging. Hypothesis-driven, layer-by-layer. Reproduce with test, then fix. 3-strikes escalation. |
| `/precommit` | Quality gate. Checks: all instructions addressed, tests meaningful (not sloppy), SOLID/DRY/KISS/YAGNI, project rules compliance, verify in running app. |
| `/reviewer` | Code quality + write tests + smoke test + accessibility + dependency audit + UI validation. |
| `/setup` | Generate install scripts, Docker, Makefile, README. One-command setup, platform agnostic. |
| `/status` | Project dashboard. What's done, what's next. |
| `/evaluate` | Grade output against the original prompt. Run between any skills as checkpoint. |
| `/updater` | Audit toolkit health, freshness, security, standards. |

## How It Works

### Shared Project State

All skills read/write `project-state.md` — core intent, parking lot (flags if main goal is deferred), key decisions, feature status, handoff summaries.

### Rules Compliance (G11)

Before writing code, skills invoke the `rules-indexer` agent to scan all project .md files (CLAUDE.md, DECISIONS.md, project-state.md, architecture docs, learnings). Changes that contradict existing decisions are flagged — not silently overridden.

### Draft Early, Deepen on Demand

```
/requirements recipe-finder
-> Intake: What? How do you do this today? What exists?
-> Draft saved immediately
-> Explore: UI/UX, ML/AI, LLM, Testing, Non-Functional, Scale
-> Pick what you want, skip the rest, come back anytime
```

### Adding Features to Existing Apps

```
/requirements add-search
-> codestructure-analyzer scans codebase ONCE
-> Codebase Index reused by all downstream skills
-> /architecture designs how feature fits (not full redesign)
-> /implementation skips skeleton, goes to feature slab
```

### Walking Skeleton + Feature Slabs (Greenfield)

```
Phase 1: Skeleton (no TDD — scaffold)
  Backend: 1 table + 1 endpoint + DB connection
  Frontend: ErrorBoundary + types/index.ts + api/client.ts
            + useAsync hook + toast library

Phase 2: Feature Slabs (TDD, security stitched in)
  Each slab: setup -> security -> TDD -> integrate -> /precommit -> commit

Phase 3: Frontend Hardening (ONCE after features stabilize)
  Crash/stuck-state/silent-lie prevention, security, code quality
```

### Explore, Debug, Fix

```
/explore /path/to/repo           -> 4-phase codebase analysis, multi-repo
/debug multiplayer is broken     -> hypotheses, layer-by-layer, reproduce, fix
/implementation fix login-bug    -> failing test, fix, verify in running app
/implementation refactor auth    -> refactor, all tests still pass
/implementation demo auto-apply  -> simulated data, validate UX
```

### Pre-Commit Quality Gate

```
/precommit
-> Instructions: all user messages addressed?
-> Tests: meaningful assertions? realistic data? no sloppy tests?
-> Principles: SOLID, DRY, KISS, YAGNI violations?
-> Rules: contradicts any decision/constraint/learning in project .md files?
-> App: verified in running app? (port check, curl endpoint)
-> Ambiguity: anything unclear? -> ask user, log concern
-> READY TO COMMIT or BLOCKED
```

### Review, Setup, Status

```
/reviewer my-app   -> code + tests + runtime + a11y + deps + UI checks
/setup my-app      -> setup.sh + Docker + Makefile + .env.example + README
/status my-app     -> what's done, what's next, suggest action
/evaluate my-app   -> grade against original prompt
```

## Modular Architecture

Lean orchestrators + sub-skills loaded on demand. All files under 400 lines. Token-optimized: guardrails load a 30-line quick reference by default (full 210-line version only when triggered), and sub-skills load only when the user selects that area — not preloaded.

```
skills/requirements/     69 lines base + 4 sub-skills + 7 references
skills/architecture/     64 lines base + 8 sub-skills + 4 references
skills/implementation/   83 lines base + 7 sub-skills + 7 references
skills/reviewer/        103 lines base + 6 sub-skills
skills/explore/         137 lines
skills/debug/           182 lines
skills/precommit/       232 lines
skills/setup/           350 lines
skills/status/          143 lines
skills/evaluate/         66 lines
skills/updater/         180 lines
shared/                 guardrails-quick (30 lines, loaded by default)
                        guardrails (full, loaded only when triggered)
                        report-format + project-state-template
```

## Agents

| Agent | Purpose |
|-------|---------|
| `functional-researcher` | How features work in other products |
| `scale-estimator` | Back-of-envelope math (QPS, storage, bandwidth) |
| `infrastructure-planner` | Servers, databases, cost estimates |
| `tech-stack-advisor` | Tech options with trade-offs |
| `pattern-advisor` | Design patterns for specific problems |
| `scale-advisor` | What changes at each scale level |
| `codestructure-analyzer` | Analyze existing codebase structure and conventions |
| `readme-validator` | Verify every claim in README is actually true |
| `rules-indexer` | Scan project .md files for decisions, constraints, learnings |

## Guardrails

Safety limits on every skill. When hit: warns, records, continues.

**Universal (G1-G11):** No secrets. No destructive ops. File safety. No PII. Mid-conversation updates. LLM data security. README auto-update. Check rules before acting — flag contradictions, don't silently override.

**Pre-commit (G-PC-1 to G-PC-5):** No sloppy tests. All instructions addressed. No false "done." Verify in running app. Ask on ambiguity.

**Skill-specific:** Question limits, backtrack limits, decision limits, OWASP references, dependency audits.

See `shared/guardrails.md` for details.

## Quick Start

```
/explore /path/to/repo        # understand any codebase
/requirements my-app          # gather requirements
/architecture my-app          # design architecture
/implementation my-app        # skeleton + slabs with TDD
/debug something is broken    # systematic diagnosis + fix
/precommit                    # quality gate before commit
/reviewer my-app              # code + tests + a11y + smoke test
/setup my-app                 # install scripts + Docker + README
/status my-app                # where am I? what's next?
/evaluate my-app              # did it match what was asked?
```

Skills read each other's output via `project-state.md` — run in order or independently.

## Example: Building a Recipe Finder App

```
Session 1: Plan
  /requirements recipe-finder
  -> "What are you building?" -> "App to find recipes by ingredients I have"
  -> "How do you do this today?" -> "Google each ingredient combo manually"
  -> Draft saved. Explore: UI/UX -> screens, design. Done.

  /architecture recipe-finder
  -> Quick arch: Python + React + SQLite + REST
  -> Deeper: frontend (React + Tailwind + Zustand) + LLM (Claude API for matching)

Session 2: Build
  /implementation recipe-finder
  -> Skeleton: 1 table, 1 endpoint, 1 page, ErrorBoundary, api/client.ts, useAsync
  -> Slab 1: Recipe CRUD (model + API + list page) -- TDD, 12 tests
  -> Slab 2: Ingredient matching (Claude API + prompt + safety) -- TDD, 8 tests
  -> Slab 3: Search UI (search bar + results + empty state) -- TDD, 6 tests
  -> /precommit before each commit:
     "All instructions addressed? Tests meaningful? Standards met? Verified in app?"

Session 3: Polish
  /reviewer recipe-finder
  -> Code: SOLID check, naming audit
  -> Tests: coverage gaps filled, 15 new tests with realistic data
  -> UI: overflow on recipe names fixed, empty state added to favorites
  -> Runtime: smoke test passes -- search works end-to-end

  /setup recipe-finder
  -> setup.sh + Dockerfile + Makefile + .env.example + README generated
  -> "git clone && ./setup.sh" works on macOS and Linux

Session 4: Debug (later)
  /debug search returns 0 results
  -> [H1] API key not in .env (CONFIRMED) -- .env had wrong key name
  -> Failing test written, fixed, regression test added
  -> "Change ready. Please verify: search for 'chicken', should see 3 results."
```

**When to run which:**
- `/precommit` — fast gate, before every commit (1 min)
- `/reviewer` — thorough audit, on demand after a feature is complete (10 min)
- `/evaluate` — prompt compliance checkpoint, between skills or at the end (5 min)

## Portability

Built for Claude Code. The patterns (TDD slabs, precommit gate, hypothesis debugging, feedback-driven rules) work with any AI coding tool — adapt the format to your agent's instruction system (`.cursorrules`, `AGENTS.md`, etc.). The SKILL.md format and agent invocation syntax are Claude Code specific; the rules and workflows inside are universal.

## Built From Real Usage

These skills are informed by 116 feedback items across 12 sessions building a real product. Every rule about async/sync failures, Promise.all page blanking, sloppy tests, false success messages, and parking lot blindness comes from actual bugs that shipped and were caught.
