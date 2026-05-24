# Agent Toolkit

Skills, guardrails, and structural hooks for AI coding agents. Plan, build, test, debug, and ship — any repo, any language.

**Best on:** [Claude Code](https://docs.anthropic.com/en/docs/claude-code) — hooks enforce rules the model cannot bypass.  
**Also works on:** Cursor, Codex, Gemini CLI, Windsurf, Aider — skills + guardrails only (no structural enforcement).

| | Count |
|---|------|
| Skills | 13 |
| Research agents | 9 |
| Guardrail groups | 21 |
| Structural hooks | 9 |

---

## Start here

### 1. Install once (global)

```bash
git clone https://github.com/jvalin17/agent-toolkit.git
cd agent-toolkit
./install.sh
```

**Requires:** `python3`, `jq`, Claude Code.

**What install does:**

| Action | Result |
|--------|--------|
| Symlinks skills | `~/.claude/skills/` |
| Symlinks agents + shared rules | `~/.claude/agents/`, `~/.claude/shared/` |
| Registers hooks | `~/.claude/settings.json` |
| Bootstraps gates (in a git repo) | `gates.json`, `.agent-toolkit/` in project root |

Re-run `./install.sh` if hooks were missing on first install.

### 2. Open your project

```bash
cd /path/to/your-project
claude
```

On session start, hooks inject project context automatically (`HANDOFF.md`, `project-state.md`, config). You should see **"AGENT TOOLKIT ACTIVE"**.

### 3. Run a skill

```bash
/explore .                  # understand existing code
/requirements my-app        # gather requirements (interactive)
/requirements auto my-app   # chain skills until done or blocked
/implementation add login   # build with TDD
/precommit                  # quality gate before commit
```

Natural language works too — e.g. "fix the login bug" routes to `/debug`.

---

## How it works

Three layers. Only the third is enforced at runtime.

```
You type a prompt
       ↓
route_to_skill.py          → injects which skill to follow
       ↓
Agent runs skill steps     → guardrails (prompt rules)
       ↓
Hooks on tool use          → block bad actions (structural)
       ↓
gate_hook.py on commit     → block until gates pass
```

| Layer | Enforced? | What |
|-------|-----------|------|
| **Skills** | Prompt only | Step-by-step workflows (`/precommit`, `/debug`, …) |
| **Guardrails** | Prompt only | Safety + quality rules — [`shared/guardrails.md`](shared/guardrails.md) |
| **Hooks** | **Yes — cannot bypass** | Block writes, gate commits, route skills, monitor session |

**Prompt rules can be ignored. Hooks cannot.**

---

## Design

Where things live and how they connect.

```
agent-toolkit/                    your-project/
├── skills/  ──symlink──►  ~/.claude/skills/
├── agents/  ──symlink──►  ~/.claude/agents/
├── shared/  ──symlink──►  ~/.claude/shared/
├── hooks/   ──path in──►  ~/.claude/settings.json   (live files, not copied)
├── gate/    ──copy on──►  .agent-toolkit/gate/      (per project, for CI)
└── templates/gates.json ──once──► gates.json        (per project, if missing)
```

| Component | Install method | Updated how |
|-----------|----------------|-------------|
| Skills, agents, shared | Symlink to repo | `git pull` in toolkit repo (auto before each skill via `update.sh`) |
| Hook scripts | Absolute path in `settings.json` | Same — edit/pull in toolkit repo, takes effect immediately |
| `gates.json` | Copied once from template | **Not auto-updated** — edit manually or use `agent-toolkit-setup` |
| `.agent-toolkit/gate/` | Copied on bootstrap | **Not auto-updated** — re-run bootstrap (see [Updates](#updates)) |

**Why two gate copies?** Hooks run from the toolkit repo (always latest). `.agent-toolkit/gate/` is a self-contained copy inside your project so CI and signed attestation work without the full toolkit checkout.

**Why symlinks for skills?** One `git pull` updates every project on your machine. No reinstall per project.

---

## Updates

### What updates automatically

| What | When |
|------|------|
| Skill content (`/precommit`, `/debug`, …) | Before every skill — `update.sh` runs `git pull` in the toolkit repo |
| Hook Python code (`session_monitor.py`, `gate_hook.py`, …) | Immediately after `git pull` — settings point at live files in the repo |
| New skill directories | Auto-symlinked on next skill run (if `update.sh` pulled them) |

So for day-to-day work: **`git pull` in the toolkit repo is enough.** You do not need to reinstall for skill or hook code changes.

### What does NOT update automatically

| What | How to update |
|------|---------------|
| New hooks added to `settings.json` | Re-run `./install.sh` (merges new hook registrations) |
| `gates.json` new keys (e.g. `report_protect`) | Edit manually, or `agent-toolkit-setup --status` and adjust |
| `.agent-toolkit/gate/` module | Re-run bootstrap: `bash scripts/bootstrap-project-gates.sh /path/to/agent-toolkit` from project root |
| `~/.claude/settings.json` hook paths | Re-run `./install.sh` if toolkit moved to a new directory |

### Quick reference

```bash
# Normal update (skills + hooks)
cd /path/to/agent-toolkit && git pull

# After a major toolkit upgrade (new hooks, moved install path)
./install.sh

# Refresh project's copied gate module
bash scripts/bootstrap-project-gates.sh "$(pwd)" /path/to/your-project

# Add new config keys to an existing project
agent-toolkit-setup --status    # see what's set
# then edit gates.json or use setup flags
```

---

## Daily workflow

### Build something

| Situation | Start with |
|-----------|------------|
| New project | `/requirements` → `/architecture` → `/implementation` |
| Existing repo | `/explore .` → `/implementation` |
| Bug | "fix …" or `/debug` |
| Before release | `/reviewer` → `/evaluate` |

### Commit (default config)

Default gates: **legacy + block + minimal** — `/precommit` required before `git commit`.

```
1. Do your work
2. /precommit
3. Agent writes .scratch/precommit_<slug>/findings.json
4. Agent runs: python3 hooks/finalize_report.py precommit .scratch/.../findings.json
5. Hook re-runs tests/lint and writes reports/precommit/pc_<slug>_<id>.md
6. Unlock gate:  echo "READY $(date +%F)" > .gates/precommit-passed
7. git commit -m "..."
```

Step 4–5 exist because **`report_protect: true` (default)** — agents cannot write to `reports/` directly. The hook owns the report file and re-runs mechanical checks so the agent cannot fake test results.

**The agent must not:**
- Skip or bypass tests (`--no-verify`, ignoring failures)
- Write directly to `reports/`, `.gates/`, or `.session/`
- Claim "ready" without running the real checks
- Commit without `/precommit` passing

Details: [`shared/gate-unlock.md`](shared/gate-unlock.md)

---

## Configuration

All settings live in **`gates.json`** at the project root.

```bash
agent-toolkit-setup --status              # show current config
agent-toolkit-setup --balanced            # daily dev preset
agent-toolkit-setup --guarded             # production preset
agent-toolkit-setup --lockdown            # strict + all reviews
agent-toolkit-setup --tdd off             # toggle one setting
```

| Setting | Default | What it does | Env override |
|---------|---------|--------------|--------------|
| `enforcement` | `block` | `block` = stop bad commits; `warn` = log only | `AGENT_TOOLKIT_ENFORCEMENT` |
| `profile` | `minimal` | Which skills are required — see [Gate profiles](#gate-profiles) | — |
| `gate_mode` | `legacy` | `legacy` = `.gates/` files; `signed` = JWT attestation | — |
| `tdd` | `true` | Remind to write tests before source edits | `AGENT_TOOLKIT_TDD` |
| `skill_routing` | `true` | Auto-detect intent → skill | `AGENT_TOOLKIT_SKILL_ROUTING` |
| `report_protect` | **`true`** | Block agent writes to `reports/` (G-REPORT-1) | `AGENT_TOOLKIT_REPORT_PROTECT` |
| `gate_protect` | `false` | Block agent writes to `.gates/` (G-GATE-1) | `AGENT_TOOLKIT_GATE_PROTECT` |
| `mode` | `normal` | `strict` = drift detection + fixture provenance | `AGENT_TOOLKIT_MODE` |
| `max_session_minutes` | `0` | Session time limit (0 = off) | `AGENT_TOOLKIT_MAX_SESSION_MINUTES` |
| `eval_threshold` | `95` | Minimum `/evaluate` score to pass gate | — |
| `test_command` | auto-detect | Command hook re-runs for attestation | — |
| `lint_command` | auto-detect | Command hook re-runs for attestation | — |

Presets (`--quick`, `--balanced`, `--guarded`, `--lockdown`) set combinations of the above. Demo: `scripts/demo-modes.sh`.

Troubleshooting: [`shared/troubleshooting.md`](shared/troubleshooting.md)

---

## Gate profiles

What `gate_hook.py` requires before `git commit` / `git push`:

| Profile | Commit requires | Push requires |
|---------|-----------------|---------------|
| **minimal** (default) | `/precommit` | `/precommit` |
| **standard** | `/precommit` | `/precommit` + `/evaluate` (≥ threshold) |
| **strict** | `/precommit` + `/evaluate` | + `/reviewer` |
| **paranoid** | `/precommit` + `/evaluate` | + `/reviewer` + `/assess` |

**Legacy mode** (default): unlock by creating marker files in `.gates/` after skills pass.  
**Signed mode** (optional): unlock via JWT from `verify_gate.py attest` — for teams and CI. Setup: `scripts/setup-signed-gates.sh`.

Full gate reference: [`shared/gate-unlock.md`](shared/gate-unlock.md)

---

## Skills

| Skill | Purpose |
|-------|---------|
| `/explore` | Understand a codebase — recon, architecture, conventions, issues |
| `/requirements` | Gather and validate requirements |
| `/architecture` | Design with trade-offs and user journey |
| `/implementation` | TDD — skeleton → slabs; fix, refactor, demo modes |
| `/debug` | Hypothesis-driven debugging with reproduction tests |
| `/assess` | Architecture fitness audit |
| `/verify` | Output quality check — is it useful, not just correct? |
| `/precommit` | Pre-commit quality gate |
| `/reviewer` | Deep audit — code, tests, a11y, deps, UI |
| `/evaluate` | 5-dimension quality score (not lenient) |
| `/setup` | Install scripts, Docker, Makefile, README |
| `/status` | Project dashboard — done, next, blockers |
| `/updater` | Toolkit health — links, freshness, standards |

Append **`auto`** to chain skills: `/requirements auto my-app`. Protocol: [`shared/orchestrator.md`](shared/orchestrator.md).

---

## Structural hooks

Registered in `~/.claude/settings.json` by `./install.sh`. Run as subprocesses — the agent cannot disable them.

| Hook | Trigger | Purpose |
|------|---------|---------|
| `session_init.py` | Session start, after compact | Load project context, init state, clear stale gates |
| `session_monitor.py` | Every tool use | Session limits; block `.session/` writes; block `reports/` when `report_protect`; drift checks in strict mode |
| `route_to_skill.py` | Every prompt | Intent → skill injection |
| `gate_hook.py` | Before `git commit` / `git push` | Enforce gate profiles |
| `tdd_enforce.py` | Before Edit/Write | TDD reminder if no test file |
| `check_doc_write.sh` | Before Write | Block writes outside repo root |
| `skill_passed.py` | After skill completes | Report gate status |
| `gate_cleanup.py` | After commit | Clear gate flags for next cycle |
| `update.sh` | Before each skill | Auto-pull toolkit |

**Report writer (not a Claude hook — run explicitly):**

```bash
python3 hooks/finalize_report.py precommit .scratch/precommit_<slug>/findings.json
```

Re-runs mechanical checks, writes canonical report to `reports/`. Used by `/precommit` today.

---

## Protection rules (structural)

These are enforced by hooks, not prompts.

| Rule | Blocks | Default |
|------|--------|---------|
| **G-SESSION-1** | Agent writes to `.session/` | Always on |
| **G-REPORT-1** | Agent writes to `reports/` | **`report_protect: true`** |
| **G-GATE-1** | Agent writes to `.gates/` | `gate_protect: false` (opt-in) |
| **G-PUSH-1** | Commit/push without required skills | `enforcement: block` |

Full guardrail list: [`shared/guardrails.md`](shared/guardrails.md)

---

## Advanced

### Auto-continuation (long tasks)

```bash
python3 scripts/auto_continue.py "Build auth with token refresh"
agent-toolkit-continue "Build auth with token refresh"   # if install created symlink
```

Detects context exhaustion → writes `HANDOFF.md` → relaunches fresh session. Stops when `HANDOFF.md` contains `## COMPLETE`.

Docs: [`architecture/auto-continuation.md`](architecture/auto-continuation.md)

### Strict mode

```json
{ "mode": "strict" }
```

Adds fixture provenance (G-IMPL-7), drift detection, periodic integrity checks. Activate: `agent-toolkit-setup --lockdown` or `AGENT_TOOLKIT_MODE=strict claude`.

Docs: [`shared/strict-mode.md`](shared/strict-mode.md)

### Signed gates (teams / CI)

```bash
scripts/setup-signed-gates.sh
scripts/set-gate-mode.sh status
```

Replaces `.gates/` marker files with JWT attestation. Details: [`shared/gate-unlock.md`](shared/gate-unlock.md)

### Other LLMs (no hooks)

```bash
./generate-project-rules.sh              # → AGENTS.md
./generate-project-rules.sh --cursor     # → AGENTS.md + .cursorrules
```

Skills and guardrails work; structural enforcement does not.

---

## Repo layout

```
skills/       13 workflow definitions
agents/       9 research sub-agents
hooks/        structural hook scripts + finalize_report.py
gate/         JWT attest/verify (copied to .agent-toolkit/gate/ on install)
shared/       guardrails, gate-unlock, report-format, orchestrator
scripts/      setup wizard, auto-continue, demo modes
templates/    gates.json, signed example, GitHub workflow
```

---

## Contributing

PRs welcome. Open an issue with battle-tested patterns or bugs you caught.

## License

Apache 2.0 — see [LICENSE](LICENSE)
