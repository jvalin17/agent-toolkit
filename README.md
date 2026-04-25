# Agent Toolkit

Reusable Claude Code skills for planning, building, and evaluating software projects. Works in any repo, any language.

## Skills

| Skill | What It Does |
|-------|-------------|
| `/requirements` | Gather requirements through structured questionnaire. Auto-scales: quick feature → standard app → full system design with scale estimation, infrastructure, and cost. Launches sub-agents when user needs research help. |
| `/architecture` | Design system architecture with waterfall decision flow. Each decision shapes the next. Presents options with trade-offs — you decide. Backtracking supported. Covers data, API, security, scaling, design patterns, CAP theorem, SOLID/DRY/KISS/YAGNI. Always includes a local/cheap option. |
| `/implementation` | Build features with TDD by default. 5 modes: backend, frontend, security, ML/data, pipeline. Language-agnostic — detects tech stack and adapts. Enforces coding standards (imports, naming, comments, formatting). User chooses test approach: TDD, implement-then-test, or write-tests-only. |
| `/evaluate` | Grade agent output against the original prompt. Parses instructions into checkable claims, inspects code with evidence (file:line), produces a scorecard. Optional code quality check against coding standards. Run after any skill or agent work. |
| `/updater` | Guardian of this toolkit. Audits skills for relevance, security, and standards compliance. Checks reference links, freshness dates, framework versions. Validates against Anthropic, Google, OpenAI, OWASP guidelines. Includes `check-links.py` script. |

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

## Reports

Skills that produce artifacts (`/requirements`, `/architecture`, `/implementation`) generate progress reports in your project's `reports/` directory:
- Created at the start, updated progressively
- UUID-suffixed to avoid collisions across runs
- Marked `completed` or `incomplete` with reason and remaining work
- Previous reports on the same topic are linked automatically

`/evaluate` produces a scorecard (its output IS the report).
`/updater` reports to the toolkit repo (it audits the toolkit, not your project).

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

`/implementation` enforces language-specific standards. `/evaluate` can optionally check against them.

| Language | Based On |
|----------|----------|
| Python | PEP 8, Google Python Style Guide |
| TypeScript/React | Google TS Guide, Airbnb JS Guide |
| Java | Google Java Style Guide, Effective Java |
| Rust | Rust API Guidelines, Clippy lints |

Universal rules enforced across all languages: no unused imports, readable variable names, comments explain WHY not WHAT, consistent indentation, small functions, no magic numbers.

## Contributors

- **jvalin17** — jvalin17@gmail.com
- **Claude** (Anthropic) — AI pair programmer

## License

MIT
