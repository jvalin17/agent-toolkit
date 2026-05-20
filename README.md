# Agent Toolkit

[![Skills: 13](https://img.shields.io/badge/Skills-13-blue?style=for-the-badge)](skills/)
[![Agents: 9](https://img.shields.io/badge/Agents-9-green?style=for-the-badge)](agents/)
[![Hooks: 8](https://img.shields.io/badge/Hooks-8-purple?style=for-the-badge)](hooks/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-yellow?style=for-the-badge)](LICENSE)
[![Health Check](https://img.shields.io/badge/Health_Check-twice_monthly-brightgreen?style=for-the-badge)](.github/workflows/updater.yml)

Production-ready skills for AI coding agents. 13 skills, 9 agents, 17 guardrails, 8 harness hooks. Plan, build, test, debug, and ship — any repo, any language.

Built for Claude Code (full harness enforcement). Portable to Codex, Cursor, Gemini CLI, Windsurf, Aider (prompt-level skills only).

## Quick Start

```bash
git clone https://github.com/jvalin17/agent-toolkit.git
cd agent-toolkit
./install.sh    # symlinks skills + agents + shared, installs harness hooks
```

Then in any project:
```bash
# Quick prototype — auto mode builds everything, you walk away
/requirements auto my-app

# Hands-on — you guide each step
/requirements my-app

# Existing codebase — understand it first
/explore .

# Non-Claude tools — generates AGENTS.md with all rules flattened
./generate-project-rules.sh
```

Re-run `./install.sh` after first install to get harness hooks. Auto-updates after that.

Inside a **git project**, `./install.sh` also bootstraps **gate layout** (`.agent-toolkit/`, `gates.json`, optional signing key + CI workflow) — no separate step. New projects get **legacy + warn** from the template; signed mode is opt-in. **All setup paths:** [Gate setup reference](#gate-setup-reference-all-paths).

## How It Works

Three layers — skills define workflows, guardrails set rules, harness makes them unbypassable:

**1. Skills (13)** — workflows for every development task
```
Interactive:  /implementation my-app       → you guide each step
Auto:         /implementation auto my-app  → skills chain automatically
              Pauses only on ambiguity or failure. 95% eval gate.
```

**2. Guardrails (17)** — rules every skill follows
```
No hardcoded shortcuts (G-IMPL-6). No sloppy tests (G-PC-1).
Evidence-first in auto mode (G-AUTO-1). No commit without /precommit (G-PUSH-1).
```

**3. Harness (8 hooks)** — structural enforcement the model cannot bypass
```
Session start:  scans .md files, loads rules, verifies hook integrity, routes intent
Every prompt:   detects "fix bug" → /debug, "build X" → /implementation
Every tool use: session monitor tracks exchanges + time, hard stops at limit
Commit/push:    gate hook warns or blocks per `enforcement` (default: warn; profiles in gates.json)
```

### When to use what

| Situation | Recommended approach |
|-----------|---------------------|
| **Quick prototype / small app** | `/requirements auto my-app` — auto mode handles everything |
| **Production app / careful build** | Interactive — `/requirements` → `/architecture` → `/implementation`, you approve each step |
| **Joining existing project midway** | `/explore .` → then `/implementation` for new features |
| **Fix a bug** | Just say "fix the login bug" — harness routes to `/debug` automatically |
| **One-off refactor** | `/implementation refactor auth` — tests pass → refactor → tests still pass |
| **Quality check before release** | `/reviewer` + `/evaluate` — deep audit + percentage score |
| **Architecture review** | `/assess` — scale-aware, only suggests changes thresholds justify |

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

## Harness Engineering

Guardrails are prompts — the model can ignore them. Hooks are structural — **the model cannot bypass them**.

### What the harness does

| Hook | When | What |
|------|------|------|
| `session-init.sh` | Session start + after `/compact` | Scans project `.md` files, loads rules, initializes session counters, verifies hook integrity, clears stale gates. |
| `session-monitor.sh` | Every tool use + every prompt | Tracks exchanges, tool calls, wall-clock time. Warns at 15 exchanges/40 min. Hard stops at 20 exchanges/50 min with grace period for HANDOFF.md. Blocks agent writes to `.session/`. |
| `route-to-skill.sh` | Every user prompt | Detects intent → injects skill routing. Agent follows workflows automatically. |
| `gate.sh` | Before `git commit` / `git push` | **Legacy (default):** checks `.gates/*-passed`. **Signed (optional):** verifies `.gate/gate-token.jwt`. **Default `enforcement: warn`** — reminds the agent without blocking; set `"block"` for hard stop. |
| `skill-passed.sh` | After skill completes | **Reports** gate status — does not issue tokens. In legacy mode, skills may write `.gates/<skill>-passed` on pass. |
| `tdd-enforce.sh` | Before every file edit | TDD reminder — if no test file exists, injects "write test first." Covers features AND bug fixes. |
| `gate-cleanup.sh` | After successful commit | Clears all flags. Next commit needs fresh passes. |
| `update.sh` | Before every skill | Auto-pulls latest toolkit. |

### Gate modes — legacy (usual) vs signed (optional)

#### Gate setup reference (all paths)

Everything below is in this README — use whichever fits (you, or ask your agent to run the **Command** column).

| What you want | Command or action | Result in `gates.json` |
|---------------|-------------------|-------------------------|
| **Default — do nothing** | `./install.sh` only | `legacy`, `warn`, `minimal` (from `templates/gates.json`) |
| **Check current mode** | `scripts/set-gate-mode.sh status` | (prints `gate_mode`, `enforcement`, `profile`) |
| **Enable signed** (recommended) | `scripts/set-gate-mode.sh signed` or `scripts/setup-signed-gates.sh` | `signed` + bootstrap + smoke test |
| **Back to legacy** | `scripts/set-gate-mode.sh legacy` | `legacy`, `warn`, `minimal` |
| **Signed + GitHub secret** | `setup-signed-gates.sh --upload-github-secret` | same + sets `AGENT_TOOLKIT_GATE_SECRET` via `gh` |
| **Signed but non-blocking hooks** | `setup-signed-gates.sh --warn` or `set-gate-mode.sh signed --warn` | `signed`, `enforcement: warn` |
| **Stricter profile** | `setup-signed-gates.sh --profile strict` | `signed`, `profile: strict` |
| **Manual signed** | Edit `gates.json` or copy `templates/gates.signed.example.json` | you set fields by hand |
| **Manual legacy** | Edit `gates.json`: `"gate_mode": "legacy"` | you set fields by hand |
| **Upload secret on install** | `AGENT_TOOLKIT_UPLOAD_GATE_SECRET=1 ./install.sh` | only uploads secret; does not enable signed |

**Ask your agent** (copy-paste):

- *“Run `agent-toolkit/scripts/set-gate-mode.sh status` and tell me our gate mode.”*
- *“Enable signed gates: run `scripts/setup-signed-gates.sh` in this repo and show me `gates.json`.”*
- *“Switch to legacy gates: run `scripts/set-gate-mode.sh legacy`.”*

**Human in the loop:** Review `gates.json` and script output after any switch. You still approve merges; signed mode needs skills + token refresh before push (see [day-to-day](#signed-mode-day-to-day)).

**Optional `AGENT_TOOLKIT_GATE_SECRET`:** not required for legacy or for CI within one job. Only for the same signing key on GitHub and your laptop — use `--upload-github-secret` or paste `.gate/signing.key` into repo Secrets.

**More detail:** [Switching modes](#switching-modes-you-or-your-agent--human-reviews-gatesjson) · [Enable signed (~5 min)](#optional-enable-signed-gates-5-minutes) · [Signed day-to-day](#signed-mode-day-to-day) · [Profiles](#gate-profiles-gatesjson) · [`shared/gate-unlock.md`](shared/gate-unlock.md)

---

**Most people should use legacy mode** — skills, hooks, and reports are enough, especially for short sessions (under ~30 minutes). No GitHub secrets, no per-repo token setup, no JWT workflow.

**Signed gates** are an **optional extra security layer** for long-running sessions, handoffs, team repos, or production merges — when you want CI and branch protection to hold authority, not filesystem flags the agent could forge.

| Mode | Setup | Best for |
|------|--------|----------|
| **legacy** (recommended default) | `"gate_mode": "legacy"` in `gates.json` | Solo dev, sessions &lt; 30–60 min, prototypes |
| **signed** (optional) | `"gate_mode": "signed"` in `gates.json` | Sessions 2+ hours, HANDOFF/compaction, team `main`, regulated work |

**`AGENT_TOOLKIT_GATE_SECRET` is completely optional.** You do not need it for legacy mode, for this toolkit repo, or for CI in a single workflow run (CI uses `.gate/signing.key` created at bootstrap). Set it only if you later want signed mode with the **same** key on GitHub and your laptop (or branch protection with stable tokens).

#### When to turn on signed gates (usual timeline)

| Session / situation | Suggested mode | Why |
|---------------------|----------------|-----|
| **&lt; 30 min**, single goal, you stay in the loop | **legacy** + **minimal** profile + `enforcement: warn` | Low friction for Cursor/LLMs; skills carry quality |
| **30–90 min**, one feature, no handoff | **legacy** | Same; refresh `.gates/` or re-run skills before commit |
| **2+ hours**, `/compact`, or **HANDOFF.md** resume | Consider **signed** on that repo | Stale flags and skipped skills are more likely |
| **Multi-day** or **async agent** (walk away, come back) | **signed** + CI check on `main` | Merge authority outside the agent filesystem |
| **Team / production** | **signed** + branch protection `agent-toolkit-gate` | Strongest; not needed for personal experiments |

There is no fixed rule — if you cap sessions at 30 minutes (as many do), you may **never** need signed mode.

#### Switching modes (you or your agent — human reviews `gates.json`)

Same commands as the [reference table](#gate-setup-reference-all-paths). `set-gate-mode.sh signed` and `setup-signed-gates.sh` both enable signed mode (the latter is what `signed` runs under the hood).

| Mode | After switch, before `git push` |
|------|--------------------------------|
| **legacy** | Run `/precommit` (and other skills per profile); flags in `.gates/` |
| **signed** | Run skills → `verify_gate.py attest` → `issue_token.py` (or CI on push) |

#### Legacy mode (default for daily work)

```json
{
  "gate_mode": "legacy",
  "enforcement": "warn",
  "profile": "minimal",
  "eval_threshold": 95
}
```

Run skills before commit; on pass they write `.gates/precommit-passed` (must contain `READY`), `.gates/evaluate-passed` (`PASSED` + score), etc. `gate.sh` validates flag **content**, not just file existence.

**`enforcement`:** `"warn"` (default) injects a **GATE WARNING** into the agent context but **does not block** the shell command — so Cursor and other LLM tools can still run `git commit` / `git push` while being reminded to run `/precommit`. Use `"enforcement": "block"` only when you want a hard stop (teams, production). Weaker than signed (agent could still `echo` flags) — acceptable for short trusted sessions.

#### Signed gates (optional extra layer)

**Problem signed mode solves:** In legacy mode, an agent could write `.gates/precommit-passed` with `echo` and bypass the harness.

**Approach:** Split **workflow** (skills) from **authority** (CI + signed token).

| Layer | Role |
|-------|------|
| **Skills** (`/precommit`, `/evaluate`, …) | Run the real workflows. Write human-readable reports under `reports/`. You (or the agent) still run these before shipping. |
| **Attestation** (CI or local script) | Mechanical checks (tests, lint) **plus** validation of skill **reports** under `reports/` (SHA-256 bound). Writes `.gate/attestation.json`. |
| **JWT** (CI issues, local hook verifies) | Short-lived token in `.gate/gate-token.jwt`, bound to `commit_sha` and your `gates.json` profile. `gate.sh` refuses `git commit` / `git push` without a valid token. |
| **GitHub** (optional but strongest) | Workflow `agent-toolkit-gate` on push/PR. Branch protection can require that check — merge authority lives outside the agent’s filesystem. |

Signing uses **HS256** and `.gate/signing.key` (stdlib + PyJWT only — no `cryptography` wheel). CI can use that file per run with **no** GitHub secret. Optionally set `AGENT_TOOLKIT_GATE_SECRET` to the same value for cross-machine or cross-run stability.

#### What `./install.sh` sets up in your repo

When you run `./install.sh` from inside a git checkout:

- `.agent-toolkit/gate/` — gate scripts copied into the project (for CI and local verify)
- `.agent-toolkit/config.json` — toolkit path and version
- `gates.json` — if missing, template is installed (`gate_mode: legacy`, `enforcement: warn`, `profile: minimal`)
- `.gate/signing.key` — gitignored signing secret (created once; optional GitHub secret only if you want the same key in CI and locally)
- `.github/workflows/agent-toolkit-gate.yml` — attest → issue token → verify (works without any GitHub secret in a single CI job)
- `.gitignore` entries for `.gate/signing.key`, `.gate/gate-token.jwt`, etc.

#### Optional: enable signed gates (~5 minutes)

**One command** (from your app repo):

```bash
/path/to/agent-toolkit/scripts/setup-signed-gates.sh
```

That script bootstraps layout, sets `gate_mode: signed` in `gates.json`, ensures `.gate/signing.key`, runs a local attest → issue → verify smoke test, and prints next steps.

| Flag | When to use |
|------|-------------|
| `--upload-github-secret` | Same signing key on GitHub Actions and your laptop (team / branch protection) |
| `--warn` | Keep `enforcement: warn` instead of `block` |
| `--profile strict` | Stricter skill requirements (see profiles table below) |

**Manual checklist** (if you prefer not to use the script):

1. `./install.sh` in the project (creates `.agent-toolkit/`, workflow, signing key).
2. Edit `gates.json`: `"gate_mode": "signed"`, pick `profile` (`standard` is a good default).
3. `(optional)` Repo → Settings → Secrets → Actions → `AGENT_TOOLKIT_GATE_SECRET` = contents of `.gate/signing.key`.
4. `(optional)` Branch protection on `main`: require check **`agent-toolkit-gate`**.
5. Local smoke test:
   ```bash
   pip install -r .agent-toolkit/gate/requirements.txt
   python .agent-toolkit/gate/scripts/verify_gate.py attest --project-root .
   python .agent-toolkit/gate/scripts/issue_token.py --project-root . --action push
   python .agent-toolkit/gate/scripts/verify_gate.py verify --project-root . --action push
   ```

Details: `shared/gate-unlock.md` and `scripts/setup-signed-gates.sh --help`.

#### Signed mode day-to-day

Skills are unchanged in intent — still run them for quality. In signed mode the harness does not trust hand-written `.gates/` files.

1. **Work as usual** — `/precommit`, `/evaluate`, `/reviewer`, `/assess` when your profile requires them. Fix what they find; reports live under `reports/`.

2. **Before `git commit` or `git push`** you need a valid **gate token** for the current `HEAD`:
   - **After push/PR:** GitHub Actions runs mechanical attestation and issues `gate-token.jwt`. Download the **gate-token** workflow artifact into `.gate/gate-token.jwt`, or rely on branch protection so merge only happens when CI passed (you may not need a local token if you only push from CI).
   - **Local (same machine, dev loop):**
     ```bash
     pip install -r .agent-toolkit/gate/requirements.txt   # once
     python .agent-toolkit/gate/scripts/verify_gate.py attest --project-root .
     python .agent-toolkit/gate/scripts/issue_token.py --project-root . --action push
     ```
     Token must match `git rev-parse HEAD`. Re-issue after each new commit.

3. **Commit or push** — `gate.sh` calls `verify_gate.py verify`. Wrong/missing token → **GATE WARNING** (default `enforcement: warn`) or **blocked** (`enforcement: block`).

4. **GitHub (team / production)** — Optional branch protection requiring **`agent-toolkit-gate`**. Optional secret `AGENT_TOOLKIT_GATE_SECRET` only if you need tokens to match between CI and local machines.

5. **Who can mint tokens?** Anyone with `.gate/signing.key` (or the GitHub secret) can issue a local JWT. That stops casual `echo` into `.gates/`, but **branch protection on `agent-toolkit-gate`** is the real merge authority for teams.

Skill gate details: `shared/gate-unlock.md`.

#### Gate profiles (`gates.json`)

| Profile | Commit needs | Push needs | Best for |
|---------|-------------|------------|----------|
| **minimal** | `/precommit` (mechanical) | `/precommit` | **Default template** — prototypes, Cursor/short sessions |
| **standard** | `/precommit` | `/precommit` + `/evaluate` (score ≥ threshold) | Balanced |
| **strict** | `/precommit` + `/evaluate` | + `/reviewer` | Team / production |
| **paranoid** | `/precommit` + `/evaluate` | + `/reviewer` + `/assess` | High-stakes |

```json
{
  "gate_mode": "legacy",
  "enforcement": "warn",
  "profile": "minimal",
  "eval_threshold": 95
}
```

Set `"enforcement": "block"` when you want `gate.sh` to return exit 2 and stop the tool. For signed mode, use `"gate_mode": "signed"` (secret optional — see above). Attestation requires mechanical checks plus valid skill reports under `reports/` (SHA-256 bound). See `gate/reports.py`.

### Examples

**Default (legacy + warn — most users):**
```bash
cd my-project
/path/to/agent-toolkit/install.sh
# → gates.json (legacy, warn, minimal), .agent-toolkit/, optional .gate/ + workflow
```
```json
{ "gate_mode": "legacy", "enforcement": "warn", "profile": "minimal" }
```
Hook injects **GATE WARNING** if flags are missing; `git commit` / `git push` still run. Skills write `.gates/precommit-passed` (`READY`), etc.

**Signed mode (optional — teams / long sessions):**

```bash
/path/to/agent-toolkit/scripts/setup-signed-gates.sh
```

Or by hand: `{ "gate_mode": "signed", "enforcement": "block", "profile": "standard" }` — see `templates/gates.signed.example.json`.
```
You: "commit this"
  → BLOCKED (or warned): missing .gate/gate-token.jwt
  → /precommit, /evaluate → attest + issue_token (or CI on push)
  → git commit allowed when token matches HEAD
```
Enable branch protection: require check **`agent-toolkit-gate`**.

### Skill routing in action

```
You: "the search is broken"
  → route-to-skill.sh injects: "Follow /debug. Hypothesis-driven. Test first."
  → Claude follows /debug workflow automatically

You: "add dark mode"
  → route-to-skill.sh injects: "Follow /implementation. TDD. Slab-by-slab."
  → Claude follows /implementation workflow automatically

You: "/reviewer"
  → No injection — you invoked the skill directly
```

### Session monitor

Prevents quality degradation from long sessions. Hook-enforced — the agent cannot bypass it.

```
session-monitor.sh tracks:
  - Exchange count (user prompts)
  - Wall-clock time
  - Tool call count

Thresholds (whichever hits first):
  15 exchanges / 40 min  → WARNING: "Prepare HANDOFF.md, finish current work"
  20 exchanges / 50 min  → GRACE: 10 tool calls to wrap up + write handoff
  Grace exhausted        → HARD STOP: only HANDOFF.md, project-state.md, git commit allowed

Agent cannot modify .session/ files (G-SESSION-1) — blocked by the same hook.
```

### Context recovery

Every session starts fresh — no relying on memory:
```
session-init.sh scans your project:
  - HANDOFF.md (PRIORITY — resume from here)
  - project-state.md (decisions, features, warnings)
  - CLAUDE.md, DECISIONS.md
  - requirements/*.md, architecture/*.md
  → Tells Claude: "Read these FIRST"
  → Re-fires after /compact (context survives)
  → Initializes session counters (fresh session = fresh limits)
  → Verifies hooks are installed and executable
  → Clears stale gate files from previous sessions
```

### Feature Tracker

In `project-state.md` — strikethrough = done, not struck = remaining:

```markdown
| Feature | Status | Verified | Commit |
|---------|--------|----------|--------|
| ~~Item CRUD~~ | ~~done~~ | ~~2026-05-19~~ | ~~abc1234~~ |
| ~~Categories~~ | ~~done~~ | ~~2026-05-19~~ | ~~def5678~~ |
| Low stock alerts | in-progress | | slab-3 |
| Search + filter | pending | | |
```

Updated by `/implementation` after each slab. New sessions read this first.

### Starting midway (existing project)

```bash
# 1. Install toolkit in the project (skills, hooks, gates.json if missing)
/path/to/agent-toolkit/install.sh

# 2. Understand the codebase
/explore .
# → creates project-state.md with architecture, conventions, features

# 3. Start working — hooks active immediately
"add search feature"
# → route-to-skill.sh routes to /implementation
# → tdd-enforce.sh reminds about test-first on every edit
# → gate.sh warns (default) or blocks if skills/flags/token not satisfied
```

### Clean development with skills

```bash
# After building, run these skills to clean up:
/reviewer                # deep code audit — finds DRY violations, stale closures
/assess                  # architecture fitness — are patterns right for current scale?
/evaluate                # 5-dimension score — where are the gaps?

# Fix what they find:
"fix the N+1 query reviewer found"
# → routes to /debug → failing test → fix → regression test

# Before release:
/setup                   # generates install scripts, Docker, Makefile, README
```

## Auto Mode

Append `auto` to any skill. Skills chain without stopping. Pauses only on ambiguity or failure.

```
/requirements auto inventory-app

[Opus]   Research: functional-researcher studies existing inventory apps
[Opus]   Requirements: drafts with domain table-stakes (not just what you said)
[Opus]   Architecture: decisions logged as D-ARCH-1, D-ARCH-2 with evidence
[Opus]   Code change plan: file-by-file before any code is written
[Sonnet] Slab 1: skeleton → TDD → precommit ✓ → eval 96% → auto-commit
[Sonnet] Slab 2: CRUD → TDD → precommit ✓ → eval 95% → auto-commit
  ⚠️ Context limit → HANDOFF.md → new session resumes
[Sonnet] Slab 3-4: remaining features → auto-commit each
[Opus]   Final: eval 95%, README verified, guardrail audit
         Cleanup: archive artifacts, README = source of truth
```

**Auto mode rules:**
- 95% eval gate (configurable). Below 70% = hard stop.
- Opus plans. Sonnet/Haiku implements. (cost-efficient)
- Evidence-first: every change cites requirement, test, or research.
- Never stops to ask "Ready to continue?" — just continues.
- Sparse input (one-liner) → research is MANDATORY before building.

## Flows

### Greenfield — Plan, Build, Ship

```
/requirements recipe-finder     → draft requirements, research domain
/architecture recipe-finder     → design with trade-offs, log decisions
/implementation recipe-finder   → skeleton → slabs with TDD → precommit → commit
/reviewer recipe-finder         → deep code audit
/setup recipe-finder            → install scripts + Docker + README
/evaluate recipe-finder         → "94% (A). To reach 96%: add rate limiting."
```

### Add Feature to Existing App

```
/requirements add-search        → scans codebase, asks only about what's NEW
/architecture add-search        → reuse check: found existing scorer.py — reuse 80%
/implementation add-search      → one slab with TDD, existing conventions
```

### Debug

```
/debug search returns 0 results
→ [H1] API key missing from .env (confirmed)
→ Failing test written → fixed → regression test added
→ "Change ready. Please verify: search for 'chicken'."
```

### Fix, Refactor, Demo

```
/implementation fix login-bug    → failing test → fix → verify
/implementation refactor auth    → tests pass → refactor → tests still pass
/implementation demo auto-apply  → mock data → validate UX first
```

### Architecture Assessment

```
/assess my-app
→ "N+1 query in user list (fix now — any scale)"
→ "No caching on search (consider at >100 QPS — you're at 80)"
→ Safe refactoring: characterize → abstract → build → switch → verify → remove
```

### Quality Scoring

```
/evaluate my-app
→ Completeness: 95% | Code Quality: 88% | Security: 100%
→ Test Quality: 85% | Efficiency: 92% | Overall: 92% (A)
```

## Guardrails

17 rules every skill follows. When hit: warns, records, continues.

| Guardrail | What |
|-----------|------|
| **G1-G9** | No secrets, no destructive ops, file safety, no PII, flag doc gaps, mid-conversation updates, LLM data security |
| **G10** | README auto-update after feature changes |
| **G11** | Check project rules before acting — flag contradictions |
| **G12** | Branch naming: `feature/`, `fix/`, `refactor/`. PR titles describe user impact. |
| **G13** | Personal data encrypted at rest. Never plaintext. |
| **G14** | Project rules override toolkit defaults. Your CLAUDE.md wins. |
| **G-IMPL-6** | No easy way out — no hardcoded returns, magic numbers, copy-paste x3, shipped stubs, swallowed errors |
| **G-PUSH-1** | No commit/push without /precommit. Non-negotiable. |
| **G-AUTO-1** | Every change must cite evidence. Never assume. |
| **G-SESSION-1** | Agent must never modify `.session/` files. Session state is hook-managed only. |
| **G-PC-1-5** | No sloppy tests, all instructions addressed, no false "done", verify in app, ask on ambiguity |

## Architecture

```
skills/                          13 skill workflows
  requirements/                  ~79 lines + 4 sub-skills + 7 references
  architecture/                  ~69 lines + 8 sub-skills + 4 references
  implementation/                ~105 lines + 7 sub-skills + 7 references
  reviewer/                      107 lines + 6 sub-skills
  assess/                        168 lines + 2 references
  debug/                         ~190 lines
  evaluate/                      ~176 lines
  explore/                       ~143 lines
  precommit/                     ~118 lines + references
  setup/                         77 lines + 1 reference
  status/                        ~147 lines
  updater/                       180 lines
  verify/                        ~101 lines

shared/                          loaded by skills on demand
  orchestrator.md                auto mode protocol (~267 lines)
  guardrails-quick.md            one-line rule summaries (~43 lines)
  guardrails.md                  full guardrail definitions
  gate-unlock.md                 how skills unlock gates (signed vs legacy)
  report-format.md               report template
  project-state-template.md      project state + feature tracker template

hooks/                           harness enforcement (Claude Code only)
  session-init.sh                scans .md files, loads rules, verifies integrity
  session-monitor.sh             tracks exchanges/time, hard stops at limit, protects .session/
  route-to-skill.sh              detects intent, routes to skill workflow
  gate.sh                        legacy .gates/ or signed JWT; warn (default) or block
  skill-passed.sh                reports gate status after skills
  tdd-enforce.sh                 TDD reminder before source file edits (no test? write first)
  gate-cleanup.sh                clears legacy flags + gate token after commit
  gates.json                     reference profile template (copy to project root)

gate/                            signed gate module (also copied to .agent-toolkit/gate/)
  attest.py                      mechanical checks → attestation.json
  core.py                        JWT issue/verify (HS256)
  keys.py                        signing key generation and management
  reports.py                     skill report validation (SHA-256 bound)
  scripts/verify_gate.py         attest | verify CLI
  scripts/issue_token.py         issue JWT (CI or local; needs signing secret)

scripts/
  bootstrap-project-gates.sh     project gate layout (called from install.sh)
  setup-signed-gates.sh          optional one-command signed mode setup
  set-gate-mode.sh               switch legacy ↔ signed (or status); agent-safe
  seed-gate-reports.sh           generate fixture reports for testing
  cleanup-archive.sh             deletes archive files older than 30 days

templates/
  gates.json                     default legacy gates.json for new projects
  gates.signed.example.json      copy/reference for manual signed setup
  github/workflows/              agent-toolkit-gate.yml for consumer repos

agents/                          9 sub-agents for parallel research
```

| Agent | Purpose |
|-------|---------|
| `functional-researcher` | How features work in other products |
| `scale-estimator` | Back-of-envelope math (QPS, storage, bandwidth) |
| `infrastructure-planner` | Servers, databases, cost estimates |
| `tech-stack-advisor` | Tech options with trade-offs |
| `pattern-advisor` | Design patterns for specific problems |
| `scale-advisor` | What changes at each scale level |
| `codestructure-analyzer` | Analyze existing codebase structure |
| `readme-validator` | Validate + fix every README claim line-by-line |
| `rules-indexer` | Scan project docs for decisions and constraints |

## Portability

| Layer | Claude Code | Other LLMs (Codex, Cursor, Gemini, Windsurf, Aider) |
|-------|------------|------------------------------------------------------|
| **Skills** | Slash commands | Flattened into AGENTS.md |
| **Guardrails** | Loaded from shared/*.md | Included in AGENTS.md |
| **Agents** | Native sub-agents | Inlined in AGENTS.md |
| **Harness** | Full hook enforcement | **Not available** — prompt-level only |

```bash
# For non-Claude tools:
./generate-project-rules.sh              # creates AGENTS.md
./generate-project-rules.sh --cursor     # also creates .cursorrules
```

## Built From Real Usage

Every rule comes from building real products with AI agents — async/sync silent failures, Promise.all page blanking, sloppy tests, false success messages, parking lot blindness. Bugs that shipped and were caught.

## Automated Health Check

GitHub Actions runs twice a month: link check, freshness check (6-month threshold), file size check (250-line target), inventory. Opens an issue if problems found.

## Contributing

PRs welcome. Battle-tested feedback? Open an issue or add to the patterns.

## License

Apache 2.0 — see [LICENSE](LICENSE)
