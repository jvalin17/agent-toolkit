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

**Auto mode** — builds entire features across sessions:

```bash
# Enable auto mode in gates.json:
{ "auto": true }

# Launch with the continuation wrapper:
agent-toolkit-continue "Build a price comparison feature for utensils in my inventory"
# → requirements → architecture → implementation → testing → verification
# Sessions restart automatically, picking up from HANDOFF.md
```

Roles activate automatically — no configuration needed. You can also invoke roles directly:

```
"use the security role to review auth"
"as DBA check these queries"
"ask backend to review the API"
```

Each role confirms its understanding before acting.

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
  → New function without test? BLOCKED. (git diff scan)
  → Agent claims "app verified" but no server started? BLOCKED. (JSONL audit)
  → Source file edited before test file? BLOCKED. (TDD ordering check)
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

- **Precommit mandatory** — `gate_hook.py` blocks `git commit` without a passing precommit gate, even in `enforcement: "warn"` mode
- **Model routing** — `taxonomy_enforce.py` blocks Agent subagent calls missing a `model` parameter or using the wrong tier (haiku for search, sonnet for code, opus for architecture)
- **Mechanical verification** — `compliance.py` reads session JSONL to verify server starts, HTTP requests, TDD file ordering, and role agent spawns. Agent self-reports are overridden by machine evidence.
- **Diff TDD check** — `compliance.py` scans the git diff for new functions without corresponding test functions; `finalize_report.py` blocks the precommit gate
- **TDD enforcement** — `tdd_enforce.py` blocks/reminds on Edit/Write of source files without a test file; `taxonomy_enforce.py` injects "write failing test FIRST" into implementation-like Agent subagent prompts
- **Skill enforcement** — `skill_enforce.py` in strict mode blocks code edits without an active skill workflow
- **Parallel role review** — precommit skill instructs the agent to spawn one reviewer per detected role in parallel; JSONL audit verifies role agents were actually spawned
- **Evidence verification** — `compliance.py` requires concrete output (command results, file:line references) — not "it works"
- **Session audit** — `compliance.py` reads Claude Code's JSONL log to track what the agent actually did (skills invoked, tools used, agents spawned)
- **Lint always passes** — `finalize_report.py` re-runs lint independently; any failure blocks the gate regardless of source

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
