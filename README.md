# Agent Toolkit

Reusable Claude Code skills for planning and building software projects. Works in any repo, any language.

## Skills

| Skill | What It Does |
|-------|-------------|
| `/requirements` | Gather requirements through structured questionnaire. Auto-scales from quick feature to full system design (QPS, storage, infrastructure, cost). |
| `/architecture` | Design system architecture with waterfall decision flow. Presents options with trade-offs — you decide. Covers data layer, API, security, scaling, design patterns. |
| `/implementation` | Build features with TDD by default. 5 modes: backend, frontend, security, ML/data, pipeline. Language-agnostic. |
| `/evaluate` | Grade agent output against the original prompt. Evidence-based — checks if what was asked actually got done. Optional after any skill. |
| `/updater` | Guardian of this repo. Audits skills for relevance, security, and standards compliance. Checks against Anthropic, Google, OpenAI best practices. |

Each skill generates a progress report in your project's `reports/` directory.

## Sub-Agents

Skills spawn these for parallel research when needed:

| Agent | Purpose |
|-------|---------|
| `functional-researcher` | How features work in other products |
| `scale-estimator` | Back-of-envelope math (QPS, storage, bandwidth) |
| `infrastructure-planner` | Servers, databases, caching, cost estimates |
| `tech-stack-advisor` | Tech options with trade-offs |
| `pattern-advisor` | Design patterns for specific problems |
| `scale-advisor` | What changes at each scale level |
| `test-generator` | Generate tests for existing code |
| `code-reviewer` | Quality, security, and principles review |

## Install

```bash
git clone https://github.com/jvalin17/agent-toolkit.git
cd agent-toolkit
./install.sh
```

This symlinks skills to `~/.claude/skills/` and agents to `~/.claude/agents/`. Available globally in any Claude Code session.

## Usage

Open any project in Claude Code and run:

```
/requirements job-agent
/architecture job-agent
/implementation backend
/evaluate                       # optional — grade the output
/updater                        # audit toolkit health
```

Skills read each other's output — run them in order for best results, or independently if you prefer.

## License

MIT
