<!-- agent-toolkit:architecture | v1 | 2026-05-20 | d7e42a19 -->

# Architecture: Auto-Continuation System

## Overview

Three Python components that replace bash session hooks and add automatic session chaining:

```
┌─────────────────────────────────────────────────────────┐
│  auto_continue.py  (outer loop — runs in user's shell)  │
│                                                         │
│  Goal: "Build auth system with token refresh"           │
│  Budget: --max-budget-usd 5.00 (optional)               │
│                                                         │
│  Loop:                                                  │
│    1. Clean .session/                                   │
│    2. Launch: claude -p <prompt> --output-format json    │
│    3. Wait for exit                                     │
│    4. Append to handoff-history.log                     │
│    5. Check HANDOFF.md → COMPLETE? stop : loop          │
└──────────────────┬──────────────────────────────────────┘
                   │ spawns subprocess
                   ▼
┌─────────────────────────────────────────────────────────┐
│  Claude Code session                                    │
│                                                         │
│  SessionStart → session_init.py                         │
│    - Scan project .md files                             │
│    - Inject continuation context if HANDOFF.md exists   │
│    - Initialize .session/state.json                     │
│                                                         │
│  PreToolUse / UserPromptSubmit → session_monitor.py     │
│    - Track cumulative_output_bytes + exchanges          │
│    - Detect PostCompact (context compressed)            │
│    - Warn → grace → hard stop (same flow as today)     │
│    - Enforce G-SESSION-1                                │
│                                                         │
│  PostCompact → session_monitor.py                       │
│    - Increment compaction counter                       │
│    - Trigger immediate handoff preparation              │
│                                                         │
│  Orchestrator (shared/orchestrator.md) runs inside      │
│  Auto-continue manages the boundary between sessions    │
└─────────────────────────────────────────────────────────┘
```

## Components

### 1. `hooks/session_monitor.py`

**Replaces:** `hooks/session-monitor.sh` (290 lines bash → ~200 lines Python)

**State file:** `.session/state.json`

```python
@dataclass
class SessionState:
    session_start: int          # Unix timestamp
    exchanges: int = 0
    tool_calls: int = 0
    cumulative_output_bytes: int = 0  # NEW: sum of tool result sizes
    compactions: int = 0              # NEW: PostCompact event count
    warned: bool = False
    stopped: int = 0                  # 0=running, 1=grace, 2=hard-stop
    stop_at_tool_call: int = 0
```

**Trigger logic (replaces fixed thresholds):**

```python
# Priority order — first match wins
TRIGGERS = [
    # PostCompact fired → context already full
    lambda s: s.compactions >= 1,

    # Cumulative output exceeds estimated capacity
    # 700KB ≈ 175K tokens ≈ 85% of 200K context window
    lambda s: s.cumulative_output_bytes > HARD_THRESHOLD_BYTES,

    # Fallback: exchange count (raised from 20 → 30)
    lambda s: s.exchanges >= FALLBACK_MAX_EXCHANGES,

    # Fallback: wall clock (raised from 50 → 75 min)
    lambda s: elapsed_minutes(s) >= FALLBACK_MAX_MINUTES,
]

WARN_THRESHOLD_BYTES = 500_000   # ~70% capacity → warning
HARD_THRESHOLD_BYTES = 700_000   # ~85% capacity → handoff trigger
FALLBACK_MAX_EXCHANGES = 30
FALLBACK_MAX_MINUTES = 75
```

**How cumulative_output_bytes is tracked:**

The hook fires on PreToolUse events. It can't see tool *output* at that point — only tool *input*. Two options:

| Option | Mechanism | Accuracy |
|--------|-----------|----------|
| **A: Estimate from input** | Read/Grep: estimate output from file size. Bash: flat estimate per call. | ~60% accurate |
| **B: PostToolUse tracking** | Register a PostToolUse hook that sees actual tool results | High accuracy |

**Decision: Option B** — register `session_monitor.py` on PostToolUse as well. PostToolUse receives `tool_result` in the payload, so we can measure actual bytes. This is the only accurate approach.

**Hook events wired in settings.json:**

```json
{
  "hooks": {
    "PreToolUse": [
      { "matcher": "Bash|Write|Edit|Skill",
        "hooks": [{ "type": "command", "command": "python3 hooks/session_monitor.py" }] }
    ],
    "PostToolUse": [
      { "matcher": "",
        "hooks": [{ "type": "command", "command": "python3 hooks/session_monitor.py" }] }
    ],
    "UserPromptSubmit": [
      { "matcher": "",
        "hooks": [{ "type": "command", "command": "python3 hooks/session_monitor.py" }] }
    ],
    "PostCompact": [
      { "matcher": "",
        "hooks": [{ "type": "command", "command": "python3 hooks/session_monitor.py" }] }
    ]
  }
}
```

**Key design: single script, multiple events.** The script reads the event type from stdin JSON (`hook_event_name`) and dispatches internally. This avoids multiple entry points and keeps state management in one place.

### 2. `hooks/session_init.py`

**Replaces:** `hooks/session-init.sh` (156 lines bash → ~120 lines Python)

Same responsibilities:
- Initialize `.session/state.json` (fresh counters)
- Scan project for .md files (priority ordering)
- Hook integrity check
- Clear stale `.gates/`
- If HANDOFF.md exists → inject continuation context

**One change:** If HANDOFF.md has a `## Goal` section, inject it prominently:
```
CONTINUATION SESSION: This is session N of an auto-continuation run.
GOAL: <goal text from HANDOFF.md>
Read HANDOFF.md FIRST and continue from where the previous session left off.
```

### 3. `scripts/auto_continue.py`

**New file.** Outer loop that manages session lifecycle.

```python
class AutoContinue:
    def __init__(self, goal: str | None, max_budget: float | None, project_dir: Path):
        self.goal = goal
        self.max_budget = max_budget
        self.project_dir = project_dir
        self.handoff_file = project_dir / "HANDOFF.md"
        self.history_log = project_dir / "handoff-history.log"
        self.session_count = 0

    def run(self) -> int:
        """Main loop. Returns 0 on success, 1 on failure."""
        self.goal = self._resolve_goal()
        self._seed_handoff()  # Write initial HANDOFF.md with ## Goal

        while True:
            self.session_count += 1
            self._clean_session_dir()

            prompt = self._build_prompt()
            exit_code = self._launch_session(prompt)

            # Check completion
            if self._is_complete():
                self._log_history("COMPLETE")
                print(f"✓ Goal reached in {self.session_count} sessions.")
                return 0

            # Log and continue
            self._log_history("HANDOFF")
            print(f"Session {self.session_count} handed off. Continuing...")

    def _resolve_goal(self) -> str:
        """Goal from: arg > HANDOFF.md > interactive prompt."""
        if self.goal:
            return self.goal
        if self.handoff_file.exists():
            # Parse ## Goal section
            ...
        return input("What's the goal? ")

    def _build_prompt(self) -> str:
        if self.session_count == 1:
            return f"Read HANDOFF.md. The goal is: {self.goal}. Begin working."
        return "Read HANDOFF.md and continue from where the previous session left off."

    def _launch_session(self, prompt: str) -> int:
        cmd = ["claude", "-p", prompt, "--output-format", "json"]
        if self.max_budget:
            cmd.extend(["--max-budget-usd", str(self.max_budget)])
        result = subprocess.run(cmd, cwd=self.project_dir)
        return result.returncode

    def _is_complete(self) -> bool:
        if not self.handoff_file.exists():
            return True  # Agent cleaned up → done
        content = self.handoff_file.read_text()
        return "## COMPLETE" in content

    def _seed_handoff(self):
        """Write initial HANDOFF.md with goal so first session has context."""
        self.handoff_file.write_text(f"# HANDOFF\n\n## Goal\n\n{self.goal}\n\n## Status\n\nSession 1 — starting.\n")

    def _log_history(self, event: str):
        """Append one line to handoff-history.log."""
        ...

    def _clean_session_dir(self):
        session_dir = self.project_dir / ".session"
        if session_dir.exists():
            shutil.rmtree(session_dir)
```

**CLI interface:**

```bash
# Interactive (default) — wraps normal `claude` session
# User works normally. On context exhaustion → auto-relaunch.
python scripts/auto_continue.py

# Interactive with goal (written to HANDOFF.md ## Goal)
python scripts/auto_continue.py "Build auth system with token refresh"

# Headless — fire-and-forget, uses `claude -p`
python scripts/auto_continue.py --headless "Build auth system"

# With budget cap
python scripts/auto_continue.py --max-budget-usd 5.00 "Build auth system"
```

**Relaunch strategy (context-aware):**

```python
def _detect_exit_reason(self) -> str:
    """Determine why session ended."""
    state_file = self.project_dir / ".session" / "state.json"
    if state_file.exists():
        state = json.loads(state_file.read_text())
        if state.get("stopped", 0) >= 1:
            return "context_exhaustion"  # Handoff triggered
    if self.handoff_file.exists():
        return "context_exhaustion"      # HANDOFF.md written
    return "unexpected_exit"             # Crash, user closed, etc.

def _relaunch(self, reason: str):
    if reason == "context_exhaustion":
        # Fresh session — clean context window, reads HANDOFF.md
        self._clean_session_dir()
        self._launch_session(fresh=True)
    else:
        # Resume — preserve context (crash recovery)
        self._launch_session(continue_last=True)
```

## Data Flow

### HANDOFF.md (rewritten each session)

```markdown
# HANDOFF

## Goal

Build auth system with token refresh for the API.

## Session

Number: 3
Previous sessions: 2
Budget used: $1.23 (of $5.00)

## Done

- [x] Token storage migration (commit abc1234)
- [x] Refresh endpoint (commit def5678)

## Next

- [ ] Expiry handling
- [ ] Integration tests

## Code Change Plan

### New files
- src/auth/expiry.py — TTL checker, ~40 lines
### Modified files
- src/auth/refresh.py — add expiry check before refresh
### Tests
- tests/test_expiry.py — 4 tests: expired, valid, edge, refresh-after-expiry

## Resume Command

/implementation auto slab-3
```

### handoff-history.log (append-only, gitignored)

```
[2026-05-20T14:32:00Z] Session 1 | HANDOFF | Done: token storage migration | Next: refresh endpoint | Commit: abc1234 | Bytes: 450KB | Trigger: cumulative_output
[2026-05-20T15:01:00Z] Session 2 | HANDOFF | Done: refresh endpoint | Next: expiry handling | Commit: def5678 | Bytes: 620KB | Trigger: PostCompact
[2026-05-20T15:28:00Z] Session 3 | COMPLETE | All tasks done | Final: ghi9012 | Eval: 96% A
```

## Decisions

| ID | Decision | Options considered | Rationale |
|----|----------|-------------------|-----------|
| D-ARCH-1 | Single Python script per hook, dispatches on event type | (A) Separate scripts per event (B) Single dispatch | Single file = one state manager, no race conditions between scripts |
| D-ARCH-2 | PostToolUse for byte tracking (not estimates) | (A) Estimate from input (B) PostToolUse actual | Accuracy matters — estimates would mis-trigger or miss-trigger |
| D-ARCH-3 | JSON state file (not key=value) | (A) key=value like bash (B) JSON (C) SQLite | JSON: native Python, typed via dataclass, human-readable |
| D-ARCH-4 | handoff-history.log in project root (gitignored) | (A) .session/ (cleaned) (B) reports/ (committed) (C) root (gitignored) | Persists across session cleanups, doesn't pollute git history |
| D-ARCH-5 | Bash hooks kept as shims during migration | (A) Hard cutover (B) Parallel with shims | Lower risk — validate Python before removing bash |
| D-ARCH-6 | auto_continue.py wraps interactive `claude` by default, `--headless` uses `-p` | (A) Always `-p` (B) Always interactive (C) Both via flag | Interactive is the primary use case; headless for fire-and-forget |
| D-ARCH-7 | Fresh session + HANDOFF.md for context exhaustion; `--continue` for crash recovery | (A) Always fresh (B) Always continue (C) Context-aware | `--continue` resumes into full context (defeats purpose). Fresh session gets clean window. But crash recovery benefits from `--continue`. |
| D-ARCH-8 | Claude Code only — not portable to Codex/Cursor | N/A | Hooks + CLI subprocess = Claude Code specific. Same as existing structural hooks. |

## Migration Strategy

**Phase 1: Python hooks alongside bash (low risk)**
```
settings.json:
  PreToolUse → session-monitor.sh (existing, unchanged)
  PostToolUse → session_monitor.py (new, byte tracking only)
  PostCompact → session_monitor.py (new, compaction tracking)
```
State lives in two places: `.session/state` (bash) and `.session/state.json` (Python). Bash remains source of truth for enforcement. Python only tracks bytes + compactions.

**Phase 2: Python takes over enforcement**
```
settings.json:
  PreToolUse → python3 hooks/session_monitor.py
  PostToolUse → python3 hooks/session_monitor.py
  UserPromptSubmit → python3 hooks/session_monitor.py
  PostCompact → python3 hooks/session_monitor.py
  SessionStart → python3 hooks/session_init.py
```
Bash hooks removed from settings.json. Kept in repo for reference.

**Phase 3: auto_continue.py ships**
Wrapper added. install.sh updated to mention it. README updated.

## Testing Strategy

| Component | Test approach |
|-----------|--------------|
| `session_monitor.py` | Unit tests: state transitions, threshold detection, G-SESSION-1 blocking, JSON output format |
| `session_init.py` | Unit tests: .md scanning, state initialization, HANDOFF.md detection |
| `auto_continue.py` | Integration test: mock `claude -p` with subprocess, verify loop/handoff/completion |
| Byte threshold calibration | Manual: run 3-5 real sessions, log cumulative_output_bytes at PostCompact, tune thresholds |

## Risks

| Risk | Mitigation |
|------|-----------|
| PostCompact doesn't fire reliably | Byte threshold + exchange/time fallbacks ensure handoff still triggers |
| Byte estimates wrong (500KB/700KB) | Calibrate from real sessions in Phase 1; thresholds are configurable |
| `claude -p` doesn't fire all hooks | Verify in Phase 1 before building auto_continue.py |
| Infinite loop (never reaches COMPLETE) | Log each session; user can Ctrl-C; future: add max-sessions safety valve |
| State file corruption (concurrent writes) | Single writer (one hook call at a time per session); atomic write via tempfile+rename |

## SOLID / DRY / KISS / YAGNI Check

| Principle | Status |
|-----------|--------|
| **SRP** | OK — session_monitor (enforcement), session_init (setup), auto_continue (lifecycle) |
| **DRY** | OK — JSON output helper shared, state read/write in one place |
| **KISS** | OK — same warn→grace→hard-stop flow, just better triggers |
| **YAGNI** | OK — no Agent SDK, no daemon mode, no web UI, no DB. Just files + subprocess |
