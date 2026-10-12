# Agent Toolkit

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

Describe what you want in plain English. The toolkit's 19 specialized roles handle requirements, architecture, implementation, testing, security, and deployment — automatically.

```
"Build a price comparison app for my inventory"
"Add real-time notifications to my dashboard"
"Migrate this PHP app to Node.js"
```

Works with **Claude Code, Cursor, Gemini, Codex, Grok, Windsurf, Aider**, or any AI tool.
Host detection loads `hosts/<id>.json`; skills are **short stubs** with modules pulled on demand (MCP/CLI).
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

**Claude Code plugin:**

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

**Easiest way to start** — just tell your agent:

```
"Use /implementation to build a user auth system"
```

The skill handles everything: requirements check, execution plan, TDD, review, precommit. You approve the plan, then watch it build slab-by-slab.

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
  → Every detected role reviews in parallel
  → Each role checks from its expertise using book + repo knowledge
  → Hooks verify what actually happened — not what the agent claims
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

### MCP Tools (usable from any MCP client)

| Tool | Purpose |
|------|---------|
| `select_agent` | Best model for a task type (haiku/sonnet/opus) |
| `build_plan` | Deterministic orchestration plan (includes host + pull_policy) |
| `plan_to_text` | Render plan as injectable context |
| `get_role_context` | Detect roles + generate context for any AI tool |
| `list_roles` | All 19 roles with metadata |
| `list_skills` | All skills with descriptions |
| `list_agents` | All 9 sub-agents |
| `build_research_plan` | Fan-out research plan (cheap fetchers + expensive synthesizer) |
| `resolve_host` | Detect LLM host + merged `hosts/*.json` config |
| `get_bootstrap` | Short bootstrap text for the host |
| `get_skill` | Skill **stub** + module catalog |
| `get_module` | One skill module (depth on demand) |
| `get_role` | Role context at compact/checks/full |
| `run_function` | Allowlisted gates (`check_tdd_order`, `gate_status`) |
| `stamp_skill` | CLI skill stamp for non-Claude hosts |

Non-MCP hosts: `scripts/toolkit_pull.py` and `generate-project-rules.sh` (see [Other LLMs](docs/other-llms.md)).

### Model Routing (saves tokens, enforced by hooks)

| Task | Model | Cost |
|------|-------|------|
| File search, grep, lint, diff, compare | **haiku** | ~$0.25/MTok |
| Code generation, bug fix, test writing | **sonnet** | ~$3/MTok |
| Quality reviews, architecture, security | **opus/fable** | ~$15/MTok |

Wrong-tier usage is blocked automatically. Cheap tasks can't waste opus tokens; critical reviews can't cut corners with haiku.

---

## Enforcement

Hooks enforce quality at every step. The agent cannot bypass them.

### Code quality

| Check | What happens |
|-------|-------------|
| **Precommit gate** | `git commit` blocked without a passing `/precommit` |
| **TDD ordering** | Source file edits blocked until a test file exists or was recently edited |
| **Diff scan** | New functions without corresponding test functions → blocked |
| **Lint re-run** | Finalize re-runs lint independently — can't fake results |
| **Skill workflow required** | Code edits blocked without an active skill (default/standard/safe) |

### Anti-gaming

The agent can lie in `findings.json`. These checks catch it.

| Check | What it catches |
|-------|----------------|
| **Skill stamps** | Every skill invocation writes a tamper-proof stamp to `.gates/stamps/`. Agent can't forge, edit, or delete them. Finalize verifies stamps before trusting claims. |
| **Execution plan protection** | If `/implementation` ran but `execution-plan.json` is missing → blocked. Agent can't delete the plan to skip compliance. |
| **Review depth** | Reviewer stamp exists but no role agents spawned → blocked (safe/standard only). Catches shallow "I reviewed it" claims. |
| **Random spot checks** | 20% chance: mechanically scans 1-3 changed files for swallowed exceptions, TODO in error paths, hardcoded secrets (safe/standard only). |
| **Mechanical verification** | Session JSONL proves what happened — server starts, HTTP requests, TDD ordering, agent spawns. Overrides agent self-reports. |
| **No fabricated history** | Claims about prior behavior ("it used to...") blocked without git log/blame evidence. |

### Process

| Check | What happens |
|-------|-------------|
| **Execution plan** | `/implementation` writes a plan (slabs, roles, skills). `/precommit` blocks if any planned skill was skipped. |
| **Reviewer gate** | Code changes require `/reviewer`. Auto-invoked if skipped. |
| **Parallel role review** | Precommit spawns one reviewer per detected role in parallel. |
| **Evidence required** | Claims need concrete output — command results, file:line references. Not "it works". |
| **Model routing** | Agent subagent calls blocked if using the wrong model tier. |
| **UI regression detection** | UI file changes inject reviewer checks and offer Playwright test generation. |

### Session safety

| Check | What happens |
|-------|-------------|
| **Canary detection** | Agent must start responses with a greeting word. When it forgets → context loss detected. |
| **Retry loop detection** | Blocked after 3 identical errors. |
| **Damage radius** | Warns after 5 files edited, blocks after 15. |
| **Session limits** | Auto-continuation caps at 20 sessions. |

> [All 19 roles](roles/ROLES-FINAL.md) · [Architecture](architecture/role-context-layer.md) · [Skills reference](docs/skills.md)

---

## Configuration

Single `"mode"` field in `gates.json` controls all enforcement:

| Mode | TDD | Plan | Precommit | Reviewer | Depth checks | Spot checks |
|------|-----|------|-----------|----------|--------------|-------------|
| `minimal` | — | — | — | — | — | — |
| `tdd` | yes | — | — | — | — | — |
| `planned` | — | yes | — | — | — | — |
| `guarded` | — | — | yes | — | — | — |
| **`default`** | **yes** | — | **yes** | — | — | — |
| `standard` | yes | yes | yes | — | yes | yes |
| `safe` | yes | yes | yes | yes | yes | yes |

### How to set a mode

**Mid-session:**
```
/agent-toolkit-mode safe
```

**Permanent** — in `gates.json`:
```json
{ "mode": "safe" }
```

**One session only:**
```bash
AGENT_TOOLKIT_MODE=safe claude "Build the auth system"
```

**CLI presets:**
```bash
agent-toolkit-setup --balanced     # mode: default (TDD + precommit)
agent-toolkit-setup --guarded      # mode: standard (+ plan + depth checks)
agent-toolkit-setup --lockdown     # mode: safe (+ reviewer + spot checks)
```

### Other settings

Context-loss detection (on by default):
```json
{ "canary": "Hey" }
```
Every response starts with "Hey". When the agent forgets, a hook catches it. Set your name (`"canary": "Jean"`) or disable (`"canary": ""`).

Override roles:
```json
{
  "roles": ["backend", "frontend", "dba"],
  "roles_add": ["security"],
  "roles_exclude": ["infrastructure"]
}
```

> [Full configuration guide](docs/configuration.md)

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
| Set mode | `"mode": "safe"` in gates.json |
| Signed gates (CI/CD) | [shared/gate-unlock.md](shared/gate-unlock.md) |

> [Auto-continuation](architecture/auto-continuation.md) · [Strict mode](shared/strict-mode.md) · [Orchestrator](shared/orchestrator.md)

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
