<!-- agent-toolkit:requirements | v1 | 2026-05-20 | c3a91f02 -->

# Requirements: Auto-Continuation System

## Core Intent

Replace fixed exchange/time session limits with **context-pressure-based** handoff detection, and automatically continue sessions without user intervention until the task goal is reached.

## Problem Statement

Today: sessions hard-stop at 20 exchanges or 50 minutes. User must manually start a new session and the agent must read HANDOFF.md. This is:
- Arbitrary (20 exchanges of 3 lines ≠ 20 exchanges of 500 lines)
- Disruptive (user must be present to restart)
- Inaccurate (time doesn't correlate with context usage)

## One Thing It Must Do Well

Seamlessly continue multi-session tasks without user babysitting — detect context pressure, hand off cleanly, relaunch, and resume until the goal is achieved.

## Key Decisions (from user)

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | Context-usage-based limits, not time/exchange | Better proxy for actual context pressure |
| D2 | Unlimited sessions until goal reached or token budget exhausted | Fire-and-forget until done |
| D3 | User provides goal at start; /evaluate measures progress | Goal-driven, not session-driven |
| D4 | Single HANDOFF.md rewritten each time + append-only history log | Clean handoff + audit trail |
| D5 | Anti-hallucination guardrails apply universally (from architecture skill) | No relaxation for auto mode |
| D6 | Python over bash for new scripts/hooks | User preference |

## Functional Requirements

### F1: Context Pressure Detection (`session_monitor.py`)

| ID | Requirement |
|----|-------------|
| F1.1 | Track cumulative tool output bytes in `.session/state.json` |
| F1.2 | Detect `PostCompact` hook event as primary "context full" signal |
| F1.3 | Warning at ~70% estimated capacity (configurable threshold) |
| F1.4 | Handoff trigger at ~85% estimated capacity or first PostCompact |
| F1.5 | Keep exchange/time as fallback (raised defaults: 30 exchanges / 75 min) |
| F1.6 | Grace period (10 tool calls) same as today after trigger |
| F1.7 | G-SESSION-1 enforcement (block agent writes to .session/) |

### F2: Automatic Session Continuation (`auto_continue.py`)

| ID | Requirement |
|----|-------------|
| F2.1 | Accept goal description from user at launch |
| F2.2 | Launch Claude Code session with `claude -p` (non-interactive) |
| F2.3 | Detect session end (process exit) |
| F2.4 | If HANDOFF.md exists and not marked COMPLETE → relaunch |
| F2.5 | If HANDOFF.md says COMPLETE or doesn't exist → stop |
| F2.6 | No max session cap (unlimited until done or budget) |
| F2.7 | Support `--max-budget-usd` passthrough for cost control |
| F2.8 | Clean `.session/` between relaunches |

### F3: Goal Tracking & Evaluation

| ID | Requirement |
|----|-------------|
| F3.1 | Store user's goal in HANDOFF.md `## Goal` section (persists across sessions) |
| F3.2 | Each session's handoff includes progress toward goal |
| F3.3 | Use /evaluate at end of final session to measure goal completion |
| F3.4 | If /evaluate score < threshold → continue (don't stop prematurely) |

### F4: Handoff Management

| ID | Requirement |
|----|-------------|
| F4.1 | Single `HANDOFF.md` — rewritten (not appended) each handoff |
| F4.2 | Append-only `handoff-history.log` with timestamp + one-line summary per handoff |
| F4.3 | HANDOFF.md includes: goal, status, done (commits), next steps, code change plan, resume command |
| F4.4 | History log location: persistent (not in `.session/` which gets cleaned) |

### F5: Session Init (`session_init.py`)

| ID | Requirement |
|----|-------------|
| F5.1 | Same project scanning as today (priority .md files, reports count) |
| F5.2 | If HANDOFF.md exists → inject "this is a continuation, read HANDOFF.md first" |
| F5.3 | Initialize `.session/state.json` with fresh counters |
| F5.4 | Hook integrity check (same as today) |

### F6: Guardrails (universal, no relaxation)

| ID | Requirement |
|----|-------------|
| F6.1 | Anti-hallucination: every change cites evidence (G-AUTO-1) |
| F6.2 | No code without test (TDD enforcement via tdd-enforce hook) |
| F6.3 | /precommit before every commit (G-PUSH-1) |
| F6.4 | Architecture skill's anti-hallucination mechanisms apply |

## Context Detection Signals (priority order)

1. **PostCompact event** — strongest signal (context already compressed)
2. **Cumulative tool output bytes** — early warning (biggest context consumer)
3. **Exchange count** — fallback (raised threshold)
4. **Wall clock time** — fallback (raised threshold)

## What This Does NOT Do

- Does not replace interactive mode (wrapper is opt-in for fire-and-forget tasks)
- Does not bypass quality gates (/precommit, /evaluate still required)
- Does not remove existing bash hooks immediately (migration path: parallel → cutover)
- Does not require user presence between sessions
- Does not send data to external services

## Dependencies

- Claude Code CLI with `-p` flag (non-interactive mode)
- Claude Code hook system (PreToolUse, PostToolUse, PostCompact, SessionStart, SessionEnd)
- Python 3.9+ (already available in environment)
- Existing gate/guardrail infrastructure

## File Layout

```
hooks/
  session_monitor.py    # Replaces session-monitor.sh
  session_init.py       # Replaces session-init.sh
scripts/
  auto_continue.py      # Outer wrapper (new)
HANDOFF.md              # Rewritten each handoff (existing, same location)
handoff-history.log     # Append-only audit trail (project root, gitignored)
.session/state.json     # Session state (JSON, replaces key=value)
```

## Migration Path

1. Add Python hooks alongside bash (both run, Python is source of truth for state)
2. Validate context tracking over 3-5 real sessions
3. Remove bash hooks, switch settings.json to Python
4. Ship `auto_continue.py` wrapper

## Invocation

```bash
# New task with goal
python scripts/auto_continue.py "Build the auth system with token refresh"

# Resume interrupted auto-run (reads goal from HANDOFF.md)
python scripts/auto_continue.py

# With budget cap
python scripts/auto_continue.py --max-budget-usd 5.00 "Build auth system"
```

If no goal arg and no HANDOFF.md → prompt interactively: "What's the goal?"

**Primary use case:** Interactive agent sessions that hit context limits mid-skill. User is present at start, provides goal, then walks away. The wrapper handles session boundaries transparently — the agent inside each session sees HANDOFF.md and continues as if nothing happened.

**Relationship to orchestrator:** `shared/orchestrator.md` chains skills within a single session. `auto_continue.py` handles the *between-sessions* boundary that the orchestrator cannot cross. They complement each other — orchestrator runs inside each session, auto_continue manages the session lifecycle.

## Open Questions

- **PostCompact hook reliability**: Does it fire consistently? Need to validate in real usage.
- **Byte threshold calibration**: 500KB/700KB are estimates — need empirical data from a few sessions.
- **`claude -p` with hooks**: Do all hooks (including SessionStart) fire in print mode? Need to verify.
