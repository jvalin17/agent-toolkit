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

**Auto-continuation** is on by default (`"continue": true` in `gates.json`). When context is exhausted, the hook writes `HANDOFF.md` and automatically relaunches a fresh session. No wrapper needed. Set `"continue": false` to disable (session will warn but keep running).

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
| `continue` | `true` / `false` | `true` | Auto-restart session when context is exhausted |
| `max_session_minutes` | `0`+ | `0` | Time limit per session in minutes; `0` = unlimited |
| `skill_routing` | `true` / `false` | `true` | Auto-detect user intent and route to the matching skill |
| `auto` | `true` / `false` | `false` | Run skills in auto mode (no confirmation prompts) |
| `model` | `auto` / model name | `auto` | Override which model the agent uses |

**Examples:**

```jsonc
// Auto-restart when context runs out (default)
"continue": true

// Keep session alive with warnings only (no restart)
"continue": false

// Cap sessions at 30 minutes
"max_session_minutes": 30

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
  "max_session_minutes": 0,
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
| TDD strict mode | `"tdd_mode": "strict"` in `gates.json` — blocks source edits until tests exist |
| Strict mode (anti-fake) | [shared/strict-mode.md](shared/strict-mode.md) |
| Signed gates (teams / CI) | [shared/gate-unlock.md](shared/gate-unlock.md) |
| Auto mode (`/skill auto`) | [shared/orchestrator.md](shared/orchestrator.md) |

---

## Contributing

PRs welcome. Open an issue with battle-tested patterns or bugs you caught.

## License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) (SPDX: `Apache-2.0`).
