# Agent Toolkit

[![Skills: 13](https://img.shields.io/badge/Skills-13-blue?style=for-the-badge)](skills/)
[![Agents: 9](https://img.shields.io/badge/Agents-9-green?style=for-the-badge)](agents/)
[![Structural hooks: 9](https://img.shields.io/badge/Structural_hooks-9-purple?style=for-the-badge)](hooks/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-yellow?style=for-the-badge)](LICENSE)
[![Health Check](https://img.shields.io/badge/Health_Check-twice_monthly-brightgreen?style=for-the-badge)](.github/workflows/updater.yml)

Production-ready skills for AI coding agents. 13 skills, 9 agents, 21 guardrail groups, 9 structural hooks. Plan, build, test, debug, and ship — any repo, any language.

Built for **Claude Code** (structural hooks + gates). Portable to Codex, Cursor, Gemini CLI, Windsurf, Aider (skills + guardrails via `AGENTS.md`; no structural hooks).

## Quick Start

```bash
git clone https://github.com/jvalin17/agent-toolkit.git
cd agent-toolkit
./install.sh    # symlinks skills + agents + shared; installs structural hooks
```

In any project:

```bash
/requirements auto my-app    # auto mode — chains skills, 95% eval gate
/requirements my-app         # interactive — you approve each step
/explore .                   # existing codebase — recon first
./generate-project-rules.sh  # non-Claude: flatten rules into AGENTS.md
```

Re-run `./install.sh` once if hooks were missing on first install; `update.sh` auto-pulls the toolkit before each skill after that.

In a **git project**, install also bootstraps gates (`.agent-toolkit/`, `gates.json`, optional signing key + CI workflow). Default: **legacy + block + minimal**. Details: [`shared/gate-unlock.md`](shared/gate-unlock.md).

## How It Works

| Layer | What |
|-------|------|
| **Skills (13)** | Workflows — `/implementation`, `/debug`, `/precommit`, … Interactive or `auto` (chains until ambiguity or failure). |
| **Guardrails (21 groups)** | Rules every skill follows — see [Guardrails](#guardrails) and [`shared/guardrails.md`](shared/guardrails.md). |
| **Structural hooks (9)** | Runtime enforcement the model cannot bypass — routing, TDD reminders, session limits, commit/push gates, doc-guard. |

### When to use what

| Situation | Approach |
|-----------|----------|
| Quick prototype | `/requirements auto my-app` |
| Production / careful build | `/requirements` → `/architecture` → `/implementation` |
| Existing codebase | `/explore .` → `/implementation` for new work |
| Fix a bug | Say "fix the login bug" — `route_to_skill.py` routes to `/debug` |
| Refactor | `/implementation refactor auth` |
| Before release | `/reviewer` + `/evaluate` |
| Architecture review | `/assess` |
| Long task, walk away | `python3 scripts/auto_continue.py "goal"` |

## Skills

| Skill | What It Does |
|-------|-------------|
| `/explore` | Understand any codebase. 4-phase: recon, architecture, conventions, issues. |
| `/requirements` | Gather requirements. Draft early after Q1+Q4, deepen on demand. |
| `/architecture` | Design with trade-offs. Reuse check. User journey mandatory. |
| `/implementation` | TDD. Walking skeleton → feature slabs. Fix, refactor, demo modes. |
| `/debug` | Hypothesis-driven. Layer-by-layer. Reproduce with test, then fix. |
| `/assess` | Architecture fitness. Scale-aware thresholds. Safe refactoring. |
| `/verify` | Is the output useful, not just correct? Session health. User confirms. |
| `/precommit` | Quality gate. Instructions, tests, standards, app verification, README. |
| `/reviewer` | Deep audit: code + tests + a11y + dependencies + UI. |
| `/evaluate` | 5-dimension percentage score. Not lenient. |
| `/setup` | Install scripts, Docker, Makefile, README. One command. |
| `/status` | Project dashboard. What's done, what's next. |
| `/updater` | Toolkit health: links, freshness, standards. |

## Structural hooks

Guardrails and skills are prompts — the model can ignore them. **Structural hooks** (Claude Code `PreToolUse` / `SessionStart` scripts) inject context and block tool use — **the model cannot bypass them**. This is not MCP; hooks are shell commands in `~/.claude/settings.json` via `./install.sh`.

| Hook | When | What |
|------|------|------|
| `session_init.py` | Session start + after `/compact` | Loads project `.md` rules, init counters, clears stale `.gates/`, HANDOFF.md continuation context injection. |
| `session_monitor.py` | PreToolUse + PostToolUse + UserPromptSubmit + PostCompact | Context-pressure limits: cumulative output bytes, PostCompact detection, exchange fallback (30). Blocks writes to `.session/` (G-SESSION-1). In strict mode: drift detection, periodic integrity checks, patch-forward detection. |
| `route_to_skill.py` | Every prompt | Intent → skill injection ("fix bug" → `/debug`, "build X" → `/implementation`). |
| `gate.py` | Before `git commit` / `git push` | Legacy: `.gates/*-passed`. Signed: JWT. Default `enforcement: block`. Auto-escalates warn→block on first violation. |
| `skill_passed.py` | After skill completes | Reports gate status (does not issue tokens). |
| `tdd_enforce.py` | Before file edit | TDD reminder if no test file exists. |
| `check_doc_write.sh` | Before file write | Blocks writes outside git repository root (monorepo-safe). User confirms cross-repo writes. |
| `gate_cleanup.py` | After commit | Clears flags / token for next cycle. |
| `update.sh` | Before each skill | Auto-pull toolkit. |

**Gates:** Most users stay on **legacy** (short sessions, no secrets). **Signed** is optional for teams and long handoffs. Setup, profiles, day-to-day, and scripts → **[`shared/gate-unlock.md`](shared/gate-unlock.md)**.

```bash
scripts/set-gate-mode.sh status          # check mode
scripts/setup-signed-gates.sh          # optional: enable signed + smoke test
```

### Gate mode examples

Knobs in `gates.json`: **`gate_mode`** (`legacy` | `signed`), **`enforcement`** (`warn` | `block`), **`profile`** (`minimal` | `standard` | `strict` | `paranoid`), plus configurable toggles for TDD, routing, time limits, model, and more. Full reference: [`shared/gate-unlock.md`](shared/gate-unlock.md).

**How to read the table:** *Commit* / *Push* = what `gate.py` checks for that action. *If missing* = behavior when requirements are not met (`warn` → GATE WARNING; `block` → tool call blocked via `{"decision":"block"}`).

#### Legacy (`gate_mode: "legacy"`)

Unlock: run skills → files under `.gates/` with real markers (`READY`, `PASSED 96%`, …). Enable `gate_protect: true` to block agents from forging gate files (G-GATE-1).

| Profile | `gates.json` | Commit requires | Push requires | If missing (`warn`) | If missing (`block`) |
|---------|--------------|-----------------|---------------|---------------------|----------------------|
| **minimal** | `"profile": "minimal", "enforcement": "warn"` | `/precommit` | `/precommit` | Warning; `git commit` / `git push` still run | — |
| **minimal** | `"profile": "minimal", "enforcement": "block"` | same | same | — | Blocked until `.gates/precommit-passed` has `READY` |
| **standard** | `"profile": "standard", "enforcement": "warn"` | `/precommit` | `/precommit` + `/evaluate` (≥ `eval_threshold`) | Warning on commit or push | — |
| **standard** | `"profile": "standard", "enforcement": "block"` | same | same | — | Blocked until flags valid (push also needs evaluate score) |
| **strict** | `"profile": "strict", "enforcement": "warn"` | `/precommit` + `/evaluate` | + `/reviewer` | Warning | — |
| **strict** | `"profile": "strict", "enforcement": "block"` | same | same | — | Blocked until all required flags |
| **paranoid** | `"profile": "paranoid", "enforcement": "warn"` | `/precommit` + `/evaluate` | + `/reviewer` + `/assess` | Warning | — |
| **paranoid** | `"profile": "paranoid", "enforcement": "block"` | same | same | — | Blocked until all required flags |

Default after `./install.sh`:

```json
{ "gate_mode": "legacy", "enforcement": "block", "profile": "minimal", "eval_threshold": 95, "tdd": true, "skill_routing": true, "max_session_minutes": 0, "model": "auto", "gate_protect": false }
```

```bash
# minimal + block (default) — missing precommit on commit:
git commit -m "x"    # → BLOCKED; exit 2
# After /precommit:
echo "READY $(date +%F)" > .gates/precommit-passed
git commit -m "x"    # → allowed
```

#### Signed (`gate_mode: "signed"`)

Unlock: skills → `reports/` → `verify_gate.py attest` → `issue_token.py` → `.gate/gate-token.jwt` (must match `git rev-parse HEAD`). Does not trust `.gates/` files.

| Profile | `gates.json` | Commit / push checks | If missing (`warn`) | If missing (`block`) |
|---------|--------------|----------------------|---------------------|----------------------|
| **minimal** | `"signed", "minimal", "warn"` | Same skill set as legacy minimal | Warning; git may still run | — |
| **minimal** | `"signed", "minimal", "block"` | same | — | Blocked without valid JWT |
| **standard** | `"signed", "standard", "warn"` | precommit; push + evaluate | Warning | — |
| **standard** | `"signed", "standard", "block"` | same | — | Blocked without JWT + reports |
| **strict** | `"signed", "strict", "warn"` | + reviewer on push | Warning | — |
| **strict** | `"signed", "strict", "block"` | same | — | Blocked |
| **paranoid** | `"signed", "paranoid", "warn"` | + assess on push | Warning | — |
| **paranoid** | `"signed", "paranoid", "block"` | same | — | Blocked |

Typical signed + block + standard (see `templates/gates.signed.example.json`):

```json
{ "gate_mode": "signed", "enforcement": "block", "profile": "standard", "eval_threshold": 95 }
```

```bash
# signed + block — commit without token:
git commit -m "x"    # → blocked (exit 2) or GATE WARNING if warn
# After skills + attest + issue (or CI on push):
python .agent-toolkit/gate/scripts/verify_gate.py attest --project-root .
python .agent-toolkit/gate/scripts/issue_token.py --project-root . --action push
git push             # → allowed when JWT matches HEAD
```

#### How to get each configuration

| Target config | Command or action |
|---------------|-------------------|
| **legacy + block + minimal** (default) | `./install.sh` only |
| **legacy + block + any profile** | Edit `gates.json`: `"enforcement": "block"`, set `"profile"` |
| **signed + block + standard** | `scripts/setup-signed-gates.sh` |
| **signed + warn + standard** | `scripts/setup-signed-gates.sh --warn` |
| **signed + block + strict** | `scripts/setup-signed-gates.sh --profile strict` |
| **signed + shared CI/laptop key** | `scripts/setup-signed-gates.sh --upload-github-secret` |
| **Switch without re-bootstrap** | `scripts/set-gate-mode.sh legacy` or `signed` |
| **Manual signed** | Copy `templates/gates.signed.example.json` → `gates.json` after install |
| **Secret upload only on install** | `AGENT_TOOLKIT_UPLOAD_GATE_SECRET=1 ./install.sh` (does not enable signed by itself) |

**Session recovery:** `session_init.py` prioritizes `HANDOFF.md`, `project-state.md` (local per project — copy from `shared/project-state-template.md`), and requirements/architecture docs.

## Auto-Continuation

Sessions that hit context limits automatically hand off and relaunch. The wrapper script manages the session lifecycle — detect context exhaustion, write HANDOFF.md, clean `.session/`, relaunch with a fresh context window.

```bash
# Fire-and-forget until goal is done
python3 scripts/auto_continue.py "Build auth system with token refresh"

# With budget cap (per session)
python3 scripts/auto_continue.py --max-budget-usd 5.00 "Build auth system"

# Resume from existing HANDOFF.md
python3 scripts/auto_continue.py

# Verify the CLI command without running (no API calls)
python3 scripts/auto_continue.py --dry-run "Build auth system"
```

If `~/.local/bin` is in your PATH, `install.sh` creates an `agent-toolkit-continue` symlink:

```bash
agent-toolkit-continue "Build auth system"
```

**How it works:** `auto_continue.py` launches Claude Code sessions via `claude -p` (headless print mode) in a loop. Each session runs with `session_monitor.py` tracking context pressure (cumulative output bytes + PostCompact events). When a threshold is hit, the agent writes HANDOFF.md and exits. The wrapper detects the handoff, cleans `.session/`, and relaunches. The new session reads HANDOFF.md via `session_init.py` and continues where the previous one left off.

**Completion:** The loop stops when HANDOFF.md contains `## COMPLETE` or is removed by the agent.

**Verify it works:** Run with `--dry-run` first — it seeds HANDOFF.md and prints the exact `claude` command without executing it.

Architecture: [`architecture/auto-continuation.md`](architecture/auto-continuation.md). Requirements: [`requirements/auto-continuation.md`](requirements/auto-continuation.md).

## Strict Mode

Optional mode that trades speed for correctness. Prevents agent faking by making inference-based test fixtures and patch-forward patterns structurally detectable and blockable.

Activate in `gates.json`:

```json
{ "mode": "strict" }
```

Or per-session via env var:

```bash
AGENT_TOOLKIT_MODE=strict claude
```

**What strict mode adds:**

| Feature | What it does |
|---------|-------------|
| **G-IMPL-7** | Test fixtures must cite data source. "I read the code" is not valid. |
| **DATA step** | Mandatory step in slab cycle: query real system before writing fixtures. |
| **Drift detection** | Tracks exchanges since last real query, patch-forward incidents, slabs without data. |
| **Integrity checks** | Every 15 exchanges, injects drift audit with score. Critical drift triggers session restart. |
| **Evaluate required** | `/evaluate` required before commit (in addition to `/precommit`). |

Normal mode is completely unaffected. Requirements: [`requirements/strict-mode.md`](requirements/strict-mode.md). Rules reference: [`shared/strict-mode.md`](shared/strict-mode.md).

## Auto Mode

Append `auto` to chain skills without stopping (`/requirements auto my-app`). Opus plans; Sonnet/Haiku implements. **95%** eval gate (default); below **70%** = hard stop. Evidence-first (G-AUTO-1). Protocol: [`shared/orchestrator.md`](shared/orchestrator.md).

## Configurable Modes

All settings live in `gates.json`. Use the setup wizard or CLI one-liners:

```bash
agent-toolkit-setup                        # interactive wizard
agent-toolkit-setup --quick                # prototype — no TDD, no routing, warnings only
agent-toolkit-setup --balanced             # daily dev — TDD + routing + commit gate
agent-toolkit-setup --guarded              # production — eval on push, time-limited, gate protection
agent-toolkit-setup --lockdown             # full review — strict mode, all gates, gate protection
agent-toolkit-setup --tdd off --model sonnet  # toggle individual settings
agent-toolkit-setup --status               # show current config
```

| Setting | Values | Default | Env var override |
|---------|--------|---------|-----------------|
| `tdd` | `true` / `false` | `true` | `AGENT_TOOLKIT_TDD` |
| `skill_routing` | `true` / `false` | `true` | `AGENT_TOOLKIT_SKILL_ROUTING` |
| `max_session_minutes` | `0` (none) / int | `0` | `AGENT_TOOLKIT_MAX_SESSION_MINUTES` |
| `model` | `auto` / any string | `auto` | `AGENT_TOOLKIT_MODEL` |
| `auto` | `true` / `false` | `false` | `AGENT_TOOLKIT_AUTO` |
| `continue` | `true` / `false` | `false` | `AGENT_TOOLKIT_CONTINUE` |
| `gate_protect` | `true` / `false` | `false` | `AGENT_TOOLKIT_GATE_PROTECT` |

**Gate protection (G-GATE-1):** When `gate_protect: true`, agents cannot write to `.gates/` directly — only skill hooks can create gate files. Prevents agents from bypassing `/precommit` by forging gate files. Enabled by default in `guarded` and `lockdown` presets.

**Demo:** `scripts/demo-modes.sh` builds the same Todo API in all 4 modes so you can compare agent behavior side by side.

Troubleshooting: [`shared/troubleshooting.md`](shared/troubleshooting.md).

## Example Workflows

| Goal | Flow |
|------|------|
| Greenfield | `/requirements` → `/architecture` → `/implementation` → `/reviewer` → `/setup` → `/evaluate` |
| Add feature | `/requirements add-X` → `/architecture add-X` → `/implementation add-X` |
| Debug | `/debug …` or natural language — hypothesis → test → fix |
| Mid-project install | `./install.sh` → `/explore .` → work (hooks active immediately) |
| Cleanup pass | `/reviewer` → `/assess` → `/evaluate` → fix findings → `/precommit` |
| Fire-and-forget | `python3 scripts/auto_continue.py "Build X"` — auto-relaunches on context exhaustion |

## Guardrails

**21 rule groups** (universal + session hooks + precommit). Per-skill rules (G-REQ, G-ARCH, G-IMPL, G-EVAL, G-UPD) in [`shared/guardrails.md`](shared/guardrails.md). When hit: warn, record, continue.

| Group | IDs | What |
|-------|-----|------|
| Universal safety | **G1–G9** | No secrets in output, confirm destructive ops, honest verification, file safety, synthetic PII, LLM data-exit safeguards, … |
| Docs & workflow | **G10–G14** | README updates, project rules first, branch/PR naming, encrypt PII, project overrides toolkit |
| Implementation quality | **G-IMPL-6, G-IMPL-7** | No shortcuts (G-IMPL-6: 20 AI anti-patterns — [`ai-antipatterns.md`](skills/implementation/references/ai-antipatterns.md)), ground truth fixtures (G-IMPL-7 — strict mode) |
| Commit gate | **G-PUSH-1** | No commit/push without `/precommit` |
| Auto mode | **G-AUTO-1** | Every change cites evidence |
| Session hooks | **G-SESSION-1** | Never modify `.session/` (structural hook blocks) |
| Gate protection | **G-GATE-1** | Never modify `.gates/` directly (when `gate_protect: true`) |
| Precommit | **G-PC-1–5** | Meaningful tests, all instructions addressed, verify in app, ask on ambiguity |
| Per-skill | **G-REQ**, **G-ARCH**, **G-EVAL**, **G-UPD** | See `guardrails.md` |

## Repo Layout

```
skills/          13 workflows (+ sub-skills & references per skill)
agents/          9 research sub-agents
shared/          guardrails, orchestrator, gate-unlock, report-format, templates
hooks/           7 Python + 1 bash structural hook scripts + 2 library modules + update.sh
update.sh        9th hook — auto-pull before skills
gate/            JWT attest/verify (copied to .agent-toolkit/gate/ on install)
scripts/         agent-toolkit-setup, agent-toolkit-continue, setup_modes.py, auto_continue.py, demo-modes.sh, …
templates/       gates.json, signed example, GitHub workflow template
```

| Agent | Purpose |
|-------|---------|
| `functional-researcher` | How features work in other products |
| `scale-estimator` | QPS, storage, bandwidth estimates |
| `infrastructure-planner` | Servers, databases, cost |
| `tech-stack-advisor` | Tech options with trade-offs |
| `pattern-advisor` | Design patterns for a problem |
| `scale-advisor` | What changes at each scale |
| `codestructure-analyzer` | Existing codebase structure |
| `readme-validator` | Line-by-line README accuracy |
| `rules-indexer` | Project docs → decisions index |

## Portability

| Layer | Claude Code | Other LLMs |
|-------|-------------|------------|
| Skills | Slash commands | In `AGENTS.md` |
| Guardrails | `shared/*.md` | In `AGENTS.md` |
| Agents | Native sub-agents | Inlined in `AGENTS.md` |
| Structural hooks | Full enforcement via `hooks/` | Not available (prompt-only) |

```bash
./generate-project-rules.sh              # AGENTS.md
./generate-project-rules.sh --cursor     # + .cursorrules
```

## Built From Real Usage

Every rule comes from building real products with AI agents — async/sync silent failures, Promise.all page blanking, sloppy tests, false success messages, parking lot blindness. Bugs that shipped and were caught.

## Automated Health Check

GitHub Actions runs twice a month: link check, freshness (6-month threshold), file size (250-line target), inventory. Opens an issue if problems are found.

## Contributing

PRs welcome. Battle-tested feedback? Open an issue or add to the patterns.

## License

Apache 2.0 — see [LICENSE](LICENSE)
