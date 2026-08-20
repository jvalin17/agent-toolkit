# Agent Toolkit

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

Make any AI coding agent build production-quality software. 19 specialized roles, 13 skills, quality gates, and guardrails — works with **Claude Code, Cursor, Gemini, Codex, Windsurf, Aider**, or any AI tool.

---

## Quick start

**Any AI tool** — open terminal in your project folder:

```bash
curl -s https://raw.githubusercontent.com/jvalin17/agent-toolkit/main/setup.sh | bash
```

**Claude Code** — full experience with enforcement:

```bash
git clone https://github.com/jvalin17/agent-toolkit.git
cd agent-toolkit && ./install.sh
cd /path/to/your-project && claude
```

Then just talk to your AI:

```
"Build a login page with email and password"
"Fix the slow database query"
"Add a REST API for user profiles"
"Review this code for security issues"
```

Roles activate automatically — no configuration needed.

---

## How it works

```
You open a React + Express + Prisma project
  → Roles auto-detect: frontend, backend, dba, security
  → Domain knowledge injected into every interaction

You say: "add a stats page"
  → Frontend: "don't compute on page load — use Web Worker"
  → Backend:  "paginate with cursors, not OFFSET"
  → DBA:      "add index on player_id"
  → Security: "validate input at API boundary"

You commit
  → Role quality checks run → missing index? BLOCKED
```

---

## What's included

### 19 Roles (auto-detected from your project files)

| Category | Roles |
|----------|-------|
| **Core** | Backend, Frontend |
| **Mobile** | iOS, Android |
| **Data** | DBA, Data Engineer, Data Scientist |
| **AI/ML** | AI/ML Engineer |
| **Infrastructure** | Infrastructure Engineer |
| **Cross-cutting** | Security, Production, QA, Architect, Code Health, Requirements, Research |
| **Specialized** | Game Dev, Embedded/IoT, Legal & Compliance |

Each role has domain knowledge learned from 95+ production open-source repos (NestJS, FastAPI, Signal, cal.com, PostHog, Kubernetes, etc.).

### 13 Skills

| Skill | Purpose |
|-------|---------|
| `/explore` | Understand existing code |
| `/requirements` | Gather and track requirements |
| `/architecture` | Design with tradeoffs |
| `/implementation` | Build with TDD |
| `/debug` | Hypothesis-driven debugging |
| `/precommit` | Quality gate before commit |
| `/evaluate` | Quality score (push gate) |
| `/reviewer` | Code review |
| `/assess` | Architecture fitness |
| `/setup` | Generate install/deploy config |
| `/status` | Project dashboard |
| `/verify` | Verify changes work |
| `/updater` | Audit toolkit health |

### Quality gates

Code can't be committed unless it passes role quality checks. Security violations are hard blocks. The agent cannot fake gate results — hooks enforce this.

→ [All 19 roles](roles/ROLES-FINAL.md) · [Architecture](architecture/role-context-layer.md) · [Skills reference](docs/skills.md)

---

## Configuration

All settings in `gates.json`. Quick presets:

```bash
agent-toolkit-setup --balanced     # daily dev (default)
agent-toolkit-setup --guarded      # production branches
agent-toolkit-setup --lockdown     # high-risk changes
```

Override roles:

```json
{
  "roles": ["backend", "frontend", "dba"],
  "roles_add": ["security"],
  "roles_exclude": ["infrastructure"]
}
```

→ [Full configuration guide](docs/configuration.md)

---

## Advanced

| Feature | Command |
|---------|---------|
| Study new repos | `python3 roles/learn.py --role backend --repo <url>` |
| Study blog posts | `python3 roles/learn.py --role frontend --url <url>` |
| Bootstrap all knowledge | `bash roles/bootstrap.sh` (~$14, ~45 min) |
| Filter knowledge | `python3 roles/learn.py --filter --role all` |
| Auto-continuation | `agent-toolkit-continue "Build auth system"` |
| TDD strict mode | `"tdd_mode": "strict"` in gates.json |
| Signed gates (CI/CD) | [shared/gate-unlock.md](shared/gate-unlock.md) |

→ [Auto-continuation](architecture/auto-continuation.md) · [Strict mode](shared/strict-mode.md) · [Orchestrator](shared/orchestrator.md)

---

## Documentation

| Doc | For |
|-----|-----|
| [System overview](docs/system-overview.md) | How everything connects |
| [Daily workflow](docs/workflow.md) | Commit, push, gate flows |
| [Install & updates](docs/install-and-updates.md) | Setup and sync |
| [Other LLMs](docs/other-llms.md) | Cursor, Gemini, Codex, Windsurf |
| [Configuration](docs/configuration.md) | All gates.json settings |
| [Roles](roles/ROLES-FINAL.md) | 19 roles with interactions |
| [Role architecture](architecture/role-context-layer.md) | How roles detect, learn, evaluate |
| [Guardrails](shared/guardrails.md) | All G-* rules |
| [Troubleshooting](shared/troubleshooting.md) | Common issues |

---

## Contributing

PRs welcome. Open an issue with battle-tested patterns or bugs you caught.

## License

Apache 2.0 — see [LICENSE](LICENSE).
