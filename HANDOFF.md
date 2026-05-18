# Agent Toolkit — Handoff Document

## What This Is

A production-ready skill toolkit for AI coding agents. 14 skills, 9 agents, 15 guardrails. Built for Claude Code, portable to Codex/Cursor/Gemini/Windsurf/Aider via `generate-project-rules.sh`.

**Repo:** https://github.com/jvalin17/agent-toolkit

## Key Files

| File | Purpose |
|------|---------|
| `README.md` | Public-facing docs, install, flows, architecture |
| `install.sh` | One-time install — symlinks skills/agents/shared, adds auto-update hook |
| `update.sh` | Called by hook before every skill — pulls latest, symlinks new files |
| `generate-project-rules.sh` | Generates AGENTS.md for non-Claude tools |
| `shared/guardrails-quick.md` | 33-line safety rules loaded by every skill |
| `shared/guardrails.md` | Full guardrail definitions (G1-G14) — loaded only when triggered |
| `shared/report-format.md` | Report structure for all 13 skills |
| `shared/project-state-template.md` | Template for project-state.md (created at project root by first skill) |
| `.github/workflows/updater.yml` | Health check CI — runs 1st and 15th of each month |
| `LICENSE` | MIT |

## Skills (13)

| Skill | Lines | Status | Notes |
|-------|-------|--------|-------|
| `/requirements` | 78 | Working (B from real usage) | Needs: draft after Q1+Q4 not Q7, auto-detect mode from context |
| `/architecture` | 68 | Working (B+ from real usage) | Has reuse check. Explore menu rarely used — agent goes direct |
| `/implementation` | 104 | Working (A- from real usage) | Best feature: slab-by-slab discipline. Mock-first for data features. |
| `/verify` | 100 | New — not yet battle-tested | Output quality check, session health, user confirms. Wired as step 5. |
| `/precommit` | 239 | Working (A from real usage) | Quick mode for small changes. No circular /evaluate dependency. |
| `/reviewer` | 103 | Working (A+ from real usage) | Best skill. Found stale closure bugs. Don't change. |
| `/assess` | 164 | Working (A from real usage) | Scale-aware. Safe refactoring sequence. |
| `/evaluate` | 174 | Working (A from real usage) | 5-dimension percentage scoring. Not lenient. |
| `/explore` | 143 | Working | 4-phase codebase analysis. Multi-repo. |
| `/debug` | 188 | Working | Hypothesis-driven. 3-strikes escalation. |
| `/setup` | 77 | Working | One-command install generation. Platform agnostic. |
| `/status` | 147 | Working | Project dashboard. |
| `/updater` | 180 | Working | Toolkit health audit. |
| `/readme` | ~200 | New — not yet battle-tested | Line-by-line README validation, link checking, test detail enforcement. Wired into precommit. |

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
| `readme-validator` | Working |
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
5. **13 skills is cognitive load ~7/10 for new users.** Core loop is requirements → implementation → verify. Rest is on-call.
6. **Model degradation in long sessions.** Session limits (300 lines, 20 exchanges, 2 failed fixes) added to /verify but compliance depends on the model following instructions.

## What Was Built in This Conversation

### New skills created
- `/readme` — line-by-line README validation, link checking, test details, wired into precommit
- `/verify` — output quality check, session health, user confirms before proceeding
- `/explore` — 4-phase codebase analysis, multi-repo
- `/debug` — hypothesis-driven, layer-by-layer, 3-strikes
- `/assess` — architecture fitness, scale thresholds, safe refactoring
- `/precommit` — quality gate, instruction compliance, test quality
- `/setup` — install scripts, Docker, Makefile, README generation
- `/status` — project dashboard

### Major changes to existing skills
- `/requirements` — example output rule for data features, "how do you do this today?", core intent parking red flag, competitive check, 3 LLM modes
- `/architecture` — reuse check, user journey mandatory, legal/ToS check, concurrency warnings, drift detection
- `/implementation` — walking skeleton, feature slabs, mock-first, one-at-a-time, session limits, fix/refactor/demo modes, frontend hardening pass, frontend resilience rules (11 per-component + 10 resilience + 7-item post-write check)
- `/evaluate` — redesigned to 5-dimension percentage scoring

### Infrastructure
- `install.sh` — now symlinks shared/ directory
- `update.sh` — auto-symlinks new skills/agents/shared on pull
- `generate-project-rules.sh` — universal AGENTS.md for non-Claude tools
- `.github/workflows/updater.yml` — health check CI (fixed exit code issues)
- `shared/guardrails-quick.md` — 33-line quick reference loaded by default
- G1-G14 guardrails + G-IMPL-6 (no easy way out) including G12 (branch naming), G13 (encrypt personal data), G14 (project rules override)
- G-IMPL-6: No easy way out — blocks hardcoded returns, magic numbers, copy-paste x3, shipped stubs, swallowed errors, boolean flag arguments. Wired into precommit and evaluate.

## Feedback Sources

- `skills-feedback.md` at `/Users/jvalin/dev/st5/house-helper/skills-feedback.md` — 116+ items across 12+ sessions
- `feedback_security_approach.md` at `/Users/jvalin/.claude/projects/-Users-jvalin-dev-st5-house-helper/memory/feedback_security_approach.md` — security rules from real bugs

## What to Build Next

1. **Battle-test /verify** — the mock-first and output quality check haven't been used on a real project yet
2. **Slim requirements intake** — draft after Q1+Q4, not Q7
3. **Decide on sub-skill routing** — either make agents read them or remove the indirection
4. **Decide on reports** — either enforce creation or remove the instructions
5. **Consider: fewer skills, deeper** — 13 is a lot. Core loop is 5 skills (requirements, implementation, verify, precommit, evaluate). Rest could be modes or optional.

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
