# Agent Toolkit

Reusable Claude Code skills for planning, building, and evaluating software projects. Works in any repo, any language.

## Skills

| Skill | What It Does |
|-------|-------------|
| `/requirements` | Gather requirements through structured questionnaire. Auto-scales: quick feature → standard app → full system design with QPS, storage, infrastructure, cost estimation. |
| `/architecture` | Design system architecture with waterfall decision flow. Presents options with trade-offs — you decide. Covers data, API, security, scaling, design patterns, CAP theorem, SOLID/DRY/KISS/YAGNI validation. |
| `/implementation` | Build features with TDD by default. 5 modes: backend, frontend, security, ML/data, pipeline. Language-agnostic with coding standards for Python, TypeScript, Java, Rust. |
| `/evaluate` | Grade agent output against the original prompt. Evidence-based — searches code, reads files, checks if what was asked actually got done. Run after any skill or any agent work. Optional. |
| `/updater` | Guardian of this toolkit. Audits skills for relevance, security, and standards. Validates against Anthropic, Google, OpenAI, OWASP best practices. Includes link checker script. |

## Sub-Agents

Skills spawn these for parallel research when needed:

| Agent | Purpose |
|-------|---------|
| `functional-researcher` | How features work in other products |
| `scale-estimator` | Back-of-envelope math (QPS, storage, bandwidth) |
| `infrastructure-planner` | Servers, databases, caching, cost estimates |
| `tech-stack-advisor` | Tech options with trade-offs (never decides) |
| `pattern-advisor` | Design patterns for specific problems |
| `scale-advisor` | What changes at each scale level |
| `test-generator` | Generate tests for existing code |
| `code-reviewer` | Quality, security, and principles review |

## Reports

Every skill generates a progress report in your project's `reports/` directory. Reports are:
- Created at the start (not just the end)
- Updated progressively as the skill works
- UUID-suffixed to avoid collisions
- Marked `completed` or `incomplete` with reason

## Install

```bash
git clone https://github.com/jvalin17/agent-toolkit.git
cd agent-toolkit
./install.sh
```

Symlinks skills to `~/.claude/skills/` and agents to `~/.claude/agents/`. Available globally in any Claude Code session.

## Usage

```
/requirements my-feature        # gather requirements
/architecture my-feature        # design architecture
/implementation backend         # build with TDD
/evaluate                       # grade the output (optional)
/updater                        # audit toolkit health
```

Skills read each other's output — run in order for best results, or independently.

## Coding Standards

The `/implementation` skill enforces language-specific coding standards:
- **Python** — PEP 8, Google Python Style Guide
- **TypeScript/React** — Google TS Guide, Airbnb JS Guide
- **Java** — Google Java Style Guide, Effective Java
- **Rust** — Rust API Guidelines, Clippy lints

Standards cover: imports, naming, comments, formatting, error handling, file organization.

## License

MIT
