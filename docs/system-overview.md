# System overview

Agent Toolkit wraps AI coding agents with **skills** (workflows), **guardrails** (rules), and **structural hooks** (enforcement on Claude Code). This document explains how those pieces connect.

## High-level flow

```
User prompt
    │
    ▼
route_to_skill.py ──► injects matching skill (e.g. /implementation)
    │
    ▼
Agent runs skill workflow
    │
    ├── session_monitor.py ── blocks bad tool use (G-SESSION-1, G-REPORT-1, G-GATE-1)
    ├── tdd_enforce.py ────── reminds test-first when enabled
    │
    ▼
Gated skills (precommit, evaluate, reviewer, assess)
    │
    ├── Agent writes findings → .scratch/<skill>_<slug>/findings.json
    └── Agent runs finalize_report.py → hook writes reports/ + .gates/
    │
    ▼
git commit / git push
    │
    └── gate_hook.py ── checks .gates/ flags or signed JWT
            │
            ├── pass → gate_cleanup.py clears scoped flags
            └── fail → block (or warn once, then escalate — see gate-unlock.md)
```

## Three layers of control

| Layer | What | Enforced how (Claude Code) |
|-------|------|----------------------------|
| **Skills** | Step-by-step workflows in `skills/*/SKILL.md` | Injected into context; agent follows by instruction |
| **Guardrails** | Rules in `shared/guardrails.md` (G-* groups) | Referenced by skills; some backed by hooks |
| **Hooks** | Python/bash in `hooks/` | Claude Code PreToolUse / SessionStart — subprocess, not optional |

On **Cursor, Codex, Gemini CLI, Windsurf, Aider**: skills and guardrails ship via `AGENTS.md` in your project. Hooks do not run — the agent follows rules by prompt, not by structural block.

## Gated skills and finalize

Four skills can unlock git operations. They share one pattern:

1. Run the skill checklist (tests, lint, review, etc.).
2. Write structured output to `.scratch/<skill>_<slug>/findings.json`.
3. Run `python3 hooks/finalize_report.py <skill> <findings.json>`.

`finalize_report.py` re-runs mechanical checks, writes the canonical markdown report under `reports/`, and (in legacy mode) writes the matching `.gates/*-passed` flag. With default **`gate_protect: true`** and **`report_protect: true`**, the agent cannot write those paths directly — only the hook can.

| Skill | Gate flag | Pass condition |
|-------|-----------|----------------|
| `/precommit` | `.gates/precommit-passed` | Mechanical checks + findings |
| `/evaluate` | `.gates/evaluate-passed` | Score ≥ `eval_threshold` (default 95) |
| `/reviewer` | `.gates/reviewer-passed` | `findings.high == 0` |
| `/assess` | `.gates/assess-passed` | `findings.fix_now == 0` |

## Gate profiles

`gates.json` → `profile` controls which skills are required at commit vs push:

| Profile | Commit | Push |
|---------|--------|------|
| **minimal** (default) | precommit | — |
| **standard** | precommit | evaluate |
| **strict** | precommit + evaluate | reviewer |
| **paranoid** | precommit + evaluate | reviewer + assess |

**Gate cleanup:** On commit, only `precommit-passed` is cleared. Push-scoped flags (`evaluate`, `reviewer`, `assess`) survive commit so you finalize once, commit, then push without re-running evaluate.

## Legacy vs signed gates

| | Legacy (default) | Signed (optional) |
|---|------------------|-------------------|
| Unlock | `.gates/*-passed` from `finalize_report.py` | JWT in `.gate/gate-token.jwt` |
| Reports | Same finalize flow | Same + SHA-256 bound attestation |
| Best for | Daily dev | Team `main`, CI branch protection, regulated work |
| Setup | `./install.sh` | `scripts/setup-signed-gates.sh` |

Both modes use the same skill → findings → finalize path. Signed mode adds `verify_gate.py attest` and `issue_token.py` so tokens bind to `commit_sha` and report hashes.

Details: [gate-unlock.md](../shared/gate-unlock.md)

## Session lifecycle

| Event | Hook | Role |
|-------|------|------|
| Session start | `session_init.py` | Load project context, run `update.sh` (pull + sync), warn on stale gates |
| Every tool use | `session_monitor.py` | Session limits, path protection, strict-mode drift |
| After compact | `session_init.py` | Re-inject context |
| Before Edit/Write | `tdd_enforce.py` | TDD reminder |
| Before git commit/push | `gate_hook.py` | Enforce gate profile |
| After commit/push | `gate_cleanup.py` | Clear scoped gate flags |

Long tasks: `scripts/auto_continue.py` runs an outer loop — launch session → read `HANDOFF.md` → relaunch until `## COMPLETE`. See [architecture/auto-continuation.md](../architecture/auto-continuation.md).

## Strict mode (anti-fake)

Optional `"mode": "strict"` in `gates.json` adds:

- **Fixture provenance (G-IMPL-7)** — test data must cite a real source
- **Drift detection** — counters for skipped queries, forward patches, etc.
- **Integrity checks** — periodic hook health warnings

Activate: `agent-toolkit-setup --lockdown` or `AGENT_TOOLKIT_MODE=strict`. Details: [strict-mode.md](../shared/strict-mode.md).

## Configuration surface

All project settings live in **`gates.json`**. Presets via `agent-toolkit-setup`:

| Preset | Typical use |
|--------|-------------|
| **balanced** | Daily development |
| **guarded** | Production — block + protect on |
| **lockdown** | Strict mode + paranoid profile |
| **quick** | Local experiments only — disables structural protection |

Rare but important options (warn escalation, env overrides, signed migration): [gate-unlock.md](../shared/gate-unlock.md#important-rare-options).

Full index: [docs/README.md](README.md)
