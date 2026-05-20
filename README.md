# Agent Toolkit

[![Skills: 13](https://img.shields.io/badge/Skills-13-blue?style=for-the-badge)](skills/)
[![Agents: 9](https://img.shields.io/badge/Agents-9-green?style=for-the-badge)](agents/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)
[![Health Check](https://img.shields.io/badge/Health_Check-twice_monthly-brightgreen?style=for-the-badge)](.github/workflows/updater.yml)

Production-ready skills for AI coding agents. Plan, build, test, debug, and ship software projects — any repo, any language. Defaults tuned for common web apps (React/TS, Python, Node); adaptable to any stack via G14 project overrides. 13 skills, 9 agents, 16 guardrails. Auto mode for hands-off building with quality gates.

Built for universal LLMs. Adapts best with Claude Code so far.

## Who This Is For

- **Solo developers** using AI agents to build full-stack apps
- **Teams** wanting a repeatable AI-assisted development workflow
- **Anyone tired of** sloppy AI-generated code, ignored instructions, tests that prove nothing, and "it works on my machine"

## Quick Start

```bash
git clone https://github.com/jvalin17/agent-toolkit.git
cd agent-toolkit
./install.sh    # symlinks skills + agents + shared, adds auto-update hook
```

**Auto-updates:** After install, the toolkit updates itself before every skill invocation — pulls latest changes AND symlinks any new skills/agents/shared files automatically. You never need to re-run `install.sh` unless you move the repo.

**Already installed an older version?** Re-run `./install.sh` once to get the improved auto-update hook. After that, updates are automatic.

Then in any project:
- **Existing codebase?** → `/explore .` to understand it first
- **Greenfield?** → `/requirements my-app` to start building ([see Flow 1](#flow-1-greenfield--plan-build-ship))
- **Hands-off?** → `/requirements auto my-app` to build autonomously ([see Auto Mode](#auto-mode))

For non-Claude tools: `./generate-project-rules.sh` in your project creates `AGENTS.md` (works with Codex, Cursor, Gemini CLI, Windsurf, Aider).

## Skills

| Skill | What It Does | Example |
|-------|-------------|---------|
| `/explore` | Understand any codebase (or multiple repos). 4-phase: recon, architecture, conventions, issues. | [Greenfield](#flow-1-greenfield--plan-build-ship) |
| `/requirements` | Gather requirements. Draft early, explore on demand. "How do you do this today?" prevents wrong product. | [Greenfield](#flow-1-greenfield--plan-build-ship) |
| `/architecture` | Design with trade-offs. User journey mandatory. Legal/ToS checks. Reuse check before new components. | [Greenfield](#flow-1-greenfield--plan-build-ship) |
| `/implementation` | TDD. Walking skeleton, then one slab at a time. Fix, refactor, demo modes. Hardening pass. | [Greenfield](#flow-1-greenfield--plan-build-ship), [Fix/Refactor](#flow-4-fix-refactor-demo) |
| `/debug` | Hypothesis-driven diagnosis. Layer-by-layer. Reproduce with test, then fix. 3-strikes escalation. | [Debug](#flow-3-debug) |
| `/assess` | Architecture fitness. Scale-aware — only suggests when thresholds justify. Safe refactoring. | [Assessment](#flow-5-architecture-assessment) |
| `/verify` | Check output is actually useful, not just technically correct. Session health. User confirms. Offers automation. |
| `/precommit` | Quality gate. Instructions addressed? Tests meaningful? SOLID/DRY? Verified in app? | [Greenfield](#flow-1-greenfield--plan-build-ship) |
| `/reviewer` | Code quality + tests + smoke test + a11y + dependencies + UI validation. | [Greenfield](#flow-1-greenfield--plan-build-ship) |
| `/setup` | Install scripts, Docker, Makefile, README. One command, platform agnostic. | [Greenfield](#flow-1-greenfield--plan-build-ship) |
| `/status` | Project dashboard. What's done, what's next. | — |
| `/evaluate` | 5-dimension quality score. Completeness, code quality, security, tests, efficiency. Percentage grade. | [Scoring](#flow-6-quality-scoring) |
| `/updater` | Toolkit health: links, freshness, standards, file sizes. | — |

## Flows

### Flow 1: Greenfield — Plan, Build, Ship

```
/requirements recipe-finder
-> "What are you building?" -> "Find recipes by ingredients"
-> "How do you do this today?" -> "Google each combo manually"
-> Draft saved. Explore: UI/UX, ML, LLM, Testing on demand.

/architecture recipe-finder
-> Quick arch: Python + React + SQLite + REST
-> Reuse check: what existing code can we leverage?
-> Go deeper: frontend, LLM integration, security

/implementation recipe-finder
-> Skeleton: 1 table + 1 endpoint + 1 page + ErrorBoundary + api client
-> Slab 1: Recipe CRUD (TDD, 12 tests) -> /verify -> /precommit -> commit
-> Slab 2: AI matching (mock output first, TDD) -> /verify -> /precommit -> commit
-> Slab 3: Search UI (TDD, 6 tests) -> /verify -> /precommit -> commit
-> Frontend hardening pass (crash/stuck-state/silent-lie prevention)

/reviewer recipe-finder -> code + tests + a11y + deps + UI checks
/setup recipe-finder    -> setup.sh + Docker + Makefile + README
/evaluate recipe-finder -> "Score: 94% (A). To reach 96%: add rate limiting."
```

### Flow 2: Add Feature to Existing App

```
/requirements add-search
-> Scans codebase ONCE, builds Codebase Index
-> Asks only about what's NEW (skips what exists)

/architecture add-search
-> Reads Codebase Index (no re-scan)
-> Reuse check: found existing scorer.py, matcher.py — reuse 80%
-> Designs how feature fits: integration points, new components, migrations

/implementation add-search
-> Skips skeleton (existing app IS the skeleton)
-> One feature slab with TDD, following existing conventions
-> /precommit -> commit on branch feature/add-search
```

### Flow 3: Debug

```
/debug search returns 0 results
-> [H1] API key missing from .env (high confidence)
-> [H2] Async/sync mismatch in endpoint (medium)
-> Investigation: [H1] CONFIRMED — .env has wrong key name
-> Failing test written -> fixed -> regression test added
-> "Change ready. Please verify: search for 'chicken'."
```

### Flow 4: Fix, Refactor, Demo

```
/implementation fix login-bug       -> failing test -> fix -> verify in app
/implementation refactor auth       -> tests pass -> refactor -> tests still pass
/implementation demo auto-apply     -> simulated data -> validate UX first
```

### Flow 5: Architecture Assessment

```
/assess my-app
-> Scans infra, maps data flow, checks anti-patterns
-> "N+1 query in user list (fix now — any scale)"
-> "No caching on search endpoint (consider at >100 QPS — you're at 80)"
-> "RAG is overkill — your corpus fits in context window"
-> Safe refactoring if user wants: characterize -> abstract -> build -> switch -> verify -> remove
```

### Flow 6: Quality Scoring

```
/evaluate my-app
-> Completeness: 95% (19/20 claims passed)
-> Code Quality: 88% (naming violations in 2 files)
-> Security: 100%
-> Test Quality: 85% (3 tests use unrealistic data)
-> Efficiency: 92%
-> Overall: 92% (A)
-> "To reach 96%: fix naming in api/users.py, use realistic test data in 3 tests."
```

### Flow 7: Auto Mode — Hands-Off Building

Append `auto` to any skill to chain the full pipeline automatically:

```
/requirements auto inventory-app

-> [Opus] Requirements: auto-research via functional-researcher, draft early
-> [Opus] Architecture: tech-stack-advisor, pattern-advisor, decisions logged as D-ARCH-1, D-ARCH-2
-> [Opus] Code change plan: file-by-file, function-by-function, evidence-cited
-> [Sonnet] Slab 1: skeleton (TDD, 4 tests) → precommit ✓ → eval 96% → auto-commit
-> [Sonnet] Slab 2: CRUD (12 tests) → precommit ✓ → eval 95% → auto-commit
-> ⚠️ Context limit → HANDOFF.md generated → new session resumes
-> [Sonnet] Slab 3-4: remaining features → auto-commit each
-> [Opus] Final quality: eval 95%, README verified line-by-line, guardrail audit
-> Cleanup: archive artifacts, README = source of truth
```

**Pauses for:** ambiguity, repeated failures, eval < 70%, architectural decisions.
**Never:** guesses, loops on failures, commits below 95% eval, pushes without auth.

### When to Run Which

| Skill | When | Time |
|-------|------|------|
| `/verify` | After each slab — is the output useful? User confirms. | ~3 min |
| `/precommit` | Before every commit — code standards + rules | ~1 min |
| `/assess` | Before major changes — architecture fitness | ~15 min |
| `/reviewer` | After a feature is complete — deep code audit | ~10 min |
| `/evaluate` | Between skills or at end — percentage quality score | ~5 min |

## Architecture

Token-optimized. Lean orchestrators load sub-skills on demand. All files under 250 lines.

```
skills/
  requirements/     ~78-line orchestrator + 4 sub-skills + 7 references
  architecture/     ~68-line orchestrator + 8 sub-skills + 4 references
  implementation/   ~104-line orchestrator + 7 sub-skills + 7 references
  reviewer/         103-line orchestrator + 6 sub-skills
  assess/           164-line orchestrator + 2 references
  debug/            ~188 lines
  evaluate/          174 lines
  explore/          ~141 lines
  precommit/        ~239 lines
  setup/             77-line orchestrator + 1 reference
  status/           ~147 lines
  updater/           180 lines
  verify/            100 lines

shared/
  orchestrator.md             ~150 lines (loaded when `auto` flag is set)
  guardrails-quick.md         ~35 lines (loaded by default)
  guardrails.md               full rules (loaded only when triggered)
  report-format.md            progress report template
  project-state-template.md   created at project root by first skill run

scripts/
  cleanup-archive.sh          deletes archive files older than 30 days

agents/                       9 sub-agents for parallel research
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
| `codestructure-analyzer` | Analyze existing codebase structure |
| `readme-validator` | Validate + fix every README claim line-by-line (links, features, paths, env vars, tests) |
| `rules-indexer` | Scan project docs for decisions and constraints |

## Guardrails (G1-G14 + G-IMPL-6 + G-PUSH-1 + G-AUTO-1)

Safety limits on every skill. When hit: warns, records, continues.

- **G1-G9:** No secrets, no destructive ops, file safety, no PII, flag doc gaps, mid-conversation updates, LLM data security
- **G10:** README auto-update after feature changes
- **G11:** Check project rules before acting — flag contradictions
- **G12:** Branch naming: `feature/`, `fix/`, `refactor/`, `chore/`. PR titles must be descriptive.
- **G13:** Personal data and user preferences encrypted at rest. Never plaintext.
- **G14:** Project rules override toolkit defaults. Your CLAUDE.md/AGENTS.md/DECISIONS.md wins over any skill's default.
- **G-IMPL-6:** No easy way out — blocks hardcoded return values, magic numbers, copy-paste x3, shipped stubs, swallowed errors. Wired into precommit and evaluate.
- **G-PUSH-1:** No commit or push without /precommit passing. Non-negotiable.
- **G-AUTO-1:** In auto mode, every change must cite evidence (requirement ID, test result, code grep, research output). Never assume.
- **G-PC-1-5:** No sloppy tests, all instructions addressed, no false "done", verify in running app, ask on ambiguity

## Harness Engineering (structural enforcement)

Guardrails are prompts — the model can ignore them. Hooks are structural — the model **cannot bypass them**.

`install.sh` sets up these hooks automatically:

| Hook | Type | What it does |
|------|------|-------------|
| `precommit-gate.sh` | PreToolUse (Bash) | **Blocks `git commit`/`git push`** unless `/precommit` has passed. Exit code 2 = blocked. |
| `precommit-passed.sh` | PostToolUse (Skill) | Creates `.precommit-passed` flag when `/precommit` completes. Only way to unlock commit. |
| `post-commit-cleanup.sh` | PostToolUse (Bash) | Clears `.precommit-passed` after commit. Next commit needs fresh `/precommit`. |
| `update.sh` | PreToolUse (Skill) | Auto-pulls latest toolkit before every skill invocation. |

**How it works:**
```
User: "commit this"
Claude: git commit -m "..."
  → precommit-gate.sh runs → no .precommit-passed → BLOCKED
  → Claude sees: "BLOCKED. Run /precommit first."
  → Claude runs /precommit → all checks pass → .precommit-passed created
  → Claude: git commit -m "..."
  → precommit-gate.sh runs → .precommit-passed exists → ALLOWED
  → post-commit-cleanup.sh runs → .precommit-passed deleted
  → Next commit requires fresh /precommit
```

The model literally cannot commit without precommit passing. No amount of "momentum" bypasses this.

## Portability

Built for universal LLMs. Claude Code adapts best so far; other tools need minor wiring.

| Piece | Claude Code | Other agents |
|-------|------------|--------------|
| Install | `./install.sh` — symlinks into `~/.claude/` | `generate-project-rules.sh` → AGENTS.md |
| Auto-update | PreToolUse hook runs `git pull` | Cron, Makefile target, or CI |
| Skills | First-class slash commands | Custom commands, saved prompts, rule files |
| Sub-agents | Invoked natively | Auto-included in generated AGENTS.md — no manual pasting |

### Universal Project Rules (one script, every tool)

```bash
/path/to/agent-toolkit/generate-project-rules.sh            # creates AGENTS.md
/path/to/agent-toolkit/generate-project-rules.sh --cursor    # also creates .cursorrules
```

Generates a single ~110-line file containing: guardrails, workflow rules (TDD, precommit, slabs), frontend/backend anti-patterns, git conventions, and all 9 agent instructions flattened inline. Run once — every AI tool reads it automatically.

| File | Read by |
|------|---------|
| `AGENTS.md` | Codex, Claude Code, Gemini CLI, Windsurf, Aider |
| `.cursorrules` | Cursor |

## Built From Real Usage

Every rule comes from building a real product with AI agents — async/sync silent failures, Promise.all page blanking, sloppy tests, false success messages, parking lot blindness. Bugs that shipped and were caught.

## Automated Health Check

GitHub Actions runs twice a month (1st and 15th): link check, freshness check (6-month threshold), file size check (250-line target), inventory. Opens an issue if problems found.

## Contributing

PRs welcome. Battle-tested feedback? Open an issue or add to the patterns.

## License

MIT
