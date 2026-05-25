# Agent Toolkit

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

Skills, guardrails, and structural hooks for AI coding agents. Plan, build, test, debug, and ship — any repo, any language.

**Best on [Claude Code](https://docs.anthropic.com/en/docs/claude-code)** — hooks enforce rules the model cannot bypass.  
**Also works on** Cursor, Codex, Gemini, Windsurf, Aider — via project rules ([setup guide](docs/other-llms.md)).

---

## What this is

| Piece | Purpose |
|-------|---------|
| **Skills** | Step-by-step workflows — `/explore`, `/implementation`, `/precommit`, … |
| **Guardrails** | Safety and quality rules ([`shared/guardrails.md`](shared/guardrails.md)) |
| **Hooks** | Structural enforcement on Claude Code — block bad writes, gate commits, route skills |

Prompt rules can be ignored. **Hooks cannot.** On other LLMs you get skills + guardrails via `AGENTS.md`; you enforce gates manually.

→ [System overview](docs/system-overview.md) · [Architecture docs](docs/README.md)

---

## Quick start

```bash
git clone https://github.com/jvalin17/agent-toolkit.git
cd agent-toolkit && ./install.sh          # once — needs python3, jq, Claude Code

cd /path/to/your-project && claude        # hooks inject context; look for "AGENT TOOLKIT ACTIVE"
/explore .                                # understand the codebase
/precommit                                # before commit (default gate)
```

Natural language works: *"fix the login bug"* routes to `/debug`. Chain hands-off: `/requirements auto my-app`.

Install details & updates: [docs/install-and-updates.md](docs/install-and-updates.md)

---

## Daily workflow

| When | Do this |
|------|---------|
| **Building** | `/explore` or `/requirements` → `/implementation` |
| **Committing** | `/precommit` → write findings → `finalize_report.py` → `git commit` |
| **Pushing** (guarded) | `/evaluate` → finalize → `git push` |

```bash
python3 hooks/finalize_report.py precommit .scratch/precommit_<slug>/findings.json
```

With defaults, only the hook writes `reports/` and `.gates/` — the agent cannot fake gate files.

→ Full commit/push flows: [docs/workflow.md](docs/workflow.md) · Gate profiles: [shared/gate-unlock.md](shared/gate-unlock.md)

---

## Skills

| Common | |
|--------|--|
| `/explore` | Understand existing code |
| `/requirements` | Gather requirements |
| `/implementation` | Build with TDD |
| `/precommit` | Quality gate before commit |
| `/debug` | Hypothesis-driven debugging |
| `/evaluate` | Quality score (push gate) |

All 13 skills: [docs/skills.md](docs/skills.md)

---

## Configuration

```bash
agent-toolkit-setup --status      # what's enabled
agent-toolkit-setup --guarded     # production preset
agent-toolkit-setup --lockdown    # strict + all reviews
```

Default: **legacy + block + minimal** — precommit required at commit, nothing extra at push.

→ All settings & presets: [docs/configuration.md](docs/configuration.md)

---

## Documentation

| Doc | For |
|-----|-----|
| [System overview](docs/system-overview.md) | How skills, hooks, gates, and reports connect |
| [Daily workflow](docs/workflow.md) | Commit, push, finalize, gate profiles |
| [Install & updates](docs/install-and-updates.md) | First setup, auto-sync, manual refresh |
| [Other LLMs](docs/other-llms.md) | Cursor, GPT, Gemini, Windsurf, Aider |
| [Skills reference](docs/skills.md) | All 13 skills |
| [Configuration](docs/configuration.md) | `gates.json`, presets, signed mode |
| [Gate unlock](shared/gate-unlock.md) | Legacy vs signed, rare options |
| [Troubleshooting](shared/troubleshooting.md) | Common failures |
| [Guardrails](shared/guardrails.md) | All G-* rules |
| [Architecture index](docs/README.md) | Design docs, requirements |

---

## Advanced

| Feature | Doc |
|---------|-----|
| Auto-continuation (long tasks) | [architecture/auto-continuation.md](architecture/auto-continuation.md) |
| Strict mode (anti-fake) | [shared/strict-mode.md](shared/strict-mode.md) |
| Signed gates (teams / CI) | [shared/gate-unlock.md](shared/gate-unlock.md) |
| Auto mode (`/skill auto`) | [shared/orchestrator.md](shared/orchestrator.md) |

---

## Contributing

PRs welcome. Open an issue with battle-tested patterns or bugs you caught.

## License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) (SPDX: `Apache-2.0`).
