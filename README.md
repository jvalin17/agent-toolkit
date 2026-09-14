# Agent Toolkit

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

Describe what you want in plain English. The toolkit's 19 specialized roles handle requirements, architecture, implementation, testing, security, and deployment — automatically.

```
"Build a price comparison app for my inventory"
"Add real-time notifications to my dashboard"
"Migrate this PHP app to Node.js"
```

Works with **Claude Code, Cursor, Gemini, Codex, Windsurf, Aider**, or any AI tool.
Also available as a **Claude Code plugin** and **MCP server**.

---

## What happens when you say "Build a price comparison app"

```
 1. /requirements            → gathers specs, tracks what needs building
 2. /architecture            → designs API + database + frontend approach
 3. /explore                 → maps codebase, conventions, existing patterns
 4. Research agents          → compares frameworks, picks best tools with evidence
 5. /implementation Step 0   → shows EXECUTION PLAN: slabs, roles, skills per slab
                               → user confirms before first line of code
 6. /implementation          → builds with TDD, slab-by-slab (sonnet — cheap)
 7. /reviewer                → judges code quality, tests, runtime (opus — thorough)
 8. /evaluate                → scores quality % — must pass threshold (opus)
 9. /precommit               → verifies execution plan was followed, blocks if not
10. On test failure           → /debug_tool (hypothesis-driven, not retry loops)
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

**Claude Code plugin** — installs skills, agents, hooks, and MCP server:

```bash
claude plugin marketplace add jvalin17/agent-toolkit
claude plugin install agent-toolkit
```

**MCP server** — zero dependencies, any Python 3.9+:

```bash
# Add to Claude Code
claude mcp add agent-toolkit -- python3 -m toolkit_mcp

# Or pipe JSON-RPC directly
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | python3 -m toolkit_mcp
```

**Auto mode** — builds entire features across sessions:

```bash
# Enable auto mode in gates.json:
{ "auto": true }

# Launch with the continuation wrapper (max 20 sessions, configurable):
agent-toolkit-continue "Build a price comparison feature for utensils in my inventory"
# → requirements → architecture → explore → implementation → reviewer → evaluate → precommit
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

Coding standards for 11 languages: C, C++, C#, Go, Java, Kotlin, MATLAB, Python, Rust, Swift, TypeScript.

### 14 Skills (orchestrator chains them automatically)

| Skill | Purpose | Pipeline position |
|-------|---------|-------------------|
| `/requirements` | Gather and track requirements | Front (if missing) |
| `/architecture` | Design with tradeoffs | Front (if missing) |
| `/explore` | Understand existing code | Before implementation |
| `/implementation` | Build with TDD | Build step |
| `/debug_tool` | Hypothesis-driven debugging | On test failure |
| `/reviewer` | Code review, tests, runtime | After implementation |
| `/evaluate` | Quality score (% gate) | After reviewer |
| `/precommit` | Final commit gate | Before commit |
| `/assess` | Architecture fitness | Final quality |
| `/readme` | Validate README line-by-line | Called by precommit |
| `/setup` | Generate install/deploy config | New projects |
| `/status` | Project dashboard | On demand |
| `/verify` | Verify changes work | Legacy (absorbed by reviewer) |
| `/updater` | Audit toolkit health | Maintenance |

### 8 MCP Tools (usable from any MCP client)

| Tool | Purpose |
|------|---------|
| `select_agent` | Best model for a task type (haiku/sonnet/opus) |
| `build_plan` | Deterministic orchestration plan |
| `plan_to_text` | Render plan as injectable context |
| `get_role_context` | Detect roles + generate context for any AI tool |
| `list_roles` | All 19 roles with metadata |
| `list_skills` | All skills with descriptions |
| `list_agents` | All 9 sub-agents |
| `build_research_plan` | Fan-out research plan (cheap fetchers + expensive synthesizer) |

### Model Routing (saves tokens, enforced by hooks)

| Task | Model | Cost |
|------|-------|------|
| File search, grep, lint, diff, compare | **haiku** | ~$0.25/MTok |
| Code generation, bug fix, test writing | **sonnet** | ~$3/MTok |
| Quality reviews, architecture, security | **opus/fable** | ~$15/MTok |

`taxonomy_enforce.py` blocks every Agent subagent call that uses the wrong tier. Cheap tasks can't waste opus tokens; critical reviews can't cut corners with haiku.

### Enforcement (hooks — can't be bypassed)

- **Precommit mandatory** — `gate_hook.py` blocks `git commit` without a passing precommit gate, even in `enforcement: "warn"` mode
- **Model routing** — `taxonomy_enforce.py` blocks Agent subagent calls missing a `model` parameter or using the wrong tier
- **Execution plan enforcement** — `/implementation` writes an execution plan (slabs, roles, skills); `/precommit` reads it and blocks if any planned skill was skipped
- **Reviewer gate** — `/precommit` verifies `/reviewer` was called on code changes; auto-invokes it if skipped
- **UI regression detection** — hooks detect UI file changes and inject reviewer checks (overflow, empty states, a11y); offer to generate Playwright E2E tests
- **Retry loop detection** — `session_monitor.py` blocks after 3 identical errors; clears on success (G-IMPL-9)
- **Damage radius limit** — warns after 5 unique files edited, blocks after 15 (G-IMPL-10)
- **No fabricated history** — G-IMPL-8 blocks claims about prior code behavior without git log/blame evidence
- **Mechanical verification** — `compliance.py` reads session JSONL to verify server starts, HTTP requests, TDD file ordering, and role agent spawns. Agent self-reports are overridden by machine evidence.
- **Diff TDD check** — `compliance.py` scans the git diff for new functions without corresponding test functions; `finalize_report.py` blocks the precommit gate
- **TDD enforcement** — `tdd_enforce.py` blocks/reminds on Edit/Write of source files without a test file; `taxonomy_enforce.py` injects "write failing test FIRST" into implementation-like Agent subagent prompts
- **Skill enforcement** — `skill_enforce.py` in strict mode blocks code edits without an active skill workflow
- **Parallel role review** — precommit spawns one reviewer per detected role in parallel (opus); skips if `/reviewer` already ran
- **Evidence verification** — `compliance.py` requires concrete output (command results, file:line references) — not "it works"
- **Session audit** — `compliance.py` reads Claude Code's JSONL log to track what the agent actually did (skills invoked, tools used, agents spawned)
- **Session limits** — `auto_continue.py` caps at 20 sessions (configurable via `AGENT_TOOLKIT_MAX_SESSIONS`), preventing infinite restart loops
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
