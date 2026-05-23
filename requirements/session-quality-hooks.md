# Requirements: Session Quality Hooks

**Core intent:** Prevent the agent from silently degrading by forcing time boundaries, test-first discipline, and real-data validation.

**Slug:** session-quality-hooks

## Features

### F1: Time-based session limit (70 min)

**Problem:** Context-based limits (output bytes, compaction) rarely trigger in practice — sessions run indefinitely while quality silently degrades. Research shows agent success rates decrease after ~35 min.

**Requirements:**

- F1.1: `session_monitor.py` checks elapsed time (`time.time() - state.session_start`) in `check_thresholds()`
- F1.2: Hard stop at 70 min — no warn, no grace. Immediate auto-handoff + block.
- F1.3: Always use `agent-toolkit-continue` by default — the wrapper relaunches a fresh session automatically
- F1.4: Configurable via `gates.json`: `"max_session_minutes": 70` (default 70)
- F1.5: Priority in `check_thresholds`: compaction > time > bytes > exchanges
- F1.6: On trigger: `trigger_auto_handoff()` → `state.stopped = 2` → block all non-git tools

**What it does NOT do:**
- No idle detection (Claude Code already has 5-min idle timeout)
- Does not replace context-based limits — time is a fallback

### F2: Strict TDD enforcement hook

**Problem:** Current `tdd_enforce.py` only reminds (injects context, never blocks). Agent ignores the reminder and writes source code without tests.

**Requirements:**

- F2.1: New mode: `"tdd_mode": "strict"` in `gates.json` (default: `"remind"` = current behavior)
- F2.2: In strict mode, `tdd_enforce.py` returns `{"decision": "block"}` when editing source files with no corresponding test
- F2.3: Block message: "TDD STRICT: Write the test for {filename} first. Source edits are blocked until a test file exists."
- F2.4: Exempt files: config, setup, hooks, scripts, migrations, generated code
- F2.5: Exempt when a test file was edited in the same session (within last 5 tool calls in state) — agent wrote test first, now writing source
- F2.6: Track `last_test_edits` in session state to support F2.5

**What it does NOT do:**
- Does not validate test quality (that's `/precommit`'s job)
- Does not block in `remind` mode (backwards compatible)

### F3: Quality-over-commits messaging + demo requirement

**Problem:** Agent treats commits as the goal. Rushes to commit without verifying output quality. Never demos with real data.

**Requirements:**

- F3.1: `session_init.py` injects quality reminder at session start: "Commits are not the goal — quality of work is. Ship fewer things that actually work over many things that are untested."
- F3.2: `skill_passed.py` (after `/implementation` completes a slab) injects demo prompt: "DEMO REQUIRED: Before committing, demo this feature with real data. Ask the user for sample data if you don't have any."
- F3.3: Track `demo_completed` flag in session state — set when agent runs a demo command after slab completion
- F3.4: `/precommit` checks `demo_completed` for new features (not bug fixes or refactors) — warn if false

**What it does NOT do:**
- Does not block commits on missing demos (warn only — user decides)
- Does not define what "real data" is (user provides it)

## Priority

F1 (time limit) > F2 (TDD strict) > F3 (quality messaging)

## Out of scope

- Idle session detection (handled by Claude Code)
- Test quality validation (handled by `/precommit`)
- Auto-generating test stubs (would produce sloppy tests)
