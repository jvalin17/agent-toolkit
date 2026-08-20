# Agent Toolkit

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

Make any AI coding agent build production-quality software. 19 specialized roles, 13 skills, quality gates, and guardrails — works with **Claude Code, Cursor, Gemini, Codex, Windsurf, Aider**, or any AI tool.

---

## What this is

| Piece | Purpose |
|-------|---------|
| **Skills** | Step-by-step workflows — `/explore`, `/implementation`, `/precommit`, … |
| **Roles** | 19 specialized agents with domain knowledge learned from 95+ open-source repos |
| **Guardrails** | Safety and quality rules ([`shared/guardrails.md`](shared/guardrails.md)) |
| **Hooks** | Structural enforcement on Claude Code — block bad writes, gate commits, route skills |

Prompt rules can be ignored. **Hooks cannot.** On other LLMs you get skills + guardrails via `AGENTS.md`; you enforce gates manually.

→ [System overview](docs/system-overview.md) · [Architecture docs](docs/README.md)

---

## Quick start

### Any AI tool (Cursor, Gemini, Codex, Windsurf, etc.)

Open your terminal in your project folder and run:

```bash
curl -s https://raw.githubusercontent.com/jvalin17/agent-toolkit/main/setup.sh | bash
```

That's it. Now open your AI tool and start building — it has 19 specialized roles loaded.

### Claude Code (full experience with enforcement)

```bash
git clone https://github.com/jvalin17/agent-toolkit.git
cd agent-toolkit && ./install.sh

cd /path/to/your-project && claude
```

Claude Code gets the full experience: auto-detection, hooks that enforce quality, gates that block bad commits, and skill routing from natural language.

### What you can say (in any tool)

```
"Build a login page with email and password"
"Fix the slow database query"
"Add a REST API for user profiles"
"Make this app work on mobile"
"Set up Docker for this project"
"Review this code for security issues"
```

The toolkit's roles (backend, frontend, security, DBA, etc.) activate automatically based on your project and guide the AI to make better decisions.

Install details & updates: [docs/install-and-updates.md](docs/install-and-updates.md)

---

## Daily workflow

| When | Do this |
|------|---------|
| **Starting** | Roles auto-detect — look for "ACTIVE ROLES:" in session context |
| **Building** | `/explore` or `/requirements` → `/implementation` (roles inject domain knowledge) |
| **Committing** | `/precommit` → role quality checks + findings → `finalize_report.py` → `git commit` |
| **Pushing** (guarded) | `/evaluate` → finalize → `git push` |
| **Learning** | `python3 roles/learn.py --role backend --repo <url>` → study new patterns |

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

## Roles

19 specialized roles auto-detect from your project and inject domain expertise into every skill. Roles provide the **knowledge**, skills provide the **workflow**.

| Category | Roles |
|----------|-------|
| **Core** | Backend, Frontend |
| **Mobile** | iOS, Android |
| **Data** | DBA, Data Engineer, Data Scientist |
| **AI/ML** | AI/ML Engineer |
| **Infrastructure** | Infrastructure Engineer |
| **Cross-cutting** | Security, Production, QA, System Architect, Code Health, Requirements, Research |
| **Specialized** | Game Dev, Embedded/IoT |
| **Compliance** | Legal & Compliance |

### How it works

Roles activate automatically and inject domain knowledge into every skill:

```
You open a React + Express + Prisma project
  → detect_role.py detects: frontend, backend, dba, security
  → Each role's advisory + learned knowledge injected into session

You type: "add a stats page"
  → /implementation runs with role context:
    Frontend: "don't compute stats on page load — defer to Web Worker"
    Backend:  "paginate with cursors, not OFFSET"
    DBA:      "add index on player_id"
    Security: "validate input at API boundary"

You run /precommit
  → Role quality checks run against your code
  → Backend: ✓ pagination on list endpoint
  → DBA: ✗ missing index on foreign key → BLOCKED
```

### Examples

```bash
# Study a new repo to improve a role's knowledge
python3 roles/learn.py --role backend --repo https://github.com/honojs/hono

# Study a blog post
python3 roles/learn.py --role frontend --url https://vercel.com/blog/core-web-vitals

# Study your own codebase (all roles analyze it)
python3 roles/learn.py --role all --path /path/to/project

# Merge learnings into runtime knowledge
python3 roles/learn.py --synthesize backend

# Filter knowledge — remove opinions, keep objective patterns
python3 roles/learn.py --filter --role all

# Check knowledge freshness
python3 roles/learn.py --health backend
```

### Greenfield app example

Starting a new project from scratch with roles:

```bash
mkdir my-saas && cd my-saas
git init && claude

# You: "Build a SaaS app with auth, payments, and a dashboard"

# What happens:
# 1. /requirements gathers specs — Requirements Engineer tracks completeness
# 2. /architecture designs system — System Architect evaluates tradeoffs
#    Research Engineer compares: Next.js vs Remix, Prisma vs Drizzle, Stripe vs Paddle
#    Requirements Engineer documents tech choices with rationale
# 3. /implementation builds slab by slab:
#    - Backend role: API with validation, pagination, error handling
#    - Frontend role: lazy-loaded components, no heavy computation on mount
#    - DBA role: indexed foreign keys, cursor pagination, parameterized queries
#    - Security role: bcrypt passwords, CSRF protection, no secrets in code
# 4. /precommit: all role quality checks must pass before commit
# 5. Production Engineer: run the app, click through flows, verify it works
```

No configuration needed — roles detect from the files you create (package.json, Prisma schema, Dockerfile) and activate automatically.

### Configuration

Roles auto-detect by default. Override in `gates.json`:

```json
{
  "roles": ["backend", "frontend", "dba"],
  "roles_add": ["security"],
  "roles_exclude": ["infrastructure"],
  "roles_max": 4
}
```

### Bootstrap knowledge

Pre-learn from 95+ production repos (NestJS, FastAPI, Signal, cal.com, PostHog, Kubernetes, etc.):

```bash
read -s -p 'API key: ' ANTHROPIC_API_KEY && export ANTHROPIC_API_KEY
bash roles/bootstrap.sh    # ~45-90 min, ~$14-18
unset ANTHROPIC_API_KEY
```

Knowledge stored in `roles/knowledge.json` — one JSON file, easy to review and edit.

### Manager guardrail

8 principles injected into every session when roles are active:

1. **QUALITY** — check anti-patterns before implementing
2. **SCOPE** — solve exactly what was asked
3. **DEPENDENCIES** — check all applicable roles
4. **RISK** — address flagged risks, don't defer
5. **ESCALATION** — follow user when guidance conflicts
6. **INFORM** — surface concerns + alternatives, let user decide
7. **USE SKILLS** — roles provide knowledge, skills provide process — use both
8. **ROLE CHECKS** — apply role quality checks in every skill

### Tool-specific setup details

| Tool | How roles load | Setup |
|------|---------------|-------|
| **Claude Code** | Automatic via hooks | `./install.sh` (once) |
| **Cursor** | `.cursor/rules/roles.md` | `python3 roles/context.py --setup` |
| **Gemini** | `.gemini/rules/roles.md` | `python3 roles/context.py --setup` |
| **Codex / Windsurf / other** | `AGENTS.md` | `python3 roles/context.py --setup` |

→ Architecture: [`architecture/role-context-layer.md`](architecture/role-context-layer.md) · Roles: [`roles/ROLES-FINAL.md`](roles/ROLES-FINAL.md)

---

## Configuration

All settings live in **`gates.json`** at your project root. Use presets or edit directly.

```bash
agent-toolkit-setup --status      # show current config
agent-toolkit-setup --balanced    # daily dev (default)
agent-toolkit-setup --guarded     # production
agent-toolkit-setup --lockdown    # strict + all reviews
agent-toolkit-setup --tdd off     # toggle one setting
```

### Presets

| Preset | Commit requires | Push requires | Use when |
|--------|----------------|---------------|----------|
| **balanced** (default) | `/precommit` | — | Daily development |
| **guarded** | `/precommit` | `/evaluate` | Production branches |
| **lockdown** | `/precommit` + `/evaluate` | `/evaluate` + `/reviewer` + `/assess` | High-risk changes |
| **quick** | — | — | Local experiments only |

### All settings

#### Gate enforcement

| Setting | Values | Default | What it does |
|---------|--------|---------|--------------|
| `enforcement` | `block` / `warn` | `block` | Whether missing gates prevent or just warn on commit/push |
| `profile` | `minimal` / `standard` / `strict` / `paranoid` | `minimal` | Which skills are required at commit and push |
| `gate_mode` | `legacy` / `signed` | `legacy` | How gates are verified — `signed` uses JWT for teams/CI |
| `eval_threshold` | `0`–`100` | `95` | Minimum `/evaluate` score to pass the push gate |

**Examples:**

```jsonc
// Block commits that skip /precommit (default behavior)
"enforcement": "block"

// Just warn (useful when rolling out gates on an existing project)
"enforcement": "warn"

// Require /evaluate before push (production branches)
"profile": "standard"

// Require /evaluate + /reviewer + /assess before push (high-risk)
"profile": "paranoid"

// Use JWT-signed gates (team repos with branch protection)
"gate_mode": "signed"

// Lower the bar for evaluate score (e.g. early prototypes)
"eval_threshold": 80
```

#### TDD & quality

| Setting | Values | Default | What it does |
|---------|--------|---------|--------------|
| `tdd` | `true` / `false` | `true` | Enable test-first workflow enforcement |
| `tdd_mode` | `remind` / `strict` | `remind` | `remind` = advisory nudge; `strict` = hard-blocks source edits until tests exist |

**Examples:**

```jsonc
// Nudge to write tests first but don't block (default)
"tdd": true, "tdd_mode": "remind"

// Hard-block: cannot edit src/ until a failing test exists
"tdd": true, "tdd_mode": "strict"

// Disable TDD enforcement entirely (not recommended)
"tdd": false
```

#### Security & anti-fake

| Setting | Values | Default | What it does |
|---------|--------|---------|--------------|
| `gate_protect` | `true` / `false` | `true` | Block agent from writing `.gates/` files directly |
| `report_protect` | `true` / `false` | `true` | Block agent from writing `reports/` files directly |
| `mode` | `normal` / `strict` | `normal` | `strict` enables anti-fake drift detection on fixtures |

**Examples:**

```jsonc
// Default: agent cannot fake passing gates or reports
"gate_protect": true, "report_protect": true

// Strict anti-fake: detect drift in test fixtures and gate provenance
"mode": "strict"

// Disable protections (only for debugging the toolkit itself)
"gate_protect": false, "report_protect": false
```

#### Session behavior

| Setting | Values | Default | What it does |
|---------|--------|---------|--------------|
| `compact_at_minutes` | `0`+ | `70` | Layer 1: write HANDOFF.md breadcrumb at this time; session continues |
| `max_session_minutes` | `0`+ | `200` | Layer 2: hard stop — session ends with restart prompt |
| `continue` | `true` / `false` | `true` | Auto-restart session when context is exhausted (headless) |
| `skill_routing` | `true` / `false` | `true` | Auto-detect user intent and route to the matching skill |
| `auto` | `true` / `false` | `false` | Run skills in auto mode (no confirmation prompts) |
| `model` | `auto` / model name | `auto` | Override which model the agent uses |

Sessions use a **two-layer** limit system. Layer 1 (`compact_at_minutes`) writes HANDOFF.md as a breadcrumb so the agent can re-orient after compaction — the session keeps running. Layer 2 (`max_session_minutes`, or 1 compaction, or 700KB output) is a hard stop that writes HANDOFF.md with a restart prompt you can paste into a new session.

**Examples:**

```jsonc
// Two-layer defaults: breadcrumb at 70 min, hard stop at 200 min
"compact_at_minutes": 70, "max_session_minutes": 200

// Shorter sessions (e.g. for cost control)
"compact_at_minutes": 30, "max_session_minutes": 60

// Disable Layer 1 breadcrumb (only hard stop at 200 min)
"compact_at_minutes": 0

// Auto-restart when context runs out (headless mode)
"continue": true

// Keep session alive with warnings only (no restart)
"continue": false

// Disable skill routing (manual /skill invocation only)
"skill_routing": false

// Run skills without asking for confirmation
"auto": true

// Pin to a specific model
"model": "opus"
```

#### Project commands

| Setting | Values | Default | What it does |
|---------|--------|---------|--------------|
| `test_command` | shell command | `"python3 -m pytest tests/ -q"` | Command the toolkit runs to execute tests |
| `lint_command` | shell command | `"python3 -m compileall -q ..."` | Command the toolkit runs to lint/check code |

**Examples:**

```jsonc
// Node.js project
"test_command": "npm test",
"lint_command": "npm run lint"

// Go project
"test_command": "go test ./...",
"lint_command": "golangci-lint run"

// Rust project
"test_command": "cargo test",
"lint_command": "cargo clippy"

// Python with coverage
"test_command": "python3 -m pytest tests/ --cov=src -q",
"lint_command": "ruff check ."
```

### Example: full config

```json
{
  "enforcement": "block",
  "profile": "standard",
  "gate_mode": "legacy",
  "eval_threshold": 95,
  "tdd": true,
  "tdd_mode": "remind",
  "gate_protect": true,
  "report_protect": true,
  "mode": "normal",
  "continue": true,
  "compact_at_minutes": 70,
  "max_session_minutes": 200,
  "skill_routing": true,
  "auto": false,
  "model": "auto",
  "test_command": "npm test",
  "lint_command": "npm run lint"
}
```

→ Full reference: [docs/configuration.md](docs/configuration.md) · Signed gates: [shared/gate-unlock.md](shared/gate-unlock.md)

---

## Documentation

| Doc | For |
|-----|-----|
| [System overview](docs/system-overview.md) | How skills, hooks, gates, roles, and reports connect |
| [Daily workflow](docs/workflow.md) | Commit, push, finalize, gate profiles |
| [Install & updates](docs/install-and-updates.md) | First setup, auto-sync, manual refresh |
| [Other LLMs](docs/other-llms.md) | Cursor, GPT, Gemini, Windsurf, Aider |
| [Skills reference](docs/skills.md) | All 13 skills |
| [Roles reference](roles/ROLES-FINAL.md) | All 19 roles, interactions, knowledge sources |
| [Role architecture](architecture/role-context-layer.md) | How roles detect, inject, learn, evaluate |
| [Configuration](docs/configuration.md) | `gates.json`, presets, signed mode |
| [Gate unlock](shared/gate-unlock.md) | Legacy vs signed, rare options |
| [Troubleshooting](shared/troubleshooting.md) | Common failures |
| [Guardrails](shared/guardrails.md) | All G-* rules |
| [Architecture index](docs/README.md) | Design docs, requirements |

---

## Advanced

| Feature | What it does |
|---------|-------------|
| Auto-continuation | Long tasks auto-restart across sessions · `agent-toolkit-continue "Build auth"` |
| Bootstrap knowledge | Study 95+ repos to improve role knowledge · `bash roles/bootstrap.sh` |
| Learn new patterns | `python3 roles/learn.py --role backend --repo <url>` |
| Filter knowledge | Remove opinions, keep objective patterns · `python3 roles/learn.py --filter --role all` |
| TDD strict mode | `"tdd_mode": "strict"` — blocks source edits until tests exist |
| Signed gates (teams) | JWT-based gate verification for CI/CD · [shared/gate-unlock.md](shared/gate-unlock.md) |
| Auto mode | Run skills without confirmation · `"auto": true` |

→ [Auto-continuation architecture](architecture/auto-continuation.md) · [Strict mode](shared/strict-mode.md) · [Orchestrator](shared/orchestrator.md)

---

## Troubleshooting

### `finalize_report.py: No such file or directory`

The skill tried to run `finalize_report.py` using a relative path from a different project directory. Ensure the skill SKILL.md files use the absolute path:

```bash
python3 /path/to/agent-toolkit/hooks/finalize_report.py <skill> .scratch/<skill>_<slug>/findings.json
```

### `BLOCKED: git commit requires precommit skill`

The gate hook blocks commits when no `gates.json` is found, assuming the project is toolkit-managed. Two fixes:

1. **Upgrade the toolkit** — the latest gate hook skips enforcement for repos without `gates.json`
2. **Temporary bypass** — set the env var before your commit:
   ```bash
   AGENT_TOOLKIT_ENFORCEMENT=warn git commit -m "your message"
   ```

### `Run install.sh in project root`

The legacy fallback triggers when `gates.json` exists but has no `commit_requires`. Either:
- Add `"commit_requires": ["precommit"]` to `gates.json` and run `/precommit`
- Or remove `gates.json` to opt out of gating entirely

---

## Contributing

PRs welcome. Open an issue with battle-tested patterns or bugs you caught.

## License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) (SPDX: `Apache-2.0`).
