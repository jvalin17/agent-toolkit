# Agent Toolkit

Skills, guardrails, and structural hooks for AI coding agents. Plan, build, test, debug, and ship — any repo, any language.

**Best on:** [Claude Code](https://docs.anthropic.com/en/docs/claude-code) — hooks enforce rules the model cannot bypass.  
**Also works on:** Cursor, Codex, Gemini CLI, Windsurf, Aider — guardrails + workflows via `AGENTS.md` (see [Other LLMs](#other-llms-cursor-gpt-gemini--more)).

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

Re-run `./install.sh` only for first install, missing `jq`, symlink conflicts, or stale skill paths (e.g. `~/.claude/skills/debug` pointing at `/tmp/...`). Day-to-day updates are automatic — see [Updates](#updates).

### 2. Open your project

```bash
cd /path/to/your-project
claude
```

Hooks inject project context (`HANDOFF.md`, `project-state.md`, `gates.json` config). You should see **"AGENT TOOLKIT ACTIVE"**.

### 3. Run a skill

```bash
/explore .                  # understand existing code
/requirements my-app        # gather requirements (interactive)
/requirements auto my-app   # chain skills until done or blocked
/implementation add login   # build with TDD
/precommit                  # quality gate before commit
```

Natural language works too — e.g. "fix the login bug" routes to `/debug`.

If `/debug` (or another skill) errors with `Skill … cannot be used with Skill tool due to disable-model-invocation`, use natural language or: `Read skills/debug/SKILL.md and follow it` — see [Troubleshooting](#troubleshooting).

> **Using Cursor, GPT, Gemini, or another LLM?** See [Other LLMs](#other-llms-cursor-gpt-gemini--more) — setup is different (no `./install.sh` required for hooks).

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

## Other LLMs (Cursor, GPT, Gemini, & more)

The toolkit is **full strength on Claude Code** (hooks block bad commits, auto-pull, report protection). On other tools you get **guardrails + workflow rules** baked into the project — the agent follows them by prompt, not by structural enforcement.

### What works where

| Capability | Claude Code | Cursor / GPT / Gemini / others |
|------------|-------------|--------------------------------|
| Guardrails & workflow rules | Yes (hooks + skills) | Yes (`AGENTS.md` / `.cursorrules`) |
| Slash skills (`/precommit`, …) | Yes (`~/.claude/skills/`) | Optional — see Cursor skills below |
| Auto skill routing | Yes (hook) | No — describe intent in chat |
| Commit/push gates | Yes (hook blocks) | No — you enforce manually |
| Report protection (`reports/`) | Yes (hook blocks) | No |
| Auto `git pull` + sync | Yes (on session start + skills) | No — pull toolkit yourself when you want updates |

### Setup (every non-Claude project)

From **your project root** (not inside the toolkit repo):

```bash
/path/to/agent-toolkit/generate-project-rules.sh
```

Creates **`AGENTS.md`** — read by Codex, Gemini CLI, many GPT-based agents, and Claude Code.

For **Cursor**, also generate `.cursorrules`:

```bash
/path/to/agent-toolkit/generate-project-rules.sh --cursor
```

Regenerate after toolkit updates if guardrails change. You do **not** need `./install.sh` unless you also use Claude Code on the same machine.

Optional — bootstrap gates in a git repo (manual unlock, no hook blocking):

```bash
cd /path/to/your-project
bash /path/to/agent-toolkit/scripts/bootstrap-project-gates.sh /path/to/agent-toolkit
```

---

### Cursor

1. **Generate rules** (once per project):
   ```bash
   cd /path/to/your-project
   /path/to/agent-toolkit/generate-project-rules.sh --cursor
   ```
2. **Open the project** in Cursor.
3. **Start Agent chat** (Cmd+I / Ctrl+I or the Agent panel).
4. **Talk normally** — the agent reads `.cursorrules` and `AGENTS.md` automatically.

**Example first messages:**

```
Explore this codebase and summarize architecture, conventions, and risks.
```

```
Gather requirements for a task management API with JWT auth.
```

```
Run a precommit-style review: tests, README accuracy, and whether we're ready to commit.
```

**Optional — full toolkit skills in Cursor:** symlink skills so Cursor exposes them as Agent Skills:

```bash
mkdir -p ~/.cursor/skills
for d in /path/to/agent-toolkit/skills/*/; do
  name=$(basename "$d")
  ln -sf "$d" ~/.cursor/skills/"$name"
done
```

Then you can invoke `@precommit` or reference skills by name depending on your Cursor version. Rules in `AGENTS.md` still apply either way.

**What you must do manually without hooks:** run tests yourself, don't skip `/precommit` discipline before commit, don't trust the agent to write `reports/` — use `hooks/finalize_report.py` if you adopt that flow.

---

### OpenAI Codex / ChatGPT (agent mode)

1. Generate rules:
   ```bash
   /path/to/agent-toolkit/generate-project-rules.sh
   ```
2. Open the repo in Codex or an IDE with GPT agent support.
3. Ensure the tool loads **`AGENTS.md`** (Codex and many setups do this by default for the repo root).
4. Start with a clear task — slash commands are not registered; use plain language:

```
Follow the precommit workflow in AGENTS.md and review my staged changes.
```

```
Debug the failing test in tests/test_auth.py — hypothesis first, then fix.
```

---

### Google Gemini CLI

1. Generate `AGENTS.md` in the project (same command as above).
2. Run Gemini from the project directory so it picks up repo context:
   ```bash
   cd /path/to/your-project
   gemini
   ```
3. Reference workflows explicitly — Gemini reads project files including `AGENTS.md` when configured for the workspace.

---

### Windsurf, Aider, and other agents

| Tool | Rules file | Notes |
|------|------------|--------|
| **Windsurf** | `AGENTS.md` or tool-specific rules | Generate `AGENTS.md`; add to Windsurf rules if the product uses a separate file |
| **Aider** | `AGENTS.md` or `.aider.conf.yml` | Point aider at the repo; paste key guardrails into chat or config if needed |
| **Generic** | `AGENTS.md` | Any agent that reads the repo root will pick up the same rules |

**Pattern for all:** generate once → open project in your tool → describe the job in natural language using the same intent as slash skills (`explore`, `requirements`, `implementation`, `precommit`, `debug`).

---

### Keeping rules up to date (non-Claude)

```bash
cd /path/to/agent-toolkit && git pull
cd /path/to/your-project
/path/to/agent-toolkit/generate-project-rules.sh --cursor   # or without --cursor
```

Claude Code users get pull + sync automatically; other tools need an occasional regenerate after toolkit changes.

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
| Skills, agents, shared | Symlink to repo | Auto — `git pull` + sync on session start and before each skill |
| Hook scripts | Absolute path in `settings.json` | Auto — same sync refreshes paths and merges new hooks |
| `gates.json` | Copied once from template | Auto — bootstrap merges **missing** top-level keys only |
| `.agent-toolkit/gate/` | Copied on bootstrap | Auto — re-copied on each sync when run from your project |

**Why two gate copies?** Hooks run from the toolkit repo (always latest). `.agent-toolkit/gate/` is a self-contained copy inside your project so CI and signed attestation work without the full toolkit checkout.

**Why symlinks for skills?** Auto-pull keeps one clone current for all projects. Sync wires it into Claude automatically.

---

## Updates

### Get the latest version

| You use | How to update |
|---------|----------------|
| **Claude Code** (normal) | Automatic — new session or any skill run triggers `update.sh` (`git pull` + sync). Start a **new session** after a pull if hooks behave oddly. |
| **Claude Code** (manual) | `cd /path/to/agent-toolkit && git pull && ./install.sh --sync-only` then new session |
| **Cursor / other LLMs** | `cd /path/to/agent-toolkit && git pull` then re-run `generate-project-rules.sh` in your project |
| **Check what's installed** | `agent-toolkit-setup --status` (in a project with `gates.json`) |

Disable automatic pull: `AGENT_TOOLKIT_AUTO_PULL=0` in the environment.

You rarely need `./install.sh` after the first install — sync handles symlinks, hook paths, and `.agent-toolkit/gate/` refresh. Re-run full `./install.sh` only for symlink conflicts or missing `jq` on first setup.

### What runs automatically

| Trigger | Script | What it does |
|---------|--------|--------------|
| **Session start** (Claude opens / compacts) | `session_init.py` → `update.sh` | `git pull` + sync |
| **Every skill** (`/precommit`, `/debug`, …) | `update.sh` | `git pull` + sync |

Sync (`install.sh --sync-only`) after each pull:

- Symlinks new skills/agents/shared
- Merges new hooks into `settings.json`
- Refreshes hook paths if you moved the clone
- Re-syncs `.agent-toolkit/gate/` and merges missing `gates.json` keys

| What | When |
|------|------|
| Latest toolkit code | Auto — `git pull` on session start and before each skill |
| Symlinks, settings, bootstrap | Auto — same sync pass |

Disable auto-pull: `AGENT_TOOLKIT_AUTO_PULL=0`

### When to run `./install.sh` manually

| Situation | Action |
|-----------|--------|
| First-time setup | `./install.sh` (once) |
| Conflict: skill exists as a real directory, not symlink | `./install.sh` — answer prompts to replace |
| `jq` was missing on first install | Install `jq`, then `./install.sh` |
| Debugging sync | `AGENT_TOOLKIT_SYNC_VERBOSE=1 ./install.sh --sync-only` |
| Stale skill symlinks (`~/.claude/skills/*` → wrong path) | `./install.sh` once, then new session |

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `/debug` or Skill tool: `disable-model-invocation` | Use natural language or `Read skills/debug/SKILL.md`. Run `./install.sh`, new session. |
| Hooks not firing (no routing, no gates) | `cd /path/to/agent-toolkit && ./install.sh` |
| Session immediately HARD STOP | `rm -rf .session`, start new session |
| `git commit` blocked after `/precommit` | Check `.gates/precommit-passed` contains `READY`; re-run `finalize_report.py` |
| `git push` blocked after `/evaluate` | Check `.gates/evaluate-passed` has `PASSED` + score ≥ threshold; re-run finalize |
| Skills point at `/tmp/...` instead of your clone | `./install.sh` refreshes symlinks and hook paths |
| Want latest toolkit without waiting for auto-pull | `cd /path/to/agent-toolkit && git pull && ./install.sh --sync-only`, new session |

Full details: [`shared/troubleshooting.md`](shared/troubleshooting.md)

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
6. Hook writes `.gates/precommit-passed` when ready (agent cannot — G-GATE-1)
7. git commit -m "..."
```

Step 4–5 exist because **`report_protect: true` (default)** — agents cannot write to `reports/` directly. The hook owns the report file and re-runs mechanical checks so the agent cannot fake test results.

**The agent must not:**
- Skip or bypass tests (`--no-verify`, ignoring failures)
- Write directly to `reports/`, `.gates/`, or `.session/`
- Claim "ready" without running the real checks
- Commit without `/precommit` passing

Details: [`shared/gate-unlock.md`](shared/gate-unlock.md)

### Push (standard / guarded profile)

`profile: "standard"` (and `agent-toolkit-setup --guarded`) requires `/evaluate`
before `git push`, with score ≥ `eval_threshold` (default 95).

```
1. Complete your work
2. /precommit → finalize → commit
3. /evaluate → finalize (once; flag survives commit)
4. git push
5. Push clears evaluate/reviewer/assess flags for the next cycle
```

`gate_cleanup.py` removes only **precommit** on commit; push-scoped flags
(evaluate, reviewer, assess) stay valid so you do not re-finalize every skill
after commit. Push removes those flags after a successful push.

For **strict/lockdown**, run reviewer (and assess) finalize after commit,
before push — evaluate from step 3 still counts.

### Push (strict / lockdown profile)

| Profile | Push requires |
|---------|---------------|
| **strict** | `/evaluate` (from commit) + **reviewer** |
| **paranoid** (lockdown) | `/evaluate` + reviewer + **assess** |

Each skill follows the same findings.json → `finalize_report.py` flow:

```
python3 hooks/finalize_report.py reviewer .scratch/reviewer_<slug>/findings.json
python3 hooks/finalize_report.py assess .scratch/assess_<slug>/findings.json
```

Reviewer passes when `findings.high == 0`; assess passes when `findings.fix_now == 0`.

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
| `gate_protect` | **`true`** | Block agent writes to `.gates/` (G-GATE-1) | `AGENT_TOOLKIT_GATE_PROTECT` |
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
| **minimal** (default) | `/precommit` | *(none — commit already gated)* |
| **standard** | `/precommit` | `/evaluate` (≥ threshold) |
| **strict** | `/precommit` + `/evaluate` | `/reviewer` *(evaluate flag survives commit)* |
| **paranoid** | `/precommit` + `/evaluate` | `/reviewer` + `/assess` |

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
| `/debug` | Hypothesis-driven debugging with reproduction tests (if Skill tool errors, Read `skills/debug/SKILL.md`) |
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
| `session_init.py` | Session start, after compact | Load context; triggers `update.sh` (pull + sync) |
| `session_monitor.py` | Every tool use | Session limits; block `.session/` writes; block `reports/` when `report_protect`; drift checks in strict mode |
| `route_to_skill.py` | Every prompt | Intent → skill injection |
| `gate_hook.py` | Before `git commit` / `git push` | Enforce gate profiles |
| `tdd_enforce.py` | Before Edit/Write | TDD reminder if no test file |
| `check_doc_write.sh` | Before Write | Block writes outside repo root |
| `skill_passed.py` | After skill completes | Report gate status |
| `gate_cleanup.py` | After commit / push | Clear commit-scoped flags on commit; push-scoped on push |
| `update.sh` | Session start + before each skill | Auto `git pull` + sync install state |

**Report writer (not a Claude hook — run explicitly):**

```bash
python3 hooks/finalize_report.py precommit .scratch/precommit_<slug>/findings.json
python3 hooks/finalize_report.py evaluate .scratch/evaluate_<slug>/findings.json
python3 hooks/finalize_report.py reviewer .scratch/reviewer_<slug>/findings.json
python3 hooks/finalize_report.py assess .scratch/assess_<slug>/findings.json
```

Re-runs mechanical checks, writes canonical report to `reports/`. Used by all four gated skills.

---

## Protection rules (structural)

These are enforced by hooks, not prompts.

| Rule | Blocks | Default |
|------|--------|---------|
| **G-SESSION-1** | Agent writes to `.session/` | Always on |
| **G-REPORT-1** | Agent writes to `reports/` | **`report_protect: true`** |
| **G-GATE-1** | Agent writes to `.gates/` | **`gate_protect: true`** |
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
