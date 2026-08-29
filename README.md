# Agent Toolkit

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

Describe what you want in plain English. The toolkit's 19 specialized roles handle requirements, architecture, implementation, testing, security, and deployment — automatically.

```
"Build a price comparison app for my inventory"
"Add real-time notifications to my dashboard"
"Migrate this PHP app to Node.js"
```

Works with **Claude Code, Cursor, Gemini, Codex, Windsurf, Aider**, or any AI tool.

---

## What happens when you say "Build a price comparison app"

```
1. Requirements Engineer    → gathers specs, tracks what needs building
2. System Architect         → designs API + database + frontend approach
3. Research Engineer        → compares frameworks, picks best tools with evidence
4. Backend Engineer         → builds API with validation, pagination, caching
5. Frontend Engineer        → builds UI with lazy loading, no heavy computation on load
6. DBA                      → designs schema with indexes, cursor pagination
7. Security Engineer        → input validation, auth, no secrets in code
8. QA Engineer              → writes test suite, edge cases, E2E flows
9. Production Engineer      → runs the app, verifies everything works
10. /precommit              → role quality checks block bad code from committing
```

All automatic. 19 roles with two layers of knowledge:
- **Foundational** — SOLID, DDD, Clean Architecture, DDIA, GoF patterns, OWASP
- **Practical** — patterns from 95+ production repos (NestJS, Signal, PostHog, Kubernetes, etc.)

---

## Quick start

**Any AI tool** — open terminal in your project folder:

```bash
curl -s https://raw.githubusercontent.com/jvalin17/agent-toolkit/main/setup.sh | bash
```

**Claude Code** — full experience with auto mode:

```bash
git clone https://github.com/jvalin17/agent-toolkit.git
cd agent-toolkit && ./install.sh
cd /path/to/your-project && claude
```

**Auto mode** — builds entire features hands-free:

```bash
# In gates.json, set:
{ "auto": true }

# Then just describe what you want:
"Build a price comparison feature for utensils in my inventory"
# → requirements → architecture → implementation → testing → verification
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
  → Every detected role reviews in parallel (backend, dba, security, qa...)
  → Each role checks from its expertise using book + repo knowledge
  → Missing index? BLOCKED. No secrets check? BLOCKED.
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

Each role has two layers of knowledge:
- **Foundational** — SOLID, DDD, GoF design patterns, Clean Architecture, DDIA, OWASP, 12-Factor App
- **Practical** — patterns from 95+ production repos (NestJS, FastAPI, Signal, cal.com, PostHog, Kubernetes)

### 13 Skills

| Skill | Purpose |
|-------|---------|
| `/explore` | Understand existing code |
| `/requirements` | Gather and track requirements |
| `/architecture` | Design with tradeoffs |
| `/implementation` | Build with TDD |
| `/debug_tool` | Hypothesis-driven debugging |
| `/precommit` | Quality gate before commit |
| `/evaluate` | Quality score (push gate) |
| `/reviewer` | Code review |
| `/assess` | Architecture fitness |
| `/setup` | Generate install/deploy config |
| `/status` | Project dashboard |
| `/verify` | Verify changes work |
| `/updater` | Audit toolkit health |

### Enforcement (hooks — can't be bypassed)

- **Parallel role review** — every commit triggers all detected roles to review in parallel, each from its expertise
- **Precommit mandatory** — even `enforcement: "warn"` can't skip precommit
- **Skill enforcement** — strict mode blocks code edits without a skill workflow
- **Model routing** — haiku for search, sonnet for code, opus/fable for architecture. Hook warns on mismatches.
- **Evidence verification** — claims must have real output, not "it works"
- **Session audit** — mechanically tracks what the agent actually did
- **No excuses** — pre-existing lint issues must be fixed, not skipped

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
| Bootstrap repo knowledge | `bash roles/bootstrap.sh` (~$14, ~45 min) |
| Bootstrap book knowledge | `bash roles/bootstrap-books.sh` (~$7) |
| Filter knowledge | `python3 roles/learn.py --filter --role all` |
| Session audit | `python3 roles/audit.py` — verify what agent actually did |
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
