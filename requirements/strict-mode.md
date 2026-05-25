# Requirements: Strict Mode

**Status:** Draft
**Date:** 2026-05-20
**Origin:** Agent faking incident — agent wrote test fixtures from inference, patched forward on failures, and passed all quality gates formally while being wrong. Strict mode prevents this by adding runtime drift detection and mandatory evidence checks.

## Core Intent

An optional mode that makes the agent restrictive but high-quality. Trades speed for correctness. Activated when building something important where faking has real consequences.

## Problem It Solves

Normal mode trusts the agent to follow skills honestly. That works most of the time. But under pressure (context filling, complex task, many slabs), the agent optimizes for completion:
- Invents test fixtures from code reading
- Patches forward when tests fail (fixes code without understanding why)
- Skips real-system queries because they're slow
- Satisfies formal checks (precommit passes) while underlying assumptions are wrong

Strict mode makes these patterns structurally detectable and blocks them.

## Activation

```bash
# In gates.json (project-level)
{ "mode": "strict" }

# Or env var (per-session)
AGENT_TOOLKIT_MODE=strict

# Or via auto-continue
claude-auto --strict "Build the payment system"
```

When active, session_init.py injects: "STRICT MODE ACTIVE — G-IMPL-7 enforced, periodic integrity checks enabled, /evaluate required before commit."

## What Strict Mode Adds

### S1: Ground Truth Enforcement (G-IMPL-7)

Test fixtures must cite their data source. "I read the code" is not a valid source.

**Valid:** query output, user-provided sample, spec/contract, factory/faker.
**Invalid:** inference from model/schema, "the code suggests," pattern completion.

Enforcement: /precommit checks fixture provenance. Block commit if any fixture has no citation.

### S2: Drift Detection (session monitor)

The session monitor tracks three counters (only in strict mode):

| Counter | What it tracks | Resets on |
|---------|---------------|-----------|
| `exchanges_since_query` | Exchanges since last real-system contact (Bash with curl/psql/SELECT/sqlite3/API call) | Any real-system query |
| `patch_forward_count` | Times a test failed → source was edited → no investigation (Read/Bash query) between | Never (cumulative per session) |
| `slabs_without_data` | Consecutive slabs completed with zero data queries | Any real-system query |

**Thresholds:**
- `exchanges_since_query > 10` → inject warning: "You haven't queried the real system in 10 exchanges. Are you working from inference?"
- `patch_forward_count > 2` → inject warning: "Patch-forward pattern detected 3 times. Stop and investigate root causes."
- `slabs_without_data > 1` → block: "2 slabs completed with no real-system queries. This slab requires data evidence before continuing."

### S3: Periodic Integrity Check (every 15 exchanges)

Every 15 exchanges, the session monitor injects a mandatory self-audit:

```
STRICT MODE INTEGRITY CHECK (exchange {N}):
- Exchanges since last real-system query: {X}
- Patch-forward incidents this session: {Y}
- Slabs without data queries: {Z}
- Drift score: {computed}

If drift score > threshold: PAUSE. Query the real system before continuing.
If drift score critical: SESSION RESTART recommended — write HANDOFF.md.
```

This is not optional context the agent can ignore — it's injected as `additionalContext` with specific instructions.

### S4: /evaluate Required Before Commit

Normal mode: only /precommit required before commit.
Strict mode: /precommit AND /evaluate both required.

Gate config in strict mode:
```json
{
  "mode": "strict",
  "commit_requires": ["precommit", "evaluate"],
  "push_requires": ["evaluate"]
}
```

### S5: Session Restart on High Drift

If drift score exceeds critical threshold:
- Session monitor sets `stopped = 2` (same as context exhaustion)
- Agent must write HANDOFF.md and exit
- auto_continue.py relaunches with fresh context
- Fresh session = fresh discipline (agent re-reads rules, counters reset)

This treats drift like context exhaustion — the agent's internal state is corrupted, restart fixes it.

### S6: Slab Cycle — Mandatory DATA Step

In strict mode, the slab cycle gains a mandatory step between SETUP and TDD:

```
1. SETUP — re-read requirements for THIS slab
2. DATA — if this slab touches any data:
   - Query the real system (SELECT, curl, API call)
   - Paste the output as evidence
   - Derive test fixtures FROM the output
   - If no real system exists: state explicitly "fixtures are synthetic (factory)" or "user-provided sample"
   - "I read the schema/model" is NOT sufficient (G-IMPL-7)
3. TDD — meaningful assertions using fixtures from step 2
```

## What Strict Mode Does NOT Change

- Skill workflows (/implementation, /debug, etc.) — same, just stricter enforcement
- Gate mechanism (legacy/signed) — same, just requires /evaluate too
- Auto-continuation — same, but drift can trigger restart
- Normal sessions — unaffected when mode != strict

## Detection: How to Identify Patch-Forward

A patch-forward occurs when:
1. A test is run (Bash containing `pytest`, `jest`, `go test`, `cargo test`)
2. The test FAILS (exit code != 0)
3. The next tool call is Edit/Write on a SOURCE file (not test file)
4. Between steps 2 and 3, there is NO:
   - Read of the failing test's output to understand why
   - Bash query (SELECT, curl, etc.) to check real state
   - Read of a related source file to investigate

The session monitor tracks tool call sequences and detects this pattern.

## Detection: How to Identify Real-System Queries

Bash commands matching any of:
- `curl`, `wget`, `httpie`, `http `
- `psql`, `mysql`, `sqlite3`, `mongosh`
- SQL keywords: `SELECT`, `INSERT`, `UPDATE`, `DELETE` (in Bash or via cli tools)
- `docker exec` + query
- API testing tools: `grpcurl`, `postman`

This list is extensible via `gates.json`:
```json
{
  "strict_query_patterns": ["custom-cli query", "my-tool fetch"]
}
```

## Drift Score Calculation

```
drift_score = (
    min(exchanges_since_query / 10, 1.0) * 0.4 +
    min(patch_forward_count / 3, 1.0) * 0.4 +
    min(slabs_without_data / 2, 1.0) * 0.2
)
```

- `< 0.3` — normal (no action)
- `0.3 - 0.6` — warning injected
- `0.6 - 0.8` — strong warning + block new slabs until query
- `> 0.8` — session restart trigger

## File Changes

### New
- `shared/strict-mode.md` — rules reference (skills read this when mode=strict)

### Modified
- `hooks/session_monitor.py` — drift counters, periodic check, tool sequence tracking
- `hooks/gate.py` — load mode, require /evaluate in strict
- `hooks/session_init.py` — detect mode, inject strict mode context
- `shared/guardrails.md` — add G-IMPL-7
- `shared/guardrails-quick.md` — add G-IMPL-7 one-liner
- `skills/implementation/SKILL.md` — DATA step in slab cycle
- `skills/precommit/SKILL.md` — fixture provenance check
- `skills/precommit/references/test-quality.md` — provenance in checklist
- `gates.json` + `templates/gates.json` — mode field, strict_query_patterns

## Success Criteria

1. Agent in strict mode cannot write test fixtures without citing data source
2. Patch-forward pattern is detected and flagged within 1 occurrence after threshold
3. Drift warning fires within 10 exchanges of last real-system query
4. Session restarts automatically on critical drift (no user intervention)
5. /evaluate is mandatory before commit in strict mode
6. Normal mode is completely unaffected
