# Agent Toolkit — Handoff Document

## What This Is

A production-ready skill toolkit for AI coding agents. 13 skills, 9 agents, 16 guardrails. Built for Claude Code, portable to Codex/Cursor/Gemini/Windsurf/Aider via `generate-project-rules.sh`. Auto mode for hands-off building with quality gates.

**Repo:** https://github.com/jvalin17/agent-toolkit

## Key Files

| File | Purpose |
|------|---------|
| `README.md` | Public-facing docs, install, flows, architecture |
| `install.sh` | One-time install — symlinks skills/agents/shared, adds auto-update hook |
| `update.sh` | Called by hook before every skill — pulls latest, symlinks new files |
| `generate-project-rules.sh` | Generates AGENTS.md for non-Claude tools |
| `shared/orchestrator.md` | Auto mode protocol — loaded when `auto` flag is set |
| `shared/guardrails-quick.md` | ~35-line safety rules loaded by every skill |
| `shared/guardrails.md` | Full guardrail definitions (G1-G14, G-IMPL-6, G-PUSH-1, G-AUTO-1) |
| `shared/report-format.md` | Report structure for all skills |
| `shared/project-state-template.md` | Template for project-state.md — includes decision IDs and resume section |
| `scripts/cleanup-archive.sh` | Deletes archive files older than 30 days |
| `.github/workflows/updater.yml` | Health check CI — runs 1st and 15th of each month |
| `LICENSE` | MIT |

## Skills (13)

| Skill | Lines | Status | Notes |
|-------|-------|--------|-------|
| `/requirements` | 78 | Working (B from real usage) | Needs: draft after Q1+Q4 not Q7, auto-detect mode from context |
| `/architecture` | 68 | Working (B+ from real usage) | Has reuse check. Explore menu rarely used — agent goes direct |
| `/implementation` | 104 | Working (A- from real usage) | Best feature: slab-by-slab discipline. Mock-first for data features. |
| `/verify` | 100 | New — not yet battle-tested | Output quality check, session health, user confirms. Wired as step 5. |
| `/precommit` | ~300 | Working (A from real usage) | Quality gate. Test suite execution, G-IMPL-6, README validation via readme-validator agent. |
| `/reviewer` | 103 | Working (A+ from real usage) | Best skill. Found stale closure bugs. Don't change. |
| `/assess` | 164 | Working (A from real usage) | Scale-aware. Safe refactoring sequence. |
| `/evaluate` | 174 | Working (A from real usage) | 5-dimension percentage scoring. Not lenient. G-IMPL-6 check. |
| `/explore` | 143 | Working | 4-phase codebase analysis. Multi-repo. |
| `/debug` | 188 | Working | Hypothesis-driven. 3-strikes escalation. |
| `/setup` | 77 | Working | One-command install generation. Platform agnostic. |
| `/status` | 147 | Working | Project dashboard. |
| `/updater` | 180 | Working | Toolkit health audit. |

**Consolidated:** `/readme` skill → absorbed into `readme-validator` agent. `/auto` skill → absorbed into `shared/orchestrator.md`. No functionality lost.

## Agents (9)

| Agent | Status |
|-------|--------|
| `functional-researcher` | Working |
| `scale-estimator` | Working |
| `infrastructure-planner` | Working |
| `tech-stack-advisor` | Working |
| `pattern-advisor` | Working |
| `scale-advisor` | Working |
| `codestructure-analyzer` | Working |
| `readme-validator` | Working — upgraded to validate+fix (absorbed /readme skill logic) |
| `rules-indexer` | Working (simplified — greps project .md files) |

## What's Working Well (don't change)

1. **Slab-by-slab discipline** — best feature across all skills. One feature at a time, stop between slabs.
2. **Reviewer skill** — A+ grade. Finds real bugs (stale closures, DRY violations, EventSource leaks).
3. **Assess skill** — scale-aware thresholds prevent over-engineering.
4. **TDD enforcement** — meaningful assertions, realistic data, no sloppy tests.
5. **Precommit gate** — catches ignored instructions, sloppy tests, naming violations.
6. **Security stitched into slabs** — not bolted on at end.
7. **Auto-update hook** — pulls latest + symlinks new skills before every invocation.
8. **G14 (project rules override toolkit defaults)** — respects team/senior autonomy.

## What's Not Working (known issues)

1. **Agent still builds wrong thing sometimes.** "Walking score 72" and "20 hospitals raw dump" — technically correct, useless to user. Mock-first (step 0) and /verify (step 5) added to fix this but NOT yet battle-tested.
2. **Requirements intake too heavy.** 7 questions before drafting. Should draft after Q1+Q4, deepen on demand. Feedback says users skip Q2-Q3.
3. **Sub-skill files rarely read.** Architecture and implementation sub-skill menus add ceremony but agents go direct. The sub-skills have valuable content (decision tables, anti-patterns) but the routing is unused.
4. **Reports never actually written.** Every skill says "write report to reports/" but in practice output is inline. Report infrastructure exists in template but isn't used.
5. **Model degradation in long sessions.** Session limits (300 lines, 20 exchanges, 2 failed fixes) added to /verify but compliance depends on the model following instructions.
6. **Auto mode not yet battle-tested.** Orchestrator, evidence-first, handoff protocol, and model selection are designed but haven't been used on a real project.

## What Was Built

### Orchestrator (auto mode)
- `shared/orchestrator.md` — auto mode protocol: skill chaining, plan-before-code, model selection (Opus plans, Sonnet implements), evidence-first (G-AUTO-1), token tracking, handoff on context limit, cleanup phase
- Activated by appending `auto` to any skill: `/implementation auto inventory-app`
- 95% eval gate default, < 70% = hard stop
- All core skills reference orchestrator when `auto` flag is set

### Guardrails added
- **G-IMPL-6:** No easy way out — blocks hardcoded returns, magic numbers, copy-paste x3, shipped stubs, swallowed errors
- **G-PUSH-1:** No commit or push without /precommit passing. Non-negotiable.
- **G-AUTO-1:** Every change must cite evidence source. Never assume.
- **G-RM-1/2/3:** README maintenance guardrails (in readme-validator agent)

### Skills consolidated
- `/readme` skill → absorbed into `readme-validator` agent (validate+fix mode)
- `/auto` skill → absorbed into `shared/orchestrator.md`
- Net result: fewer skills (14→13), stronger coverage

### Infrastructure
- `install.sh` — symlinks shared/ directory
- `update.sh` — auto-symlinks new skills/agents/shared on pull
- `generate-project-rules.sh` — universal AGENTS.md for non-Claude tools
- `scripts/cleanup-archive.sh` — deletes archive files older than 30 days
- `shared/project-state-template.md` — typed decision IDs (D-ARCH-, D-IMPL-), code change plan section, resume section
- `.github/workflows/updater.yml` — health check CI (fixed exit code issues)

## Feedback Sources

- `skills-feedback.md` at `/Users/jvalin/dev/st5/house-helper/skills-feedback.md` — 116+ items across 12+ sessions
- `feedback_security_approach.md` at `/Users/jvalin/.claude/projects/-Users-jvalin-dev-st5-house-helper/memory/feedback_security_approach.md` — security rules from real bugs
- `feedback_skills_enforcement.md` at `/Users/jvalin/.claude/projects/-Users-jvalin-dev-st5-green-leaf-judgement/memory/feedback_skills_enforcement.md` — why skills, not memories, enforce quality

## What to Build Next

1. **Battle-test auto mode** — run `/requirements auto` on a real project, validate orchestrator behavior
2. **Battle-test /verify** — mock-first and output quality check on a real project
3. **Slim requirements intake** — draft after Q1+Q4, not Q7
4. **Decide on sub-skill routing** — either make agents read them or remove the indirection
5. **Decide on reports** — either enforce creation or remove the instructions
6. **MCP token counting** — if line/char estimation proves unreliable, build an MCP server for precise token tracking

## Session Health Thresholds (from research)

| Limit | Threshold |
|-------|-----------|
| Reliable context | ~25-32K tokens |
| Session exchanges | 20 before degradation |
| File size for AI editing | 150-500 lines sweet spot |
| Opus at 1M tokens | 76% accuracy |
| Sonnet at 1M tokens | 18.5% accuracy |
| After 2 failed fixes | Stop and restart fresh |

## How to Continue

1. `cd /Users/jvalin/dev/st5/agent-toolkit`
2. Read this file for context
3. Check `skills-feedback.md` for latest real-usage feedback
4. Run `/status agent-toolkit` to see current state
5. Core skills to use: `/requirements`, `/implementation`, `/verify`, `/precommit`, `/evaluate`
6. Auto mode: append `auto` to any skill invocation
