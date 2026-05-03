# Agent Toolkit

[![Skills: 12](https://img.shields.io/badge/Skills-12-blue?style=for-the-badge)](skills/)
[![Agents: 9](https://img.shields.io/badge/Agents-9-green?style=for-the-badge)](agents/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)
[![Health Check](https://img.shields.io/badge/Health_Check-twice_monthly-brightgreen?style=for-the-badge)](.github/workflows/updater.yml)

Production-ready skills for AI coding agents. Plan, build, test, debug, and ship software projects — any repo, any language, any stack.

Built for universal LLMs. Adapts best with Claude Code so far.

## Who This Is For

- **Solo developers** using AI agents to build full-stack apps
- **Teams** wanting a repeatable AI-assisted development workflow
- **Anyone tired of** sloppy AI-generated code, ignored instructions, tests that prove nothing, and "it works on my machine"

## Quick Start

```bash
git clone https://github.com/jvalin17/agent-toolkit.git
cd agent-toolkit
./install.sh
```

Then in any project:

```
/explore .                        # understand this codebase
/requirements my-app              # gather requirements
/architecture my-app              # design architecture
/implementation my-app            # build with TDD
/debug something is broken        # systematic diagnosis
/assess my-app                    # architecture fitness check + safe refactoring
/precommit                        # quality gate before commit
/reviewer my-app                  # code + tests + a11y audit
/setup my-app                     # install scripts + Docker + README
/status my-app                    # where am I? what's next?
/evaluate my-app                  # did it match what was asked?
```

## Skills

| Skill | What It Does |
|-------|-------------|
| `/explore` | Understand any codebase (or multiple repos). 4-phase: recon, architecture mapping, conventions, feature/issue mapping. |
| `/requirements` | Gather requirements. Draft early, explore on demand. Asks "how do you do this today?" to prevent building the wrong product. |
| `/architecture` | Design architecture with trade-offs. User journey mandatory. Legal checks. Concurrency warnings. |
| `/implementation` | Build with TDD. Walking skeleton, then feature slabs. Fix, refactor, demo modes. Frontend hardening pass. |
| `/debug` | Systematic debugging. Hypothesis-driven, layer-by-layer. Reproduce with test, then fix. 3-strikes escalation. |
| `/assess` | Architecture fitness check. Scale-aware — suggests changes only when thresholds justify them. Safe refactoring with characterize-abstract-build-switch-verify-remove sequence. |
| `/precommit` | Quality gate before every commit. All instructions addressed? Tests meaningful? SOLID/DRY? Rules compliance? Verified in running app? |
| `/reviewer` | Code quality + write tests + smoke test + accessibility + dependency audit + UI validation. |
| `/setup` | Generate install scripts, Docker, Makefile, README. One-command setup, platform agnostic. |
| `/status` | Project dashboard. What's done, what's next, suggest action. |
| `/evaluate` | Grade output against the original prompt. Run between skills as checkpoint. |
| `/updater` | Audit toolkit health, freshness, security, standards. |

## How It Works

### Plan -> Build -> Ship

```
/requirements recipe-finder
-> "What are you building?" -> "App to find recipes by ingredients"
-> "How do you do this today?" -> "Google each combo manually"
-> Draft saved. Explore areas on demand. Done.

/architecture recipe-finder
-> Quick arch: Python + React + SQLite + REST
-> Go deeper: frontend, LLM integration, security

/implementation recipe-finder
-> Phase 1: Walking skeleton (thin end-to-end path)
-> Phase 2: Feature slabs with TDD, security stitched in
-> Phase 3: Frontend hardening (crash/stuck-state/silent-lie prevention)
-> /precommit before every commit

/reviewer recipe-finder
-> Code quality, test coverage, smoke test, a11y, dependency audit

/setup recipe-finder
-> setup.sh + Docker + Makefile + .env.example + README
-> "git clone && ./setup.sh" — works on any platform
```

### Adding Features to Existing Apps

```
/requirements add-search
-> Scans your codebase ONCE, builds a Codebase Index
-> Index reused by all downstream skills (no re-scanning)
-> /architecture designs how feature fits (not a full redesign)
-> /implementation skips skeleton, goes straight to feature slab
```

### Debug Anything

```
/debug multiplayer is broken
-> Hypotheses: [H1] WebSocket disconnect not broadcast (high confidence)
-> Investigation: [H1] CONFIRMED — disconnect handler never emits event
-> Reproducing test written, fix applied, regression test added
-> "Change ready. Please verify: [specific action]."
```

### Pre-Commit Quality Gate

```
/precommit
-> All user instructions addressed? (re-reads every message)
-> Tests meaningful? (no assertTrue(True), no "foo" test data)
-> SOLID/DRY/KISS/YAGNI principles?
-> Contradicts any project decision/constraint/learning?
-> Verified in running app? (not just tests passing)
-> READY TO COMMIT or BLOCKED
```

### When to Run Which

| Skill | When | Time |
|-------|------|------|
| `/assess` | Before major changes, or periodically to check fitness | ~15 min |
|-------|------|------|
| `/precommit` | Before every commit | ~1 min |
| `/reviewer` | After a feature is complete | ~10 min |
| `/evaluate` | Between skills or at the end | ~5 min |

## Architecture

Token-optimized. Lean orchestrators load sub-skills on demand — only the area you're working on gets loaded, not the whole toolkit.

```
skills/
  requirements/     71-line orchestrator + 4 sub-skills + 7 references
  architecture/     66-line orchestrator + 8 sub-skills + 4 references
  implementation/   85-line orchestrator + 7 sub-skills + 7 references
  reviewer/        103-line orchestrator + 6 sub-skills
  assess/          164-line orchestrator + 2 references (patterns + anti-patterns)
  explore/         137 lines
  debug/           182 lines
  precommit/       232 lines
  setup/           350 lines
  status/          143 lines
  evaluate/         66 lines
  updater/         180 lines

shared/
  guardrails-quick.md         30-line summary (loaded by default)
  guardrails.md               full rules (loaded only when triggered)
  report-format.md            progress report template
  project-state-template.md   template for project-state.md (created at project root by skills)
```

## Agents

Sub-agents for parallel research and validation:

| Agent | Purpose |
|-------|---------|
| `functional-researcher` | How features work in other products |
| `scale-estimator` | Back-of-envelope math (QPS, storage, bandwidth) |
| `infrastructure-planner` | Servers, databases, cost estimates |
| `tech-stack-advisor` | Tech options with trade-offs |
| `pattern-advisor` | Design patterns for specific problems |
| `scale-advisor` | What changes at each scale level |
| `codestructure-analyzer` | Analyze existing codebase structure |
| `readme-validator` | Verify every claim in README is true |
| `rules-indexer` | Scan project docs for decisions and constraints |

## Guardrails

Safety limits on every skill. When hit: warns, records, continues.

**Universal:** No secrets in output. No destructive ops without confirmation. LLM data security. README auto-update. Check project rules before acting.

**Pre-commit:** No sloppy tests. All instructions addressed. No false "done." Verify in running app. Ask on ambiguity.

**Skill-specific:** Question limits, backtrack limits, decision limits, OWASP references, dependency audits.

## Portability

Built for universal LLMs — the patterns, workflows, and rules work with any AI coding agent. Claude Code adapts best so far thanks to native skill/agent support and auto-update hooks. For other tools, adapt the SKILL.md format to your agent's instruction system:

| Tool | How to adapt |
|------|-------------|
| Claude Code | Works natively — `./install.sh` and go |
| Cursor | Copy skill content to `.cursorrules` or project rules |
| Codex / Devin | Use as `AGENTS.md` or system prompts |
| Any LLM agent | The instructions are plain English — paste into your agent's config |

## Built From Real Usage

Every rule in this toolkit comes from building a real product with AI agents — async/sync silent failures, Promise.all page blanking, sloppy tests that prove nothing, false success messages, parking lot blindness. These aren't theoretical patterns; they're bugs that shipped and were caught.

## Automated Health Check

A GitHub Actions workflow runs twice a month (1st and 15th) to keep the toolkit fresh:

- **Link check** — runs `check-links.py` against all reference URLs
- **Freshness check** — flags references older than 6 months
- **File size check** — flags any file exceeding 400 lines
- **Inventory** — counts skills, agents, total lines

Opens a GitHub issue if broken links, stale references, or oversized files are found. Can also be triggered manually from the Actions tab.

## Contributing

PRs welcome. If you've battle-tested these skills and have feedback, open an issue or add to the patterns.

## License

MIT
