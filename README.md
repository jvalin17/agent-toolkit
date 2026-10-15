# Agent Toolkit

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

Plain-English requests → requirements, architecture, TDD implementation, review, and commit gates. **19 roles**, **14 skills**, hooks that verify behavior (not agent claims).

Hosts: **Claude Code, Cursor, Gemini, Codex, Grok, Windsurf**, or any MCP/CLI client (Aider and others use `hosts/default.json`). Detection loads `hosts/<id>.json`; skills are short stubs with modules pulled on demand.

```
"Build a price comparison app for my inventory"
"Use /implementation to build a user auth system"
"use the security role to review auth"
```

Pipeline: [docs/workflow.md](docs/workflow.md) · Multi-host: [docs/other-llms.md](docs/other-llms.md)

---

## Quick start

```bash
# Any project
curl -s https://raw.githubusercontent.com/jvalin17/agent-toolkit/main/setup.sh | bash

# Claude Code (full hooks)
git clone https://github.com/jvalin17/agent-toolkit.git
cd agent-toolkit && ./install.sh
cd /path/to/your-project && claude

# Claude Code plugin
claude plugin marketplace add jvalin17/agent-toolkit
claude plugin install agent-toolkit

# MCP (Python 3.9+)
claude mcp add agent-toolkit -e PYTHONPATH=/path/to/agent-toolkit -- python3 -m toolkit_mcp
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | python3 -m toolkit_mcp

# Cursor / Codex / Grok / Windsurf (structural hooks)
./install.sh --host cursor --project /path/to/your-app

# Gemini (CLI gate — use atk for commits)
./install.sh --host gemini --project /path/to/your-app
python3 scripts/atk.py --project /path/to/your-app commit -m "message"

# Demos
./demos/run_demos.sh   # see demos/README.md
```

**Auto mode** (`gates.json`: `{ "auto": true }`):

```bash
agent-toolkit-continue "Build a price comparison feature"
# requirements → … → precommit; resumes via HANDOFF.md (cap 20 sessions)
```

---

## How it works

1. Open a project → roles auto-detect from files (e.g. React+Express+Prisma → frontend, backend, dba, security).
2. Ask for a change → matching roles inject checks; research/implement skills run as needed.
3. Commit → detected roles review in parallel; hooks verify session/tool evidence, not self-reports.

---

## What's included

### Roles (19)

| Category | Roles |
|----------|-------|
| Core | Backend, Frontend |
| Mobile | iOS, Android |
| Data | DBA, Data Engineer, Data Scientist |
| AI/ML | AI/ML Engineer |
| Infra | Infrastructure Engineer |
| Cross-cutting | Security, Production, QA, Architect, Code Health, Requirements, Research |
| Specialized | Game Dev, Embedded/IoT, Legal & Compliance |

Knowledge: foundational (SOLID, DDD, Clean Architecture, DDIA, GoF, OWASP, 12-Factor) + practical (95+ repos). Coding standards: C, C++, C#, Go, Java, Kotlin, MATLAB, Python, Rust, Swift, TypeScript.

### Skills (14)

| Skill | Role |
|-------|------|
| `/requirements` | Specs (front if missing) |
| `/architecture` | Design + tradeoffs |
| `/explore` | Codebase map |
| `/implementation` | TDD build |
| `/debug_tool` | Hypothesis debug on failure |
| `/reviewer` | Code/tests/runtime |
| `/evaluate` | Quality % gate |
| `/precommit` | Commit gate |
| `/assess` | Architecture fitness |
| `/agent-toolkit-mode` | Switch enforcement mode mid-session |
| `/setup` | Install/deploy scaffolding |
| `/status` | Dashboard |
| `/verify` | Output quality check (user judges usefulness) |
| `/updater` | Toolkit health |

### MCP tools (15)

| Tool | Purpose |
|------|---------|
| `select_agent` | Model for task type (haiku/sonnet/opus) |
| `build_plan` | Orchestration plan (+ host, pull_policy) |
| `plan_to_text` | Plan as injectable context |
| `get_role_context` | Detect roles + context |
| `list_roles` / `list_skills` / `list_agents` | Catalogs (19 / 14 / 9) |
| `build_research_plan` | Cheap fetch + expensive synthesize |
| `resolve_host` | Host detect + `hosts/*.json` |
| `get_bootstrap` | Short host bootstrap text |
| `get_skill` / `get_module` | Stub + on-demand module |
| `get_role` | Role context (compact/checks/full) |
| `run_function` | Allowlisted gates (`check_tdd_order`, `gate_status`) |
| `stamp_skill` | Skill stamp for non-Claude hosts |

Non-MCP: `scripts/toolkit_pull.py`, `generate-project-rules.sh` — [docs/other-llms.md](docs/other-llms.md).

### Model routing (hook-enforced for subagents)

`taxonomy_enforce.py` checks the `model` on every `Agent` spawn and blocks an expensive model on a cheap task or a cheap model on deep-reasoning work. It does not change the main session's model.

| Tier | Tasks | Relative cost |
|------|-------|---------|
| haiku | search, grep, lint, diff | lowest |
| sonnet | codegen, fixes, tests | mid |
| opus/fable | review, architecture, security | highest |

---

## Enforcement

Hooks block bypass. Agent text in `findings.json` is not trusted alone.

| Area | Checks |
|------|--------|
| **Code** | Precommit before `git commit`; TDD order + diff scan; lint re-run on finalize; skill required for edits (default/standard/safe) |
| **Anti-gaming** | HMAC-signed gate flags (key outside the repo); git gate sees through `bash -c`, env prefixes, absolute paths; default-deny on `.gates/`, `gates.json`, host settings, key files; env overrides can only strengthen; corrupt or deleted `gates.json` fails closed; repo-supplied test commands allowlisted; tamper-resistant skill stamps; execution-plan presence; review-depth; 20% spot checks; JSONL mechanical proof — trust boundary in [gate-unlock.md](shared/gate-unlock.md#trust-boundary--what-the-gates-do-and-do-not-stop) |
| **Process** | Plan → precommit compliance; reviewer gate; parallel role review; evidence required; model routing; UI regression hooks |
| **Session** | Canary greeting (optional `gates.json` `canary`); retry block after 3 identical errors; damage radius warn@5 / block@15; auto-continue ≤20 sessions |

> [Roles](roles/ROLES-FINAL.md) · [Role architecture](architecture/role-context-layer.md) · [Skills](docs/skills.md)

---

## Configuration

`gates.json` `"mode"`:

| Mode | TDD | Plan | Precommit | Reviewer | Depth | Spot |
|------|-----|------|-----------|----------|-------|------|
| `minimal` | — | — | — | — | — | — |
| `tdd` | yes | — | — | — | — | — |
| `planned` | — | yes | — | — | — | — |
| `guarded` | — | — | yes | — | — | — |
| **`default`** | yes | — | yes | — | — | — |
| `standard` | yes | yes | yes | — | yes | yes |
| `safe` | yes | yes | yes | yes | yes | yes |

```bash
/agent-toolkit-mode safe                          # mid-session
# gates.json: { "mode": "safe" }                  # permanent
AGENT_TOOLKIT_MODE=safe claude "Build auth"       # one session
agent-toolkit-setup --balanced                    # → default
agent-toolkit-setup --guarded                     # → standard
agent-toolkit-setup --lockdown                    # → safe
```

Other keys: `"canary": "Hey"` (or `""` off); `"roles"` / `"roles_add"` / `"roles_exclude"`. Full guide: [docs/configuration.md](docs/configuration.md).

---

## Advanced

| Feature | Command / doc |
|---------|----------------|
| Learn from repo/URL | `python3 roles/learn.py --role backend --repo <url>` |
| Bootstrap knowledge | `bash roles/bootstrap.sh` · `bash roles/bootstrap-books.sh` |
| Filter / audit | `python3 roles/learn.py --filter --role all` · `python3 roles/audit.py` |
| Auto-continue | `agent-toolkit-continue "…"` · [architecture/auto-continuation.md](architecture/auto-continuation.md) |
| Signed gates | [shared/gate-unlock.md](shared/gate-unlock.md) |
| Strict / orchestrator | [shared/strict-mode.md](shared/strict-mode.md) · [shared/orchestrator.md](shared/orchestrator.md) |

---

## Documentation

| Doc | For |
|-----|-----|
| [System overview](docs/system-overview.md) | How pieces connect |
| [Daily workflow](docs/workflow.md) | Pipeline, commit, push |
| [Install & updates](docs/install-and-updates.md) | Setup / sync |
| [Other LLMs](docs/other-llms.md) | Cursor, Gemini, Codex, … |
| [Demos](demos/README.md) | Sample apps |
| [Configuration](docs/configuration.md) | `gates.json` |
| [Roles](roles/ROLES-FINAL.md) | 19 roles |
| [Role architecture](architecture/role-context-layer.md) | Detect / learn / evaluate |
| [Guardrails](shared/guardrails.md) | G-* rules |
| [Troubleshooting](shared/troubleshooting.md) | Common issues |

---

## Contributing

PRs welcome. Open an issue with battle-tested patterns or bugs you caught.

## License

Apache 2.0 — see [LICENSE](LICENSE).
